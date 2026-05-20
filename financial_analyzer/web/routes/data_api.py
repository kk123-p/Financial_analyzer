"""数据获取 API — POST /fetch → htmx 局部更新"""
import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

from ..services.data_service import DataService
from ..dependencies import get_adapter, get_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fetch", tags=["data"])

_templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

# 简易 session
_sessions: dict[str, dict] = {}
DEFAULT_SESSION_ID = "default"

# 缓存配置，避免每次 /fetch 都读磁盘
_cached_token_config: dict | None = None
_token_config_loaded = False


def _get_session(request: Request) -> dict:
    sid = request.cookies.get("fa_session", DEFAULT_SESSION_ID)
    if sid not in _sessions:
        _sessions[sid] = {"data": {}, "stock_code": ""}
    return _sessions[sid]


def _load_and_apply_token(adapter):
    """从 config.json 加载 token 并应用到 adapter（首次读磁盘后缓存）"""
    global _cached_token_config, _token_config_loaded
    from financial_analyzer.config import CONFIG_FILE
    try:
        if not _token_config_loaded:
            _token_config_loaded = True
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    _cached_token_config = json.load(f)
        if _cached_token_config:
            tushare_token = _cached_token_config.get("tushare", "")
            if tushare_token and not adapter.tushare_pro:
                adapter.set_tushare_token(tushare_token)
                logger.info("已从配置加载 Tushare Token")
    except Exception as e:
        logger.warning(f"加载 Token 失败: {e}")


@router.post("")
async def fetch_data(
    request: Request,
    stock_code: str = Form(...),
    source: str = Form("tushare"),
    start_date: str = Form("20240101"),
):
    adapter = get_adapter()
    _load_and_apply_token(adapter)
    end_date = datetime.now().strftime("%Y%m%d")
    ds = DataService(adapter)

    # 获取基本行情数据
    def do_fetch_basic():
        return ds.fetch_stock_data(stock_code, start_date, end_date, source,
                                   include_financials=False)

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, do_fetch_basic)

    if not data:
        return _error_response(_diagnose_error(adapter, stock_code))

    # 保存数据到 session
    session = _get_session(request)
    session["data"] = {k: df.to_dict("records") for k, df in data.items()}
    session["stock_code"] = stock_code

    kpis = ds.extract_kpis(data)

    # 统计财务报表状态
    fin_types = DataService.FINANCIAL_DATA_TYPES
    fin_loaded = [k for k in fin_types if k in data and data[k]]
    fin_pending = [k for k in fin_types if k not in data or not data[k]]

    # 后台加载财务报表（使用 session ID 避免请求对象过期）
    if fin_pending:
        sid = request.cookies.get("fa_session", DEFAULT_SESSION_ID)

        def do_fetch_financials():
            return ds.fetch_financials_async(stock_code, start_date, end_date)

        async def background_financials():
            try:
                logger.info(f"开始后台加载财务报表: {fin_pending}")
                fin_data = await loop.run_in_executor(None, do_fetch_financials)
                # 确保使用正确的 session（必须存在）
                sess = _sessions.get(sid)
                if sess is None:
                    logger.error(f"后台任务: session {sid} 不存在")
                    return
                if fin_data:
                    for k, df in fin_data.items():
                        sess["data"][k] = df.to_dict("records")
                    logger.info(f"后台财务报表加载完成: {list(fin_data.keys())}")
                # 标记所有待加载类型（成功或失败都标记，避免一直显示加载中）
                for k in fin_pending:
                    if k not in sess["data"]:
                        sess["data"][k] = []
                logger.info(f"财务报表后台加载结束。已加载: {list(fin_data.keys()) if fin_data else '无'}")
            except Exception as e:
                logger.error(f"后台财务报表加载失败: {e}", exc_info=True)

        asyncio.create_task(background_financials())

    from fastapi.responses import HTMLResponse
    response = templates.TemplateResponse(request, "partials/kpi_cards.html", {
        "kpis": kpis,
        "stock_code": stock_code,
        "has_data": True,
        "data_types": sorted(data.keys()),
        "fin_loaded": fin_loaded,
        "fin_pending": fin_pending,
    })
    return response


