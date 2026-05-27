"""模拟盘 API 路由"""
import logging
import os
import threading
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from financial_analyzer.quant.paper_trading.portfolio import PortfolioManager
from financial_analyzer.quant.paper_trading.ledger import TradeLedger
from financial_analyzer.quant.paper_trading.pnl import PnLTracker
from ..dependencies import get_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/paper", tags=["paper_trading"])

DATA_DIR = os.path.join(os.path.expanduser("~"), ".financialanalyzer", "paper_trading")

_lock = threading.Lock()
_portfolio: PortfolioManager | None = None


def _get_portfolio(initial_capital: float = 5000.0) -> PortfolioManager:
    global _portfolio
    if _portfolio is None:
        _portfolio = PortfolioManager(initial_capital=initial_capital)
        _portfolio.load()
    return _portfolio


def _trades_to_list(trades) -> list[dict]:
    return [
        {
            "date": t.date,
            "stock_code": t.stock_code,
            "stock_name": t.stock_name,
            "action": t.action,
            "price": t.price,
            "shares": t.shares,
            "commission": t.commission,
            "total_cost": t.total_cost,
        }
        for t in trades
    ]


def _snapshots_to_list(snapshots) -> list[dict]:
    return [
        {
            "date": s.date,
            "total_value": s.total_value,
            "cash": s.cash,
            "holdings_value": s.holdings_value,
            "unrealized_pnl": s.unrealized_pnl,
            "realized_pnl": s.realized_pnl,
            "total_pnl": s.total_pnl,
            "return_pct": s.return_pct,
        }
        for s in snapshots
    ]


@router.post("/init")
async def init_portfolio(
    capital: float = Query(5000.0, description="初始资金"),
):
    """初始化模拟盘"""
    with _lock:
        global _portfolio
        _portfolio = PortfolioManager(initial_capital=capital)
        _portfolio.save()
        holdings = _portfolio.get_holdings_summary()
        return JSONResponse({
            "status": "ok",
            "initial_capital": capital,
            "cash": _portfolio.cash,
            "holdings": holdings,
        })


@router.post("/execute")
async def execute_signals(
    task_id: str = Query(..., description="量化信号生成的 task_id"),
):
    """执行最新量化信号"""
    from financial_analyzer.web.routes.quant_api import _task_store, _task_lock

    with _task_lock:
        task = _task_store.get(task_id)

    if not task:
        return JSONResponse({"error": f"任务 {task_id} 不存在"}, status_code=404)
    if task.get("status") != "done":
        return JSONResponse({"error": "信号任务尚未完成"}, status_code=400)

    result = task.get("result", {})
    signals = result.get("signals", [])
    if not signals:
        return JSONResponse({"error": "无可用信号"}, status_code=400)

    from financial_analyzer.quant.models import TradeList, SignalResult
    from datetime import date as date_cls

    signal_results = []
    for s in signals:
        signal_results.append(SignalResult(
            stock_code=s["code"],
            stock_name=s["name"],
            action=s["action"],
            composite_score=s.get("score", 0.0),
            target_weight=s.get("weight", 0.0),
            reason=s.get("reason", ""),
        ))

    trade_list = TradeList(
        date=date_cls.today(),
        universe=result.get("universe", ""),
        signals=signal_results,
    )

    prices = {s["code"]: s.get("price", 0) for s in signals}

    # 补充缺失价格：对 price<=0 的股票从数据源获取最新价格
    missing_codes = [code for code, price in prices.items() if price <= 0]
    if missing_codes:
        logger.info(f"有 {len(missing_codes)} 只股票缺少价格，尝试从数据源获取...")
        from datetime import date as _date
        _adapter = get_adapter()
        _today_str = _date.today().strftime("%Y%m%d")
        for code in missing_codes:
            try:
                df = _adapter.get_stock_data(code, "20240101", _today_str, "daily")
                if df is not None and not df.empty and "close" in df.columns:
                    prices[code] = float(df.iloc[0]["close"])
                    logger.info(f"  获取 {code} 最新价格: {prices[code]}")
            except Exception as e:
                logger.warning(f"  获取 {code} 价格失败: {e}")

    with _lock:
        portfolio = _get_portfolio()
        executed = portfolio.execute_signals(trade_list, prices)
        portfolio.save()

    return JSONResponse({
        "executed": _trades_to_list(executed),
        "portfolio": portfolio.get_holdings_summary(),
        "cash": round(portfolio.cash, 2),
    })


@router.get("/portfolio")
async def get_portfolio():
    """获取当前持仓和盈亏"""
    with _lock:
        portfolio = _get_portfolio()
        holdings = portfolio.get_holdings_summary()
        total_value = portfolio.get_portfolio_value(
            {h["code"]: h["last_price"] for h in holdings}
        )
        return JSONResponse({
            "cash": round(portfolio.cash, 2),
            "total_value": round(total_value, 2),
            "holdings": holdings,
        })


@router.get("/ledger")
async def get_ledger():
    """获取交易流水"""
    with _lock:
        portfolio = _get_portfolio()
        return JSONResponse({
            "trades": _trades_to_list(portfolio.ledger.trades),
            "total_commission": round(portfolio.ledger.total_commission(), 2),
        })


@router.get("/pnl")
async def get_pnl():
    """获取盈亏历史快照"""
    with _lock:
        portfolio = _get_portfolio()
        tracker = portfolio.pnl_tracker
        latest = tracker.get_latest_snapshot()
        latest_dict = None
        if latest:
            latest_dict = {
                "date": latest.date,
                "total_value": latest.total_value,
                "total_pnl": latest.total_pnl,
                "return_pct": latest.return_pct,
            }
        return JSONResponse({
            "initial_capital": tracker.initial_capital,
            "realized_pnl": round(tracker.realized_pnl, 2),
            "latest": latest_dict,
            "snapshots": _snapshots_to_list(tracker.snapshots),
        })


@router.post("/reset")
async def reset_portfolio():
    """重置模拟盘"""
    with _lock:
        global _portfolio
        capital = _portfolio.initial_capital if _portfolio else 5000.0
        _portfolio = PortfolioManager(initial_capital=capital)
        _portfolio.save()
        return JSONResponse({
            "status": "ok",
            "initial_capital": capital,
            "cash": _portfolio.cash,
        })
