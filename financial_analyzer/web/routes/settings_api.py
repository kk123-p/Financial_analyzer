"""Token 配置 & 设置 API — 不依赖 DataSourceAdapter，避免阻塞"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from financial_analyzer.config import CONFIG_FILE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_enabled_modules() -> dict:
    """返回已启用的数据模块配置"""
    config = _load_config()
    defaults = {k: True for k in [
        "moneyflow", "margin", "hk_hold", "block_trade",
        "stk_holdernumber", "top10_holders", "dividend", "weekly_monthly"
    ]}
    saved = config.get("data_modules", {})
    defaults.update(saved)
    return defaults


def _check_package(pkg_name: str) -> bool:
    """检查 Python 包是否已安装"""
    try:
        __import__(pkg_name)
        return True
    except ImportError:
        return False


@router.get("/tokens")
async def get_tokens(request: Request):
    """Token 配置页面"""
    config = _load_config()

    has_tushare = bool(config.get("tushare"))
    has_deepseek = bool(config.get("deepseek_api_key"))

    source_status = {
        "tushare": "available" if _check_package("tushare") else "未安装",
        "akshare": "available" if _check_package("akshare") else "未安装",
        "sina": "available",
        "yfinance": "available" if _check_package("yfinance") else "未安装",
    }

    module_labels = {
        "moneyflow": "资金流向", "margin": "融资融券", "hk_hold": "北向资金",
        "block_trade": "大宗交易", "stk_holdernumber": "股东人数",
        "top10_holders": "前十大股东", "dividend": "分红数据",
        "weekly_monthly": "周线/月线",
    }
    default_mods = config.get("data_modules", {})
    module_html = '<h4 style="color:var(--fg-secondary);font-size:12px;margin:16px 0 4px 0;">数据模块（勾选启用）</h4>'
    for key, label in module_labels.items():
        checked = "checked" if default_mods.get(key, True) else ""
        module_html += f'<div style="font-size:11px;padding:2px 0;"><label><input type="checkbox" name="module_{key}" {checked}> {label}</label></div>'

    return HTMLResponse(f"""
    <div id="token-status-content">
        <h3 style="color:var(--accent);margin:0 0 16px 0;">Token 配置</h3>
        <form hx-post="/settings/save-tokens" hx-target="#token-status-content" hx-swap="outerHTML">
            <div style="margin-bottom:14px;">
                <label style="color:var(--fg-secondary);font-size:12px;font-weight:600;">Tushare Pro Token</label>
                <input type="password" name="tushare_token" value="{config.get('tushare', '')}"
                       style="width:100%;padding:8px;background:var(--bg-input);border:1px solid var(--border);color:var(--fg-primary);border-radius:6px;margin-top:4px;box-sizing:border-box;"
                       placeholder="输入 Tushare Token (注册: tushare.pro)">
                <div style="font-size:10px;color:var(--fg-muted);margin-top:4px;">
                    状态: {"已配置" if has_tushare else "未配置"} | 包: {source_status['tushare']}
                </div>
            </div>
            <div style="margin-bottom:14px;">
                <label style="color:var(--fg-secondary);font-size:12px;font-weight:600;">DeepSeek API Key</label>
                <input type="password" name="deepseek_key" value="{config.get('deepseek_api_key', '')}"
                       style="width:100%;padding:8px;background:var(--bg-input);border:1px solid var(--border);color:var(--fg-primary);border-radius:6px;margin-top:4px;box-sizing:border-box;"
                       placeholder="输入 DeepSeek API Key (注册: platform.deepseek.com)">
                <div style="font-size:10px;color:var(--fg-muted);margin-top:4px;">
                    状态: {"已配置" if has_deepseek else "未配置"}
                </div>
            </div>
            {module_html}
            <div style="margin-bottom:14px;">
                <h4 style="color:var(--fg-secondary);font-size:12px;margin:0 0 4px 0;">数据源包状态</h4>
                {"".join(f'<div style="font-size:11px;padding:1px 0;color:{"var(--success)" if v == "available" else "var(--danger)"}">{"●" if v == "available" else "○"} {k.upper()}: {v}</div>' for k, v in source_status.items())}
            </div>
            <div style="display:flex;gap:8px;margin-top:14px;">
                <button type="submit" class="btn btn-accent">保存 Token</button>
                <button type="button" class="btn" onclick="closeModal('token-modal')">关闭</button>
            </div>
        </form>
    </div>
    """)


@router.post("/save-tokens")
async def save_tokens(
    request: Request,
    tushare_token: str = Form(""),
    deepseek_key: str = Form(""),
):
    config = _load_config()
    messages = []

    # 保存 Tushare Token
    if tushare_token.strip():
        config["tushare"] = tushare_token.strip()
        messages.append("Tushare Token 已保存")

        # 尝试应用 Token 到 adapter
        try:
            from ..dependencies import get_adapter
            adapter = get_adapter()
            if adapter:
                success = adapter.set_tushare_token(tushare_token.strip())
                if success:
                    messages.append("Token 验证成功")
                else:
                    messages.append("Token 已保存（请手动验证）")
        except Exception as e:
            logger.warning(f"应用 Token 时出错: {e}")
            messages.append("Token 已保存（应用时出错，请刷新后重试）")
    elif tushare_token == "" and "tushare" in config:
        # 保留原有 token，不做更改
        pass

    # 保存 DeepSeek Key
    if deepseek_key.strip():
        config["deepseek_api_key"] = deepseek_key.strip()
        messages.append("DeepSeek API Key 已保存")
        # 清除 AI 配置缓存
        try:
            from .ai_api import invalidate_ai_config
            invalidate_ai_config()
        except Exception:
            pass

    # 保存数据模块配置
    module_keys = ["moneyflow", "margin", "hk_hold", "block_trade",
                   "stk_holdernumber", "top10_holders", "dividend", "weekly_monthly"]
    data_modules = {}
    form_data = await request.form()
    for key in module_keys:
        data_modules[key] = f"module_{key}" in form_data
    config["data_modules"] = data_modules

    _save_config(config)
    msg_html = "<br>".join(messages) if messages else "配置未更改"

    has_tushare = bool(config.get("tushare"))
    has_deepseek = bool(config.get("deepseek_api_key"))

    module_labels = {
        "moneyflow": "资金流向", "margin": "融资融券", "hk_hold": "北向资金",
        "block_trade": "大宗交易", "stk_holdernumber": "股东人数",
        "top10_holders": "前十大股东", "dividend": "分红数据",
        "weekly_monthly": "周线/月线",
    }
    default_mods = config.get("data_modules", {})
    module_html = '<h4 style="color:var(--fg-secondary);font-size:12px;margin:16px 0 4px 0;">数据模块（勾选启用）</h4>'
    for key, label in module_labels.items():
        checked = "checked" if default_mods.get(key, True) else ""
        module_html += f'<div style="font-size:11px;padding:2px 0;"><label><input type="checkbox" name="module_{key}" {checked}> {label}</label></div>'

    return HTMLResponse(f"""
    <div id="token-status-content">
        <h3 style="color:var(--accent);margin:0 0 16px 0;">Token 配置</h3>
        <div style="color:var(--success);font-size:12px;margin-bottom:8px;background:var(--accent-subtle);padding:8px;border-radius:6px;">{msg_html}</div>
        <form hx-post="/settings/save-tokens" hx-target="#token-status-content" hx-swap="outerHTML">
            <div style="margin-bottom:14px;">
                <label style="color:var(--fg-secondary);font-size:12px;font-weight:600;">Tushare Pro Token</label>
                <input type="password" name="tushare_token" value="{config.get('tushare', '')}"
                       style="width:100%;padding:8px;background:var(--bg-input);border:1px solid var(--border);color:var(--fg-primary);border-radius:6px;margin-top:4px;box-sizing:border-box;"
                       placeholder="输入 Tushare Token">
                <div style="font-size:10px;color:var(--fg-muted);margin-top:4px;">
                    状态: {"已配置" if has_tushare else "未配置"}
                </div>
            </div>
            <div style="margin-bottom:14px;">
                <label style="color:var(--fg-secondary);font-size:12px;font-weight:600;">DeepSeek API Key</label>
                <input type="password" name="deepseek_key" value="{config.get('deepseek_api_key', '')}"
                       style="width:100%;padding:8px;background:var(--bg-input);border:1px solid var(--border);color:var(--fg-primary);border-radius:6px;margin-top:4px;box-sizing:border-box;"
                       placeholder="输入 DeepSeek API Key">
                <div style="font-size:10px;color:var(--fg-muted);margin-top:4px;">
                    状态: {"已配置" if has_deepseek else "未配置"}
                </div>
            </div>
            {module_html}
            <div style="display:flex;gap:8px;margin-top:14px;">
                <button type="submit" class="btn btn-accent">保存 Token</button>
                <button type="button" class="btn" onclick="closeModal('token-modal')">关闭</button>
            </div>
        </form>
    </div>
    """)
