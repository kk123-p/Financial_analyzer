"""AI 分析 API + WebSocket 辩论"""
import asyncio
import json
import logging
import queue
import threading

import pandas as pd
from fastapi import APIRouter, Request, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from .data_api import _get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

# 队列哨兵类型，避免字符串魔法值
class _Sentinel:
    pass
QUEUE_DONE = _Sentinel()

# 缓存配置，避免每次 WebSocket 连接都读磁盘
_cached_ai_config: dict | None = None
_cache_lock = threading.Lock()


def _get_ai_config() -> dict:
    global _cached_ai_config
    if _cached_ai_config is not None:
        return _cached_ai_config
    with _cache_lock:
        if _cached_ai_config is not None:
            return _cached_ai_config
        # 加载 AI 分析参数（分析权重、辩论轮数等）
        from financial_analyzer.deepseek.prompts import _load_config as _load_ai_config
        config = _load_ai_config()
        # 从主配置文件加载 API key（UI Token 设置保存在此文件）
        from financial_analyzer.config import CONFIG_FILE
        if CONFIG_FILE.exists():
            try:
                import json
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    main_config = json.load(f)
                if main_config.get("deepseek_api_key"):
                    config["api_key"] = main_config["deepseek_api_key"]
            except Exception:
                pass
        _cached_ai_config = config
        return _cached_ai_config


def invalidate_ai_config():
    """清除缓存的 AI 配置（API key 变更后调用）"""
    global _cached_ai_config
    with _cache_lock:
        _cached_ai_config = None


@router.post("/chat")
async def ai_chat(
    request: Request,
    question: str = Form(...),
):
    """AI 单次分析（非流式）"""
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        return _ai_error("请先获取股票数据")

    try:
        from financial_analyzer.ai.report_builder import ReportBuilder
        from financial_analyzer.deepseek.client import DeepSeekClient, DeepSeekConfig

        data = {k: pd.DataFrame(v) for k, v in data_raw.items()}
        report = ReportBuilder.build(data, stock_code)

        # 加载 API key
        from financial_analyzer.deepseek.prompts import _load_config
        ai_config = _load_config()
        api_key = ai_config.get("api_key", "")
        if not api_key:
            return _ai_error("请先配置 DeepSeek API Key")

        config = DeepSeekConfig(api_key=api_key)
        client = DeepSeekClient(config)

        structured = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        prompt = f"""基于以下财务分析报告，回答用户问题。

## 公司数据报告
{structured[:8000]}

## 用户问题
{question}

请用专业、简洁的中文回答。"""

        result = await asyncio.to_thread(
            client.generate_report, prompt, "综合分析", None
        )

        if result.success:
            return _ai_response(result.content)
        return _ai_error(result.error or "AI 分析失败")

    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        return _ai_error(str(e))


