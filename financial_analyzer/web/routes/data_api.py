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


def _get_session(request: Request) -> dict:
    sid = request.cookies.get("fa_session", DEFAULT_SESSION_ID)
    if sid not in _sessions:
        _sessions[sid] = {"data": {}, "stock_code": ""}
    return _sessions[sid]


def _load_and_apply_token(adapter):
    """从 config.json 加载 token 并应用到 adapter"""
    from financial_analyzer.config import CONFIG_FILE
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            tushare_token = config.get("tushare", "")
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

    # 确保 token 已加载
    _load_and_apply_token(adapter)

    end_date = datetime.now().strftime("%Y%m%d")

    # 在线程池中执行同步数据获取（避免阻塞事件循环）
    ds = DataService(adapter)

    def do_fetch():
        return ds.fetch_stock_data(stock_code, start_date, end_date, source)

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, do_fetch)

    if not data:
        # 详细的诊断信息
        available = adapter.get_available_sources()
        tried_source = adapter.active_source
        has_token = bool(adapter.tushare_pro)

        diag_lines = [
            f"无法获取 {stock_code} 的数据",
            f"",
            f"尝试数据源: {tried_source.upper()}",
            f"可用数据源: {', '.join(available)}",
            f"Tushare Token: {'已配置' if has_token else '未配置'}",
            f"",
            f"建议:",
        ]
        if not has_token and "akshare" in available:
            diag_lines.append("  - 使用数据源 'akshare' (无需Token)")
        if not has_token:
            diag_lines.append("  - 在左侧「Token 配置」中设置 Tushare Token")
        diag_lines.append("  - 检查股票代码格式 (A股: 000001.SZ, 600519.SH)")
        diag_lines.append("  - 检查起始日期是否有效")

        return _error_response("<br>".join(diag_lines))

    # 保存到 session
    session = _get_session(request)
    session["data"] = {k: df.to_dict("records") for k, df in data.items()}
    session["stock_code"] = stock_code

    kpis = ds.extract_kpis(data)

    return templates.TemplateResponse(request, "partials/kpi_cards.html", {
        "kpis": kpis,
        "stock_code": stock_code,
        "has_data": True,
        "data_types": list(data.keys()),
    })


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
    return HTMLResponse(
        content=f'<div class="error-toast" id="fetch-status">{msg}</div>',
        status_code=200,
    )
