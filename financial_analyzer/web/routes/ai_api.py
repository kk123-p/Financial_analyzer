"""AI 分析 API + WebSocket 辩论"""
import asyncio
import json
import logging
import queue
import threading

import pandas as pd
from fastapi import APIRouter, Request, Form, WebSocket, WebSocketDisconnect

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
        engine = DebateEngine(config=config)

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
            engine = DebateEngine(config=config)
            return engine

        orchestrator = AnalysisOrchestrator(
            llm_client=client,
            debate_engine_factory=debate_factory,
        )
        conversation = ConversationManager()

        await websocket.send_text(json.dumps({"type": "meta", "content": "ready"}))

<<<<<<< HEAD
        # Track current analysis task for cancellation
        _current_task: asyncio.Task | None = None

=======
>>>>>>> e0e0c9e60405e5fdebe1933aef34c0c834b9b84b
        while True:
            msg_data = await websocket.receive_text()
            msg = json.loads(msg_data)

            if msg.get("type") == "message":
                user_message = msg.get("content", "").strip()
                if not user_message:
                    continue

<<<<<<< HEAD
                import asyncio as aio
                event_queue: aio.Queue = aio.Queue()

                def analysis_callback(event_type: str, content: str, meta: dict | None):
                    # Called from orchestrator thread — must be threadsafe
                    event_queue.put_nowait((event_type, content, meta))

                async def run_analysis_async():
                    try:
                        await aio.to_thread(
                            orchestrator.analyze,
=======
                import queue as q_module
                msg_queue = q_module.Queue()
                loop = asyncio.get_event_loop()

                def analysis_callback(event_type: str, content: str, meta: dict | None):
                    msg_queue.put((event_type, content, meta))

                def run_analysis():
                    try:
                        orchestrator.analyze(
>>>>>>> e0e0c9e60405e5fdebe1933aef34c0c834b9b84b
                            user_message=user_message,
                            conversation=conversation,
                            data=data,
                            stock_code=stock_code,
                            company_name=company_name,
                            callback=analysis_callback,
                        )
                    except Exception as e:
                        logger.error(f"Analysis error: {e}", exc_info=True)
<<<<<<< HEAD
                        await event_queue.put(("error", str(e), None))
                        await event_queue.put(("done", "", None))

                task = aio.create_task(run_analysis_async())
                _current_task = task

                while True:
                    try:
                        item = await event_queue.get()
                    except aio.CancelledError:
                        break
=======
                        msg_queue.put(("error", str(e), None))

                thread = threading.Thread(target=run_analysis, daemon=True)
                thread.start()

                while True:
                    item = await loop.run_in_executor(None, msg_queue.get)
>>>>>>> e0e0c9e60405e5fdebe1933aef34c0c834b9b84b
                    event_type, content, meta = item

                    if event_type == "done":
                        await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                        break

                    payload = {"type": event_type, "content": content}
                    if meta:
                        payload["meta"] = meta
<<<<<<< HEAD
                    try:
                        await websocket.send_text(json.dumps(payload))
                    except Exception:
                        break

            elif msg.get("type") == "stop":
                if _current_task and not _current_task.done():
                    _current_task.cancel()
=======
                    await websocket.send_text(json.dumps(payload))

            elif msg.get("type") == "stop":
>>>>>>> e0e0c9e60405e5fdebe1933aef34c0c834b9b84b
                await websocket.send_text(json.dumps({"type": "meta", "content": "stopped"}))
                break

    except WebSocketDisconnect:
        logger.info("AI conversation WebSocket disconnected")
<<<<<<< HEAD
        if _current_task and not _current_task.done():
            _current_task.cancel()
=======
>>>>>>> e0e0c9e60405e5fdebe1933aef34c0c834b9b84b
    except Exception as e:
        logger.error(f"AI conversation error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass
    finally:
<<<<<<< HEAD
        if _current_task and not _current_task.done():
            _current_task.cancel()
=======
>>>>>>> e0e0c9e60405e5fdebe1933aef34c0c834b9b84b
        try:
            await websocket.close()
        except Exception:
            pass