@router.websocket("/debate")
async def ai_debate(websocket: WebSocket):
    """AI 三方辩论 — 完整3轮辩论，复用桌面版 DebateEngine"""
    await websocket.accept()
    engine = None

    try:
        init_data = await websocket.receive_text()
        params = json.loads(init_data)
        stock_code = params.get("stock_code", "")

        if not stock_code:
            await websocket.send_text(json.dumps({"type": "error", "content": "缺少股票代码"}))
            await websocket.close()
            return

        from financial_analyzer.deepseek.client import DeepSeekConfig
        from financial_analyzer.ai.debate_engine import DebateEngine

        ai_config = _get_ai_config()
        api_key = ai_config.get("api_key", "")
        if not api_key:
            await websocket.send_text(json.dumps({"type": "error", "content": "请先配置 DeepSeek API Key"}))
            await websocket.close()
            return

        config = DeepSeekConfig(api_key=api_key)
        engine = DebateEngine(api_key=api_key, config=config)

        # 准备分析数据
        session = _get_session_for_ws(stock_code)
        if session and session.get("data"):
            data = {k: pd.DataFrame(v) for k, v in session["data"].items()}
            prepare_result = engine.prepare(data, stock_code)
            company_name = prepare_result.get("report", {}).get("company_snapshot", {}).get("name", stock_code)
        else:
            await websocket.send_text(json.dumps({"type": "status",
                "role": "system", "content": "财务数据不足，将使用基本股票信息进行辩论"}))
            company_name = stock_code
            engine.state.report_text = f"股票代码: {stock_code}\n(无详细财务数据)"

        msg_queue: queue.Queue = queue.Queue()
        loop = asyncio.get_event_loop()

        def debate_callback(role: str, chunk: str, done: bool):
            msg_queue.put((role, chunk, done))

        def on_debate_complete(state):
            msg_queue.put(QUEUE_DONE)

        engine.start_debate(
            company_name=company_name,
            stock_code=stock_code,
            callback=debate_callback,
            on_complete=on_debate_complete,
        )

        while True:
            msg = await loop.run_in_executor(None, msg_queue.get)
            if msg is QUEUE_DONE:
                await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                break

            role, content, done = msg

            if role == "_meta":
                await websocket.send_text(json.dumps({
                    "type": "meta",
                    "content": content,
                    "info": done,
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "role": role,
                    "content": content,
                    "done": done,
                }))
                # 仅当队列为空时才让出事件循环，避免每chunk 5ms的累积延迟
                if msg_queue.empty():
                    await asyncio.sleep(0)

        # 辩论主体结束，发送完成信号
        await websocket.send_text(json.dumps({"type": "meta", "content": "debate_complete"}))

        # 进入追问模式
        FU_DONE = object()
        while True:
            try:
                followup_msg = await asyncio.wait_for(websocket.receive_text(), timeout=300)
            except (asyncio.TimeoutError, WebSocketDisconnect, RuntimeError):
                break

            fu_data = json.loads(followup_msg)
            if fu_data.get("type") == "followup":
                question = fu_data.get("content", "")
                if not question:
                    continue

                fu_queue: queue.Queue = queue.Queue()

                def fu_callback(role: str, chunk: str, done: bool):
                    fu_queue.put((role, chunk, done))

                def fu_on_complete(state):
                    fu_queue.put(FU_DONE)

                engine.send_followup(
                    question=question,
                    callback=fu_callback,
                    on_complete=fu_on_complete,
                )

                while True:
                    item = await loop.run_in_executor(None, fu_queue.get)
                    if item is FU_DONE:
                        await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                        break
                    role, content, done = item
                    if role == "_meta":
                        await websocket.send_text(json.dumps({
                            "type": "meta",
                            "content": content,
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "role": role,
                            "content": content,
                            "done": done,
                        }))
                        if fu_queue.empty():
                            await asyncio.sleep(0)

            elif fu_data.get("type") == "stop":
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        if engine:
            try:
                engine.stop()
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Debate error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


def _get_session_for_ws(stock_code: str) -> dict | None:
    """WebSocket 无 HTTP request，查找匹配 stock_code 的 session"""
    from .data_api import _sessions
    # 优先查找 stock_code 匹配的 session
    for sid, sess in _sessions.items():
        if sess.get("stock_code") == stock_code:
            return sess
    # 回退到默认 session
    return _sessions.get("default", None)


def _ai_response(content: str):
    from html import escape
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""
    <div class="ai-response" id="ai-result">
        <div class="ai-content">{escape(content)}</div>
    </div>
    """)


def _ai_error(msg: str):
    from html import escape
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""
    <div class="ai-error" id="ai-result">
        <p>⚠️ {escape(msg)}</p>
    </div>
    """)


# ============================================================================
# Phase 2: 统一 AI 对话 WebSocket（替代 /ai/chat + /ai/debate）
# ============================================================================

