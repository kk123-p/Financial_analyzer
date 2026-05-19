"""分析路由 — GET /analyze/{type} → htmx 局部更新"""
import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from http.client import HTTPException

from ..services.analysis_service import AnalysisService
from ..dependencies import get_adapter, get_cache
from .data_api import _get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analysis"])

_templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/{analysis_type}")
async def run_analysis(request: Request, analysis_type: str):
    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw or not stock_code:
        return _empty_result("请先输入股票代码并获取数据")

    import pandas as pd
    data = {k: pd.DataFrame(v) for k, v in data_raw.items()}

    service = AnalysisService(get_adapter(), get_cache())

    # 同步分析器在后台线程运行
    loop = asyncio.get_event_loop()
    result_text = await loop.run_in_executor(
        None, service.run, analysis_type, data, stock_code
    )

    # 将纯文本格式化为 HTML
    from ..services.result_formatter import ResultFormatter
    result_html = ResultFormatter.format(result_text)

    return templates.TemplateResponse(request, "partials/result_text.html", {
        "result": result_html,
        "analysis_type": analysis_type,
    })


def _empty_result(msg: str):
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content=f'<div class="empty-state"><p>{msg}</p></div>',
        status_code=200,
    )
