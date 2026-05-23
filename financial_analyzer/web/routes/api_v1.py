"""JSON REST API v1 — 供前端调用"""
import asyncio
import json
import logging
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..services.data_service import DataService
from ..services.analysis_service import AnalysisService, get_analysis_list, get_pipeline_stages
from ..dependencies import get_adapter, get_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["api"])

from .data_api import _get_session, _load_and_apply_token

_config_dir = Path.home() / ".financialanalyzer"


# ============================================================================
# 数据获取
# ============================================================================

@router.post("/fetch")
async def api_fetch_data(request: Request):
    """获取股票数据 → JSON"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    stock_code = body.get("stock_code", "")
    source = body.get("source", "tushare")
    start_date = body.get("start_date", "20240101")

    if not stock_code:
        return JSONResponse({"success": False, "error": "缺少 stock_code"}, status_code=400)

    adapter = get_adapter()
    _load_and_apply_token(adapter)
    cache = get_cache()
    data_service = DataService(adapter)

    session = _get_session(request)
    session["stock_code"] = stock_code
    session["source"] = source

    try:
        result = data_service.fetch_stock_data(stock_code, start_date)
        session["data"] = result.get("data", {})

        kpis = data_service.extract_kpis(result.get("data", {}))

        data_types = list(result.get("data", {}).keys())
        financial_ready = all(
            t in result.get("data", {}) and result["data"][t] is not None and
            (not hasattr(result["data"][t], 'empty') or not result["data"][t].empty)
            for t in ["income", "balance", "cashflow"]
        )

        return JSONResponse({
            "success": True,
            "stock_code": stock_code,
            "kpis": kpis,
            "data_types": data_types,
            "financial_ready": financial_ready,
        })
    except Exception as e:
        logger.error(f"数据获取失败: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============================================================================
# 分析
# ============================================================================

@router.get("/analyze/{analysis_type}")
async def api_run_analysis(request: Request, analysis_type: str):
    """运行指定分析 → JSON"""
    session = _get_session(request)
    data = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data or not stock_code:
        return JSONResponse({"success": False, "error": "请先获取股票数据"}, status_code=400)

    adapter = get_adapter()
    cache = get_cache()
    analysis_service = AnalysisService(adapter, cache)

    import asyncio
    loop = asyncio.get_event_loop()
    result_text = await loop.run_in_executor(
        None, analysis_service.run, analysis_type, data, stock_code
    )

    from ..services.result_formatter import ResultFormatter
    result_html = ResultFormatter.format(result_text)

    return JSONResponse({
        "success": True,
        "analysis_type": analysis_type,
        "result_text": result_text,
        "result_html": result_html,
    })


# ============================================================================
# AI 对话
# ============================================================================

@router.post("/ai/chat")
async def api_ai_chat(request: Request):
    """AI 分析对话 → JSON"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    question = body.get("question", "")
    stock_code = body.get("stock_code", "")

    if not question:
        return JSONResponse({"success": False, "error": "缺少 question"}, status_code=400)

    from financial_analyzer.ai.report_builder import ReportBuilder
    from financial_analyzer.deepseek.client import DeepSeekClient, DeepSeekConfig

    config_path = _config_dir / "config.json"
    api_key = ""
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            api_key = config.get("deepseek_api_key", "") or config.get("deepseek", {}).get("api_key", "")

    if not api_key:
        return JSONResponse({"success": False, "error": "未配置 DeepSeek API Key"}, status_code=400)

    try:
        session = _get_session(request)
        data = session.get("data", {})
        sc = stock_code or session.get("stock_code", "")

        report = ReportBuilder.build(data, sc)
        import pandas as pd
        report_text = json.dumps(report, ensure_ascii=False, default=str)

        client = DeepSeekClient(config=DeepSeekConfig(api_key=api_key))
        system_prompt = "你是一位专业的中国A股财务分析师，请基于提供的财务数据进行分析。"
        user_prompt = f"以下是公司 {sc} 的财务数据：\n\n{report_text}\n\n问题：{question}"

        result = client.generate_deep_analysis(
            user_prompt, system_prompt=system_prompt
        )

        return JSONResponse({
            "success": True,
            "content": result.content if result.success else f"分析失败: {result.error}",
        })
    except Exception as e:
        logger.error(f"AI 分析失败: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============================================================================
# 分析类型列表
# ============================================================================

@router.get("/analysis-types")
async def api_analysis_types():
    """返回所有38种分析类型"""
    return JSONResponse({
        "pipeline_stages": [
            {"stage": s[0], "entry": s[1], "items": [{"key": i[0], "label": i[1]} for i in s[2]]}
            for s in get_pipeline_stages()
        ],
        "flat_list": [
            {"key": i[0], "label": i[1]}
            for g in get_analysis_list() for i in g[1]
        ],
    })


# ============================================================================
# 设置状态
# ============================================================================

@router.get("/settings/status")
async def api_settings_status():
    """数据源和 Token 状态"""
    adapter = get_adapter()
    sources = adapter.get_available_sources()

    config_path = _config_dir / "config.json"
    has_tushare = False
    has_deepseek = False
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            has_tushare = bool(config.get("tushare", ""))
            has_deepseek = bool(config.get("deepseek_api_key", "") or config.get("deepseek", {}).get("api_key", ""))

    return JSONResponse({
        "sources": sources,
        "active_source": getattr(adapter, '_active_source', 'unknown'),
        "has_tushare": has_tushare,
        "has_deepseek": has_deepseek,
    })


@router.post("/settings/tokens")
async def api_save_tokens(request: Request):
    """保存 Token 配置"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    tushare_token = body.get("tushare_token", "")
    deepseek_key = body.get("deepseek_key", "")

    config_path = _config_dir / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    if tushare_token:
        config["tushare"] = tushare_token
        adapter = get_adapter()
        adapter.set_tushare_token(tushare_token)
    if deepseek_key:
        config["deepseek_api_key"] = deepseek_key

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return JSONResponse({"success": True, "message": "Token 已保存"})


# ============================================================================
# 流式 AI 对话 (SSE)
# ============================================================================

def _load_deepseek_config():
    config_path = _config_dir / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@router.post("/ai/chat/stream")
async def api_ai_chat_stream(request: Request):
    """AI 分析对话 → Server-Sent Events 流式响应"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    question = body.get("question", "")
    stock_code = body.get("stock_code", "")

    if not question:
        return JSONResponse({"success": False, "error": "缺少 question"}, status_code=400)

    config = _load_deepseek_config()
    api_key = config.get("deepseek_api_key", "") or config.get("deepseek", {}).get("api_key", "")
    if not api_key:
        return JSONResponse({"success": False, "error": "未配置 DeepSeek API Key"}, status_code=400)

    from financial_analyzer.ai.report_builder import ReportBuilder
    from financial_analyzer.deepseek.client import DeepSeekStreamClient, DeepSeekConfig

    session = _get_session(request)
    data = session.get("data", {})
    sc = stock_code or session.get("stock_code", "")

    report = ReportBuilder.build(data, sc)
    report_text = json.dumps(report, ensure_ascii=False, default=str)

    system_prompt = "你是一位专业的中国A股财务分析师，请基于提供的财务数据进行分析。"
    user_prompt = f"以下是公司 {sc} 的财务数据：\n\n{report_text}\n\n问题：{question}"

    client = DeepSeekStreamClient(config=DeepSeekConfig(api_key=api_key))

    async def generate():
        queue = asyncio.Queue()
        def callback(chunk: str, done: bool):
            try:
                queue.put_nowait((chunk, done))
            except asyncio.QueueFull:
                pass

        import threading
        def stream_call():
            client.generate_deep_analysis_stream(
                user_prompt, system_prompt=system_prompt, callback=callback
            )

        thread = threading.Thread(target=stream_call, daemon=True)
        thread.start()

        while True:
            try:
                chunk, done = await asyncio.wait_for(queue.get(), timeout=60)
                yield f"data: {json.dumps({'chunk': chunk, 'done': done}, ensure_ascii=False)}\n\n"
                if done:
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'error': '请求超时'})}\n\n"
                break

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================================
# 结构化数据摘要
# ============================================================================