@router.websocket("/conversation")
async def ai_conversation(websocket: WebSocket):
    """统一 AI 对话入口 — 支持快速问答、深度分析、三方辩论"""
    await websocket.accept()
    orchestrator = None
    conversation = None
    _current_task: asyncio.Task | None = None

    try:
        init_data = await websocket.receive_text()
        params = json.loads(init_data)
        stock_code = params.get("stock_code", "")

        if not stock_code:
            await websocket.send_text(json.dumps({"type": "error", "content": "缺少股票代码"}))
            await websocket.close()
            return

        session = _get_session_for_ws(stock_code)
        if not session or not session.get("data"):
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "请先获取财务数据，再使用 AI 分析功能"
            }))
            await websocket.close()
            return

        data = {k: pd.DataFrame(v) for k, v in session["data"].items()}
        company_name = session.get("stock_name", stock_code)

        template_name = params.get("template_name", "")
        template_data = params.get("template")  # 前端传过来的完整模板 dict

        ai_config = _get_ai_config()
        api_key = ai_config.get("api_key", "")
        if not api_key:
            await websocket.send_text(json.dumps({"type": "error", "content": "请先配置 DeepSeek API Key"}))
            await websocket.close()
            return

        from financial_analyzer.deepseek.client import DeepSeekConfig, DeepSeekStreamClient
        from financial_analyzer.ai.conversation import ConversationManager
        from financial_analyzer.ai.orchestrator import AnalysisOrchestrator

        config = DeepSeekConfig(api_key=api_key)
        client = DeepSeekStreamClient(config=config)

        def debate_factory():
            from financial_analyzer.ai.debate_engine import DebateEngine
            engine = DebateEngine(api_key=api_key, config=config)
            return engine

        orchestrator = AnalysisOrchestrator(
            llm_client=client,
            debate_engine_factory=debate_factory,
        )

        # 设置当前模板
        if template_data and isinstance(template_data, dict) and template_data.get("name"):
            orchestrator._current_template = template_data
        elif template_name:
            from financial_analyzer.ai.prompt_store import PromptsStore
            store = PromptsStore()
            orchestrator._current_template = store.get_template(template_name)

        conversation = ConversationManager()

        await websocket.send_text(json.dumps({"type": "meta", "content": "ready"}))

        while True:
            try:
                msg_data = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except RuntimeError:
                break
            msg = json.loads(msg_data)

            if msg.get("type") == "message":
                user_message = msg.get("content", "").strip()
                if not user_message:
                    continue

                import asyncio as aio
                event_queue: aio.Queue = aio.Queue()

                def analysis_callback(event_type: str, content: str, meta: dict | None):
                    event_queue.put_nowait((event_type, content, meta))

                async def run_analysis_async():
                    try:
                        await aio.to_thread(
                            orchestrator.analyze,
                            user_message=user_message,
                            conversation=conversation,
                            data=data,
                            stock_code=stock_code,
                            company_name=company_name,
                            callback=analysis_callback,
                        )
                    except Exception as e:
                        logger.error(f"Analysis error: {e}", exc_info=True)
                        await event_queue.put(("error", str(e), None))
                        await event_queue.put(("done", "", None))

                task = aio.create_task(run_analysis_async())
                _current_task = task

                while True:
                    try:
                        item = await event_queue.get()
                    except aio.CancelledError:
                        break
                    event_type, content, meta = item

                    if event_type == "done":
                        await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                        break

                    payload = {"type": event_type, "content": content}
                    if meta:
                        payload["meta"] = meta
                    try:
                        await websocket.send_text(json.dumps(payload))
                    except Exception:
                        break

            elif msg.get("type") == "template":
                template_name = msg.get("template_name", "")
                extra_question = msg.get("extra_question", "")

                if not template_name:
                    await websocket.send_text(json.dumps({
                        "type": "error", "content": "缺少模板名称"
                    }))
                    continue

                from financial_analyzer.ai.prompt_store import PromptsStore
                store = PromptsStore()
                template = store.get_template(template_name)
                if template is None:
                    await websocket.send_text(json.dumps({
                        "type": "error", "content": f"模板不存在: {template_name}"
                    }))
                    continue

                # Set active template on conversation so orchestrator routes correctly
                conversation._active_template = template

                import asyncio as aio
                event_queue = aio.Queue()

                def template_callback(event_type: str, content: str, meta: dict | None):
                    event_queue.put_nowait((event_type, content, meta))

                async def run_template_async():
                    try:
                        await aio.to_thread(
                            orchestrator._stream_template,
                            template=template,
                            data=data,
                            stock_code=stock_code,
                            company_name=company_name,
                            conversation=conversation,
                            callback=template_callback,
                            extra_question=extra_question,
                        )
                    except Exception as e:
                        logger.error(f"Template analysis error: {e}", exc_info=True)
                        await event_queue.put(("error", str(e), None))
                        await event_queue.put(("done", "", None))

                task = aio.create_task(run_template_async())
                _current_task = task

                while True:
                    try:
                        item = await event_queue.get()
                    except asyncio.CancelledError:
                        break
                    event_type, content, meta = item

                    if event_type == "done":
                        await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                        break

                    payload = {"type": event_type, "content": content}
                    if meta:
                        payload["meta"] = meta
                    try:
                        await websocket.send_text(json.dumps(payload))
                    except Exception:
                        break

            elif msg.get("type") == "stop":
                if _current_task and not _current_task.done():
                    _current_task.cancel()
                await websocket.send_text(json.dumps({"type": "meta", "content": "stopped"}))
                break

    except WebSocketDisconnect:
        logger.info("AI conversation WebSocket disconnected")
        if _current_task and not _current_task.done():
            _current_task.cancel()
    except Exception as e:
        logger.error(f"AI conversation error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass
    finally:
        if _current_task and not _current_task.done():
            _current_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


# ============================================================================
# Phase 2 UX: Prompt 模板管理 API
# ============================================================================


@router.get("/prompts")
async def list_prompts():
    """列出所有 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    return store.list_templates()


@router.get("/prompts/{name:path}")
async def get_prompt(name: str):
    """获取单个 Prompt 模板完整内容"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    template = store.get_template(name)
    if template is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "模板不存在"}, status_code=404)
    return template


