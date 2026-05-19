"""AI 分析 API + WebSocket 辩论"""
import asyncio
import json
import logging

import pandas as pd
from fastapi import APIRouter, Request, Form, WebSocket, WebSocketDisconnect

from .data_api import _get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


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
    """AI 三方辩论 — WebSocket 流式推送"""
    await websocket.accept()

    try:
        # 等待客户端发送初始参数
        init_data = await websocket.receive_text()
        params = json.loads(init_data)
        stock_code = params.get("stock_code", "")

        if not stock_code:
            await websocket.send_text(json.dumps({"type": "error", "content": "缺少股票代码"}))
            await websocket.close()
            return

        # 这里复用现有的同步 DebateEngine + DeepSeek stream client
        # 简化版：收集数据 + 使用 DeepSeek stream client 流式推送

        from financial_analyzer.deepseek.client import DeepSeekStreamClient, DeepSeekConfig
        from financial_analyzer.deepseek.prompts import (
            _load_config, get_debate_system_prompt,
            build_debate_round1,
        )

        ai_config = _load_config()
        api_key = ai_config.get("api_key", "")
        if not api_key:
            await websocket.send_text(json.dumps({"type": "error", "content": "请先配置 DeepSeek API Key"}))
            await websocket.close()
            return

        config = DeepSeekConfig(api_key=api_key)
        client = DeepSeekStreamClient(config)

        # 构建分析报告
        session = _get_session_for_ws(stock_code)
        if session and session.get("data"):
            from financial_analyzer.ai.report_builder import ReportBuilder
            data = {k: pd.DataFrame(v) for k, v in session["data"].items()}
            report = ReportBuilder.build(data, stock_code)
            report_text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        else:
            report_text = f"股票代码: {stock_code}\n(无法获取完整财务数据)"

        system_prompt = get_debate_system_prompt()
        prompt = build_debate_round1(report_text, stock_code, stock_code, "value")

        await websocket.send_text(json.dumps({"type": "status", "content": "辩论开始..."}))

        # 流式发送
        def stream_callback(chunk: str):
            """回调在线程中运行，通过 asyncio 转发到 WebSocket"""
            pass  # 由 client 内部处理

        # 使用生成器方式流式输出
        try:
            full_text = ""
            for chunk in client.chat_stream(prompt, system_prompt):
                full_text += chunk
                await websocket.send_text(json.dumps({
                    "type": "chunk",
                    "content": chunk,
                }))
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Stream error: {e}")

        await websocket.send_text(json.dumps({"type": "done", "content": ""}))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
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
    """WebSocket 无 HTTP request，通过默认 session 获取"""
    from .data_api import _sessions
    return _sessions.get("default", None)


def _ai_response(content: str):
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""
    <div class="ai-response" id="ai-result">
        <div class="ai-content">{content}</div>
    </div>
    """)


def _ai_error(msg: str):
    from fastapi.responses import HTMLResponse
    return HTMLResponse(f"""
    <div class="ai-error" id="ai-result">
        <p>⚠️ {msg}</p>
    </div>
    """)