@router.get("/data/summary")
async def api_data_summary(request: Request):
    """返回当前 session 的结构化财务数据摘要"""
    session = _get_session(request)
    data = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data or not stock_code:
        return JSONResponse({"success": False, "error": "请先获取股票数据"}, status_code=400)

    summary = {"stock_code": stock_code}

    # 行情数据
    basic = data.get("basic")
    if basic is not None and not basic.empty:
        latest = basic.iloc[0]
        summary["price"] = _safe_val(latest, ["close", "收盘价"])
        summary["total_share"] = _safe_val(latest, ["total_share", "总股本"])
        if summary["price"] and summary["total_share"]:
            summary["market_cap_yi"] = round(summary["price"] * summary["total_share"] / 1e4, 2)

    # 最新财务数据
    income = data.get("income")
    balance = data.get("balance")
    cashflow = data.get("cashflow")

    if income is not None and not income.empty:
        inc = income.iloc[0]
        np_val = _safe_val(inc, ["net_profit", "净利润"])
        rev = _safe_val(inc, ["revenue", "total_revenue", "营业收入"])
        summary["revenue_yi"] = round(rev / 1e8, 2) if rev else None
        summary["net_profit_yi"] = round(np_val / 1e8, 2) if np_val else None
        if rev and rev > 0:
            op_cost = _safe_val(inc, ["oper_cost", "营业支出"])
            if op_cost:
                summary["gross_margin"] = round((rev - op_cost) / rev * 100, 2)
            summary["net_margin"] = round(np_val / rev * 100, 2) if np_val else None

    if balance is not None and not balance.empty:
        bal = balance.iloc[0]
        ta = _safe_val(bal, ["total_assets", "资产总计"])
        tl = _safe_val(bal, ["total_liab", "负债合计"])
        eq = _safe_val(bal, ["total_equity", "股东权益合计"])
        summary["total_assets_yi"] = round(ta / 1e8, 2) if ta else None
        summary["debt_ratio"] = round(tl / ta * 100, 2) if tl and ta else None
        summary["roe"] = round(np_val / eq * 100, 2) if np_val and eq and eq > 0 else None
        if summary["price"] and summary["total_share"] and eq:
            summary["pb"] = round(summary["price"] * summary["total_share"] / (eq * 10000), 2)

    if cashflow is not None and not cashflow.empty:
        cf = cashflow.iloc[0]
        ocf = _safe_val(cf, ["n_cashflow_act", "经营活动现金流量净额"])
        summary["op_cashflow_yi"] = round(ocf / 1e8, 2) if ocf else None
        summary["cf_np_ratio"] = round(ocf / np_val, 2) if ocf and np_val and np_val != 0 else None

    summary["data_types"] = [k for k in data.keys() if data[k] is not None and not (hasattr(data[k], 'empty') and data[k].empty)]

    return JSONResponse({"success": True, "summary": summary})


