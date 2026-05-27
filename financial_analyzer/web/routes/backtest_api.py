"""回测 API 路由"""
import json
import logging
import re
import threading
import uuid
from dataclasses import asdict
from datetime import datetime, date
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.data_fetcher import QuantDataFetcher
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.engine.signal import SignalGenerator
from financial_analyzer.quant.backtest.engine import BacktestEngine
from financial_analyzer.web.routes.quant_api import (
    ALL_FACTORS, DEFAULT_FACTOR_CONFIGS, _load_token,
)
from ..dependencies import get_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

_task_store: dict[str, dict] = {}
_task_lock = threading.Lock()


def _update_task(task_id: str, **kwargs):
    with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].update(kwargs)


def _serialize_result(result):
    """Convert BacktestResult to JSON-safe dict."""
    metrics_dict = None
    if result.metrics:
        metrics_dict = {
            "total_return": result.metrics.total_return,
            "annualized_return": result.metrics.annualized_return,
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "max_drawdown": result.metrics.max_drawdown,
            "win_rate": result.metrics.win_rate,
            "volatility": result.metrics.volatility,
            "calmar_ratio": result.metrics.calmar_ratio,
            "benchmark_return": result.metrics.benchmark_return,
            "monthly_returns": result.metrics.monthly_returns,
        }

    snapshots_list = []
    for s in result.snapshots:
        snapshots_list.append({
            "date": s.date,
            "holdings": s.holdings,
            "cash": s.cash,
            "total_value": s.total_value,
        })

    trades_list = []
    for trade_list in result.trades:
        period_trades = []
        for sig in trade_list.signals:
            period_trades.append({
                "code": sig.stock_code,
                "name": sig.stock_name,
                "action": sig.action,
                "score": round(sig.composite_score, 4),
                "weight": round(sig.target_weight, 4),
                "reason": sig.reason,
            })
        trades_list.append({
            "date": str(trade_list.date),
            "signals": period_trades,
        })

    return {
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_value": result.final_value,
        "metrics": metrics_dict,
        "snapshots": snapshots_list,
        "trades": trades_list,
        "attribution": result.attribution,
    }


@router.post("/run")
async def run_backtest(
    pool: str = Query("沪深300", description="选股池名称"),
    start_date: str = Query("20230101", description="回测起始日期 YYYYMMDD"),
    end_date: str = Query("20251231", description="回测结束日期 YYYYMMDD"),
    initial_capital: float = Query(5000.0, description="初始资金"),
):
    """启动回测任务（后台线程）"""
    # Validate date format
    date_pattern = re.compile(r'^\d{8}$')
    if not date_pattern.match(start_date):
        return JSONResponse({"error": "start_date 格式错误，应为 YYYYMMDD"}, status_code=400)
    if not date_pattern.match(end_date):
        return JSONResponse({"error": "end_date 格式错误，应为 YYYYMMDD"}, status_code=400)

    try:
        sd = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        ed = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
    except ValueError as e:
        return JSONResponse({"error": f"日期无效: {e}"}, status_code=400)

    if sd >= ed:
        return JSONResponse({"error": "start_date 必须早于 end_date"}, status_code=400)

    if ed > date.today():
        return JSONResponse({"error": "end_date 不能超过今天"}, status_code=400)

    task_id = uuid.uuid4().hex[:12]

    import time as _time
    with _task_lock:
        _task_store[task_id] = {
            "status": "starting",
            "progress": 0,
            "message": "正在初始化...",
            "started_at": datetime.now().isoformat(),
            "started_ts": _time.time(),
            "pool": pool,
            "start_date": start_date,
            "end_date": end_date,
        }

    def run_backtest_pipeline():
        try:
            _update_task(task_id, status="running", progress=5, message="加载 Tushare 连接...")
            adapter = get_adapter()
            _load_token(adapter)

            _update_task(task_id, progress=10, message="构建回测引擎组件...")

            mgr = UniverseManager(adapter)
            fetcher = QuantDataFetcher(adapter, start_date=start_date)
            builder = FactorMatrixBuilder(factors=ALL_FACTORS)
            normalizer = CrossSectionalNormalizer(method="zscore")
            scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
            ranker = Ranker(top_n=30)
            optimizer = ConstraintOptimizer()
            signal_gen = SignalGenerator()

            engine = BacktestEngine(
                universe_manager=mgr,
                data_fetcher=fetcher,
                factor_matrix_builder=builder,
                normalizer=normalizer,
                scorer=scorer,
                ranker=ranker,
                optimizer=optimizer,
                signal_generator=signal_gen,
            )

            _update_task(task_id, progress=20, message=f"开始回测 {start_date} ~ {end_date}...")

            result = engine.run(
                start_date=start_date,
                end_date=end_date,
                pool=pool,
                initial_capital=initial_capital,
            )

            _update_task(task_id, progress=90, message="序列化结果...")
            result_dict = _serialize_result(result)

            _update_task(task_id, status="done", progress=100, message="完成",
                         result=result_dict)

        except Exception as e:
            logger.error(f"回测失败: {e}", exc_info=True)
            _update_task(task_id, status="error", message=str(e))

    threading.Thread(target=run_backtest_pipeline, daemon=True).start()
    return JSONResponse({"task_id": task_id})


@router.get("/status/{task_id}")
async def backtest_status(task_id: str):
    """查询回测进度"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return JSONResponse({k: v for k, v in task.items() if k != "result"})


@router.get("/result/{task_id}")
async def backtest_result(task_id: str):
    """获取回测结果"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    if task["status"] == "done":
        return JSONResponse(task.get("result", {}))
    return JSONResponse({
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
    })
