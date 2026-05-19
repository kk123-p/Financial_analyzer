"""页面路由 — Jinja2 整页渲染"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .data_api import _get_session

router = APIRouter(tags=["pages"])

_templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

# 暴露给模板的全局配置
from financial_analyzer.config import APP_VERSION


@router.get("/")
async def index(request: Request):
    from ..services.analysis_service import get_analysis_list

    # 不调用 get_adapter() 以避免网络阻塞；仅列出可用源名称
    sources = ["tushare", "akshare", "sina", "yfinance"]
    active_source = "tushare"

    session = _get_session(request)

    return templates.TemplateResponse(request, "base.html", {
        "version": APP_VERSION,
        "sections": get_analysis_list(),
        "sources": sources,
        "active_source": active_source,
        "kpis": {
            "stock_name": "--",
            "current_price": "--",
            "price_change": "--",
            "price_change_up": False,
            "volume": "--",
            "pe_ratio": "--",
            "market_cap": "--",
            "source": active_source.upper(),
        },
        "stock_code": session.get("stock_code", ""),
    })