# ============================================================================
# 批量分析
# ============================================================================

@router.post("/analyze/batch")
async def api_run_batch_analysis(request: Request):
    """批量运行多个分析类型 → JSON"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    types = body.get("types", [])

    if not types:
        return JSONResponse({"success": False, "error": "缺少 types 参数"}, status_code=400)

    session = _get_session(request)
    data = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data or not stock_code:
        return JSONResponse({"success": False, "error": "请先获取股票数据"}, status_code=400)

    adapter = get_adapter()
    cache = get_cache()
    analysis_service = AnalysisService(adapter, cache)
    loop = asyncio.get_event_loop()

    from ..services.result_formatter import ResultFormatter

    results = {}
    for atype in types:
        try:
            text = await loop.run_in_executor(None, analysis_service.run, atype, data, stock_code)
            results[atype] = {
                "success": True,
                "result_text": text,
                "result_html": ResultFormatter.format(text),
            }
        except Exception as e:
            results[atype] = {"success": False, "error": str(e)}

    return JSONResponse({"success": True, "results": results})


# ============================================================================
# 缓存管理
# ============================================================================

@router.get("/cache/stats")
async def api_cache_stats():
    """缓存统计信息"""
    cache = get_cache()
    stats = cache.get_stats()
    # 补充内存缓存信息
    memory_keys = list(cache.memory_cache.keys()) if hasattr(cache, 'memory_cache') else []
    stats["memory_entries"] = len(memory_keys)
    stats["memory_keys"] = memory_keys[:20]
    return JSONResponse({"success": True, "stats": stats})


@router.post("/cache/clear")
async def api_cache_clear(request: Request):
    """清除缓存"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    data_type = body.get("data_type")
    symbol = body.get("symbol")
    cache = get_cache()
    cache.clear_cache(data_type=data_type, symbol=symbol)
    return JSONResponse({"success": True, "message": "缓存已清除"})


def _safe_val(row, keys: list):
    """从DataFrame行中安全提取数值"""
    if row is None:
        return None
    for k in keys:
        if k in row.index:
            v = row[k]
            try:
                if pd.notna(v):
                    return float(v)
            except (ValueError, TypeError):
                pass
    return None
