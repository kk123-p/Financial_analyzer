"""FastAPI 应用工厂 + 生命周期管理"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from financial_analyzer.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _get_app_dir() -> Path:
    """返回应用根目录（兼容 PyInstaller 打包和源码运行）"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


async def _scheduler_loop():
    """后台调度循环：每月末自动触发信号生成"""
    from financial_analyzer.quant.scheduler import SignalScheduler
    from financial_analyzer.data_sources.adapter import DataSourceAdapter
    from .dependencies import get_adapter

    adapter = get_adapter()
    scheduler = SignalScheduler(adapter=adapter, check_interval_hours=6)

    while True:
        try:
            await scheduler.run_if_due(_monthly_signal_callback)
        except Exception as e:
            logger.error(f"调度器异常: {e}")
        await asyncio.sleep(3600 * scheduler.check_interval)


async def _monthly_signal_callback():
    """月末自动信号生成回调"""
    from .routes.quant_api import run_signal_generation
    logger.info("月末自动触发信号生成...")
    # 触发沪深300信号生成
    await run_signal_generation(pool="沪深300", top_n=30)


async def _task_cleanup_loop():
    """定期清理过期任务（1小时TTL）"""
    import time
    while True:
        await asyncio.sleep(300)  # 每5分钟清理一次
        try:
            from .routes.quant_api import _task_store, _task_lock
            from .routes.backtest_api import _task_store as bt_store, _task_lock as bt_lock
            now = time.time()
            for store, lock in [(_task_store, _task_lock), (bt_store, bt_lock)]:
                with lock:
                    expired = [
                        tid for tid, task in store.items()
                        if task.get("status") in ("done", "error")
                        and now - task.get("started_ts", now) > 3600
                    ]
                    for tid in expired:
                        del store[tid]
                    if expired:
                        logger.info(f"清理过期任务: {len(expired)} 个")
        except Exception as e:
            logger.debug(f"任务清理跳过: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # 启动后台任务
    scheduler_task = asyncio.create_task(_scheduler_loop())
    cleanup_task = asyncio.create_task(_task_cleanup_loop())

    yield

    # 关闭后台任务
    scheduler_task.cancel()
    cleanup_task.cancel()

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
    from .routes import (
        pages, data_api, analysis, charts_api, ai_api, export_api,
        settings_api, api_v1, quant_api, backtest_api, paper_trading_api,
    )
    app.include_router(pages.router)
    app.include_router(data_api.router)
    app.include_router(analysis.router)
    app.include_router(charts_api.router)
    app.include_router(ai_api.router)
    app.include_router(export_api.router)
    app.include_router(settings_api.router)
    app.include_router(api_v1.router)
    app.include_router(quant_api.router)
    app.include_router(backtest_api.router)
    app.include_router(paper_trading_api.router)

    return app


app = create_app()
