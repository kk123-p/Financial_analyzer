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
        from financial_analyzer.deepseek.prompts import _load_config
        _cached_ai_config = _load_config()
        return _cached_ai_config


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