@router.put("/prompts/{name:path}")
async def save_prompt(name: str, request: Request):
    """保存/更新 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    data = await request.json()
    store = PromptsStore()
    ok = store.save_template(name, data)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "不能覆盖系统预置模板"}, status_code=403)
    return {"status": "ok"}


@router.delete("/prompts/{name:path}")
async def delete_prompt(name: str):
    """删除 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    ok = store.delete_template(name)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "模板不存在或为系统预置"}, status_code=403)
    return {"status": "ok"}


@router.post("/prompts/{name:path}/duplicate")
async def duplicate_prompt(name: str, request: Request):
    """复制 Prompt 模板"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    body = await request.json()
    new_name = body.get("new_name", name + " - 副本")
    store = PromptsStore()
    ok = store.duplicate_template(name, new_name)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "复制失败"}, status_code=400)
    return {"status": "ok", "new_name": new_name}


@router.get("/prompts/{name:path}/export")
async def export_prompt(name: str):
    """导出 Prompt 模板为 JSON 文件下载"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    store = PromptsStore()
    json_str = store.export_template(name)
    if json_str is None:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "模板不存在"}, status_code=404)
    safe_name = name.replace("/", "_").replace("\\", "_")
    return PlainTextResponse(
        json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'}
    )


@router.post("/prompts/import")
async def import_prompt(file: UploadFile):
    """导入 Prompt 模板（上传 JSON 文件）"""
    from financial_analyzer.ai.prompt_store import PromptsStore
    try:
        content = await file.read()
        json_str = content.decode("utf-8")
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "文件读取失败"}, status_code=400)
    store = PromptsStore()
    ok = store.import_template(json_str)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "导入失败，JSON 格式不正确"}, status_code=400)
    return {"status": "ok"}


# ============================================================================
# Phase 2 UX: 财务数据报告 API
# ============================================================================


@router.get("/report")
async def get_financial_report(request: Request):
    """获取当前 session 的财务体检报告"""
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "请先获取财务数据"}, status_code=400)

    # 优先返回缓存的 report
    cached = session.get("ai_report")
    if cached:
        return cached

    # 按需构建
    try:
        from financial_analyzer.ai.report_builder import ReportBuilder
        import pandas as pd
        data = {k: pd.DataFrame(v) for k, v in data_raw.items()}
        report = ReportBuilder.build(data, stock_code)
        session["ai_report"] = report
        return report
    except Exception as e:
        logger.error(f"Report build error: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/report/export")
async def export_financial_report(request: Request):
    """导出财务体检报告为 JSON 文件"""
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "请先获取财务数据"}, status_code=400)

    try:
        from financial_analyzer.ai.report_builder import ReportBuilder
        import pandas as pd
        import json
        data = {k: pd.DataFrame(v) for k, v in data_raw.items()}
        report = ReportBuilder.build(data, stock_code)
        session["ai_report"] = report
        json_str = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        safe_name = stock_code.replace("/", "_").replace("\\", "_")
        return PlainTextResponse(
            json_str,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report_{safe_name}.json"'}
        )
    except Exception as e:
        logger.error(f"Report export error: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)


# ============================================================================
# Phase 2 UX: 辩论导出
# ============================================================================


@router.post("/debate/export/{fmt}")
async def export_debate_result(fmt: str, request: Request):
    """
    导出辩论结果为 Markdown 或 HTML

    Args:
        fmt: "md" 或 "html"
    Body: {"debate_data": {...}, "stock_code": "...", "company_name": "..."}
    """
    from datetime import datetime
    body = await request.json()
    debate_data = body.get("debate_data", {})
    stock_code = body.get("stock_code", "")
    company_name = body.get("company_name", stock_code)

    if not debate_data:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "缺少辩论数据"}, status_code=400)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    safe_name = stock_code.replace("/", "_").replace("\\", "_")

    if fmt == "md":
        md = _build_debate_markdown(debate_data, company_name, stock_code, now)
        return PlainTextResponse(
            md, media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="debate_{safe_name}.md"'}
        )
    elif fmt == "html":
        html = _build_debate_html(debate_data, company_name, stock_code, now)
        return PlainTextResponse(
            html, media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="debate_{safe_name}.html"'}
        )
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": f"不支持的格式: {fmt}"}, status_code=400)


