"""FastAPI 应用工厂 + 生命周期管理"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from financial_analyzer.logging_config import setup_logging


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

    # 静态文件
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 注册路由
    from .routes import pages, data_api, analysis, charts_api, ai_api, export_api, settings_api
    app.include_router(pages.router)
    app.include_router(data_api.router)
    app.include_router(analysis.router)
    app.include_router(charts_api.router)
    app.include_router(ai_api.router)
    app.include_router(export_api.router)
    app.include_router(settings_api.router)

    return app
