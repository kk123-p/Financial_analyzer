"""
Ch8 现金流量表进阶分析 — 现金流5型画像 + 盈利质量
=================================================
整合《Python大数据财务分析》第8章 (lines 19-358)

5型画像逻辑 (lines 301-358):
  基于经营/投资/筹资三流正负号组合：
    妖精型: 经营+ 投资+ 筹资+
    老母鸡型: 经营+ 投资+ 筹资-
    蛮牛型: 经营+ 投资- 筹资+
    奶牛型: 经营+ 投资- 筹资-
    危险型: 经营-
"""
import pandas as pd
import numpy as np


def extract_cashflow_signs(
    cashflow_df: pd.DataFrame,
) -> dict[str, float | None]:
    """
    提取最近一期的经营/投资/筹资现金流净值

    Returns:
        {"ocf": float, "icf": float, "fcf": float}  # fcf = 筹资现金流
    """
    if cashflow_df is None or cashflow_df.empty:
        return {"ocf": None, "icf": None, "fcf": None}

    latest = cashflow_df.iloc[0]
    ocf_cols = ["n_cashflow_act", "经营活动现金流量净额"]
    icf_cols = ["n_cash_invest_act", "投资活动现金流量净额"]
    fcf_cols = ["n_cash_finance_act", "筹资活动现金流量净额"]  # fcf here = financing CF

    def _get(cols):
        for c in cols:
            if c in latest.index:
                v = latest[c]
                if pd.notna(v):
                    return float(v)
        return None

    return {
        "ocf": _get(ocf_cols),
        "icf": _get(icf_cols),
        "fcf": _get(fcf_cols),  # financing cashflow
    }


def classify_portrait(ocf: float | None, icf: float | None, fin_cf: float | None) -> dict:
    """
    现金流5型画像分类 — 完全复现教科书 Ch8 lines 301-358

    Returns:
        {
            "type": str,          # "奶牛型" / "妖精型" / etc
            "type_cn": str,       # 完整中文描述
            "danger": bool,       # 是否有危险
            "description": str,   # 投资含义解读
        }
    """
    if ocf is None:
        return {"type": "unknown", "type_cn": "数据不足", "danger": False, "description": ""}

    if ocf <= 0:
        return {
            "type": "danger",
            "type_cn": "危险型",
            "danger": True,
            "description": "经营现金流为负，企业自身造血能力不足，需警惕流动性风险",
        }

    inv_pos = icf is not None and icf > 0
    fin_pos = fin_cf is not None and fin_cf > 0

    if inv_pos and fin_pos:
        return {
            "type": "yaojing",
            "type_cn": "妖精型",
            "danger": False,
            "description": "经营赚钱+投资赚钱+筹资流入，钱多到用不完，关注资金使用效率",
        }
    elif inv_pos and not fin_pos:
        return {
            "type": "laomuji",
            "type_cn": "老母鸡型",
            "danger": False,
            "description": "经营赚钱+投资回报，同时偿还债务或分红，财务状况稳健",
        }
    elif not inv_pos and fin_pos:
        return {
            "type": "manniu",
            "type_cn": "蛮牛型",
            "danger": False,
            "description": "经营赚钱但不够投资，靠外部融资支撑扩张，关注投资回报何时转正",
        }
    else:
        return {
            "type": "nailao",
            "type_cn": "奶牛型",
            "danger": False,
            "description": "经营赚钱支撑投资+偿债，成熟期现金牛企业，自由现金流充裕",
        }


def multi_year_portrait(
    cashflow_df: pd.DataFrame,
    years: int = 5,
) -> list[dict]:
    """
    多年现金流画像变迁 — 仿教科书 Ch8 多年分析思路

    Returns:
        [{year: str, type: str, type_cn: str, ocf: float, ...}, ...]
    """
    if cashflow_df is None or cashflow_df.empty:
        return []

    results = []
    for i in range(min(years, len(cashflow_df))):
        row = cashflow_df.iloc[i]
        signs = extract_cashflow_signs(pd.DataFrame([row]))
        portrait = classify_portrait(signs["ocf"], signs["icf"], signs["fcf"])
        period = str(row.get("end_date", row.get("trade_date", f"期间{i}")))
        results.append({
            "period": period[:10] if len(period) > 10 else period,
            "ocf": signs["ocf"],
            "icf": signs["icf"],
            "fin_cf": signs["fcf"],
            **portrait,
        })
    return results


def stability_assessment(portraits: list[dict]) -> str:
    """
    现金流画像稳定性评估

    Returns:
        "高度稳定" / "基本稳定" / "波动较大" / "趋势恶化" / "趋势改善"
    """
    if not portraits or len(portraits) < 2:
        return "数据不足"

    types = [p.get("type") for p in portraits]

    # 所有年份同型 = 高度稳定
    if len(set(types)) == 1:
        return "高度稳定"

    # 仅奶牛和蛮牛之间切换 = 基本稳定
    stable_types = {"nailao", "manniu", "laomuji"}
    if all(t in stable_types for t in types):
        return "基本稳定"

    # 最近一年变为危险 = 趋势恶化
    if types[0] == "danger":
        return "趋势恶化"

    # 从危险变为其他 = 趋势改善
    if types[-1] == "danger" and types[0] != "danger":
        return "趋势改善"

    return "波动较大"