def _build_debate_markdown(debate_data: dict, company_name: str, stock_code: str, now: str) -> str:
    """将辩论数据组装为 Markdown"""
    lines = [
        f"# 三方投研辩论 — {company_name}({stock_code})",
        f"> 辩论时间：{now}",
        "",
    ]

    ANALYST_LABELS = {
        "value": "📊 格雷厄姆式价值分析师",
        "growth": "🚀 费雪式成长分析师",
        "risk": "🛡️ 塔勒布式风控师",
    }

    # 各轮辩论
    for round_key, round_title in [("round1", "第1轮：独立陈述"),
                                     ("round2", "第2轮：交叉质询"),
                                     ("round3", "第3轮：共识与情景概率")]:
        lines.append(f"## {round_title}")
        statements = debate_data.get(round_key, {})
        if isinstance(statements, dict):
            for role_key in ["value", "growth", "risk"]:
                content = statements.get(role_key, "")
                label = ANALYST_LABELS.get(role_key, role_key)
                lines.append(f"\n### {label}")
                lines.append(content)
        elif isinstance(statements, str):
            lines.append(statements)
        lines.append("")

    # 综合共识
    consensus = debate_data.get("consensus", "")
    if consensus:
        lines.append("## 综合共识")
        lines.append(consensus)
        lines.append("")

    # 追问
    followups = debate_data.get("followups", [])
    if followups:
        lines.append("## 用户追问")
        for fu in followups:
            lines.append(f"\n> {fu.get('question', '')}")
            for role_key in ["value", "growth", "risk"]:
                content = fu.get(role_key, "")
                label = ANALYST_LABELS.get(role_key, role_key)
                if content:
                    lines.append(f"\n### {label}")
                    lines.append(content)
            lines.append("")

    return "\n".join(lines)


def _build_debate_html(debate_data: dict, company_name: str, stock_code: str, now: str) -> str:
    """将辩论数据组装为独立 HTML 页面"""
    md_content = _build_debate_markdown(debate_data, company_name, stock_code, now)
    html_body_parts = []
    for line in md_content.split("\n"):
        line_escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("# "):
            html_body_parts.append(f'<h1 style="color:#F1F5F9;border-bottom:1px solid rgba(59,130,246,0.2);padding-bottom:8px;">{line_escaped[2:]}</h1>')
        elif line.startswith("## "):
            html_body_parts.append(f'<h2 style="color:#E2E8F0;margin-top:24px;">{line_escaped[3:]}</h2>')
        elif line.startswith("### "):
            html_body_parts.append(f'<h3 style="color:#94A3B8;margin-top:16px;">{line_escaped[4:]}</h3>')
        elif line.startswith("> "):
            html_body_parts.append(f'<blockquote style="color:#94A3B8;border-left:3px solid rgba(59,130,246,0.3);padding-left:12px;margin:8px 0;">{line_escaped[2:]}</blockquote>')
        elif line.strip():
            html_body_parts.append(f'<p style="color:#CBD5E1;line-height:1.8;">{line_escaped}</p>')
        else:
            html_body_parts.append("<br>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>三方辩论 — {company_name}</title>
<style>
  body {{
    max-width: 900px; margin: 40px auto; padding: 20px;
    background: #0B1021; color: #CBD5E1;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.7;
  }}
  h1 {{ color: #F1F5F9; border-bottom: 1px solid rgba(59,130,246,0.2); padding-bottom: 8px; }}
  h2 {{ color: #E2E8F0; margin-top: 24px; }}
  h3 {{ color: #94A3B8; margin-top: 16px; }}
  blockquote {{ color: #94A3B8; border-left: 3px solid rgba(59,130,246,0.3); padding-left: 12px; margin: 8px 0; }}
</style>
</head>
<body>
{"".join(html_body_parts)}
</body>
</html>"""
