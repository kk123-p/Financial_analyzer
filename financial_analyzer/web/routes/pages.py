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
    """主页面 — 返回 SPA 前端"""
    from fastapi.responses import FileResponse
    from pathlib import Path

    frontend_index = Path(__file__).parent.parent.parent.parent / "frontend" / "index.html"
    if frontend_index.exists():
        return FileResponse(str(frontend_index))
    # 回退到旧版 Jinja2 模板
    return templates.TemplateResponse(request, "base.html", {})