@router.get("/financials-status")
async def financials_status(request: Request):
    """查询财务报表是否已加载完成"""
    session = _get_session(request)
    data = session.get("data", {})

    fin_types = DataService.FINANCIAL_DATA_TYPES
    loaded = [k for k in fin_types if k in data and data[k]]
    pending = [k for k in fin_types if k not in loaded]

    if not pending:
        # 全部加载完成：更新状态 + 触发数据表格刷新
        status_html = f"""
        <div id="fin-status" class="fin-status-done"
             hx-swap-oob="true">
            <span style="color:var(--success);">●</span> 财务数据加载完成
            ({', '.join(loaded) if loaded else '无'})
        </div>
        """
        from fastapi.responses import HTMLResponse
        resp = HTMLResponse(content=status_html)
        resp.headers["HX-Trigger"] = "refreshDataTable"
        return resp
    else:
        return HTMLResponse(f"""
        <div id="fin-status" class="fin-status-loading"
             hx-get="/fetch/financials-status" hx-trigger="every 2s" hx-swap="outerHTML">
            <span style="color:var(--warning);">◌</span> 正在加载财务数据...
            已加载: {', '.join(loaded) if loaded else '无'} | 等待: {', '.join(pending)}
        </div>
        """)


@router.get("/data-table")
async def data_table(request: Request):
    """返回最新的数据表格（供 htmx 刷新）"""
    session = _get_session(request)
    data = session.get("data", {})

    all_data_types = DataService.BASIC_DATA_TYPES + DataService.FINANCIAL_DATA_TYPES
    loaded = [k for k in all_data_types if k in data and data[k]]
    pending = [k for k in all_data_types if k not in loaded]

    rows = []
    for dtype in loaded:
        rows.append(f"""
        <tr>
            <td>{dtype}</td>
            <td style="color:var(--fg-muted);font-size:11px;">{dtype}</td>
            <td style="color:var(--success);">✓</td>
        </tr>""")

    if pending:
        rows.append(f"""
        <tr><td colspan="3" style="color:var(--warning);text-align:center;">
            ◌ 另有 {len(pending)} 项数据仍在等待加载...
        </td></tr>""")

    return HTMLResponse(f"""
    <div id="data-table-content"
         hx-get="/fetch/data-table" hx-trigger="refreshDataTable from:body" hx-swap="outerHTML">
        <table class="data-table">
            <thead><tr><th>数据类型</th><th>说明</th><th>状态</th></tr></thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
    </div>
    """)


def _diagnose_error(adapter, stock_code: str) -> str:
    from html import escape
    available = adapter.get_available_sources()
    tried = adapter.active_source
    has_token = bool(adapter.tushare_pro)
    lines = [
        f"无法获取 {escape(stock_code)} 的数据",
        f"尝试数据源: {tried.upper()} | 可用: {', '.join(available)}",
        f"Tushare Token: {'已配置' if has_token else '未配置'}",
    ]
    if not has_token and "akshare" in available:
        lines.append("建议: 使用 'akshare' 数据源 (无需Token)")
    if not has_token:
        lines.append("建议: 在左侧「Token 配置」设置 Tushare Token")
    return "<br>".join(lines)


@router.get("/status")
async def fetch_status(request: Request):
    """获取数据源状态"""
    import json
    from financial_analyzer.config import CONFIG_FILE

    adapter = get_adapter()
    config = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    available = adapter.get_available_sources()
    has_token = bool(adapter.tushare_pro)

    lines = ["数据源状态:", ""]
    for src in available:
        lines.append(f"  ● {src.upper()}: 可用")
    for src in ["tushare", "akshare", "sina", "yfinance"]:
        if src not in available:
            lines.append(f"  ○ {src.upper()}: 不可用（未安装 Python 包）")

    lines.append("")
    if has_token:
        lines.append("Tushare Token: 已配置")
    else:
        lines.append("Tushare Token: 未配置 → 建议使用 akshare 或 sina 数据源")

    return HTMLResponse("<br>".join(lines))


def _error_response(msg: str):
    from html import escape
    return HTMLResponse(
        content=f'<div class="error-toast" id="fetch-status">{escape(msg)}</div>',
        status_code=200,
    )
