"""FastAPI 应用工厂 + 生命周期管理"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from financial_analyzer.logging_config import setup_logging


def _get_app_dir() -> Path:
    """返回应用根目录（兼容 PyInstaller 打包和源码运行）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    # 关闭资源
    from .dependencies import get_cache
    try:
        get_cache().close()
    except Exception:
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="Financial Analyzer Pro",
        version="10.0.0",
        lifespan=lifespan,
    )

    # CORS — 允许 React 开发服务器和未来部署
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app_root = _get_app_dir()

    # 新前端 — 纯 HTML/CSS/JS SPA（挂载在 /static/frontend）
    # 必须先挂载更具体的路径，否则 /static 会抢先捕获 /static/frontend/* 请求
    frontend_dir = app_root / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend_static")

    # 静态文件
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 健康检查
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # 注册路由
    from .routes import pages, data_api, analysis, charts_api, ai_api, export_api, settings_api, api_v1, quant_api
    app.include_router(pages.router)
    app.include_router(data_api.router)
    app.include_router(analysis.router)
    app.include_router(charts_api.router)
    app.include_router(ai_api.router)
    app.include_router(export_api.router)
    app.include_router(settings_api.router)
    app.include_router(api_v1.router)
    app.include_router(quant_api.router)

    return app


app = create_app()
