"""
Ch9 + 附录: 杜邦分析 + ROIC + 行业话语权
========================================
整合《Python大数据财务分析》：
  - Ch9 杜邦分析 (lines 72-132, 164-192, 194-234)
  - 附录1: 行业话语权分析 (营运负债/营运资产)
  - 附录2-4: 资产负债表重构 + ROIC计算
"""
import pandas as pd
import numpy as np
from typing import Any


def dupont_3factor(
    net_profit: float | None,
    revenue: float | None,
    total_assets: float | None,
    equity: float | None,
) -> dict[str, float]:
    """
    杜邦三因子分解 — 复现教科书 Ch9 lines 59-66

    ROE = 净利率 × 总资产周转率 × 权益乘数
    """
    result: dict[str, float] = {}
    if not all(v is not None and v > 0 for v in [net_profit, revenue, total_assets, equity]):
        return result

    net_margin = net_profit / revenue
    asset_turnover = revenue / total_assets
    equity_multiplier = total_assets / equity
    roe = net_margin * asset_turnover * equity_multiplier

    result["ROE"] = round(roe * 100, 2)
    result["销售净利率"] = round(net_margin * 100, 2)
    result["总资产周转率"] = round(asset_turnover, 4)
    result["权益乘数"] = round(equity_multiplier, 2)
    return result


def dupont_5factor(
    net_profit: float | None,
    pretax_profit: float | None,
    ebit: float | None,
    revenue: float | None,
    total_assets: float | None,
    equity: float | None,
) -> dict[str, float]:
    """
    杜邦五因子分解（增强版）

    ROE = 税负效应 × 利息效应 × 营业利润率 × 总资产周转率 × 权益乘数

    复现教科书 Ch9 的扩展分析思路
    """
    result: dict[str, float] = {}
    if not all(v is not None and v > 0 for v in [net_profit, revenue, total_assets, equity]):
        return result

    tax_burden = net_profit / pretax_profit if pretax_profit and pretax_profit > 0 else 0.75
    interest_burden = pretax_profit / ebit if ebit and ebit > 0 else 1.0
    op_margin = ebit / revenue if ebit and revenue > 0 else 0
    asset_turnover = revenue / total_assets if total_assets > 0 else 0
    equity_multiplier = total_assets / equity if equity > 0 else 0
    roe = tax_burden * interest_burden * op_margin * asset_turnover * equity_multiplier

    result["ROE"] = round(roe * 100, 2)
    result["税负效应"] = round(tax_burden, 4)
    result["利息效应"] = round(interest_burden, 4)
    result["营业利润率"] = round(op_margin * 100, 2)
    result["总资产周转率"] = round(asset_turnover, 4)
    result["权益乘数"] = round(equity_multiplier, 2)
    return result


def classify_dupont_driver(
    net_margin: float,
    asset_turnover: float,
    equity_multiplier: float,
) -> str:
    """
    三种盈利模式分类 — 复现教科书 Ch9 lines 164-192

    高利润率驱动：净利率 > 行业平均(>15%)
    高周转率驱动：总资产周转率 > 1
    高杠杆率驱动：权益乘数 > 3
    均衡驱动：以上均不满足
    """
    margin_high = net_margin > 15
    turnover_high = asset_turnover > 1.0
    leverage_high = equity_multiplier > 3.0

    score_margin = net_margin / 15
    score_turnover = asset_turnover / 1.0
    score_leverage = equity_multiplier / 3.0

    drivers = []
    if margin_high:
        drivers.append(("高利润率驱动型", score_margin))
    if turnover_high:
        drivers.append(("高周转率驱动型", score_turnover))
    if leverage_high:
        drivers.append(("高杠杆率驱动型", score_leverage))

    if drivers:
        drivers.sort(key=lambda x: x[1], reverse=True)
        return drivers[0][0]

    return "均衡驱动型"


def roe_screening(periods: list[dict], threshold: float, required_years: int) -> bool:
    """
    ROE连续筛选 — 复现教科书 Ch9 lines 72-132

    三层筛选：
      连续3年 ROE > 20%
      连续5年 ROE > 15%
      连续10年 ROE > 12%
    """
    if len(periods) < required_years:
        return False

    roe_values = []
    for p in periods[:required_years]:
        roe = p.get("roe")
        if roe is not None and not (isinstance(roe, float) and np.isnan(roe)):
            roe_values.append(float(roe))

    if len(roe_values) < required_years:
        return False

    return all(r > threshold for r in roe_values)


def calculate_roic(
    ebit: float | None,
    income_tax: float | None,
    pretax_profit: float | None,
    short_debt: float,
    long_debt: float,
    equity: float,
) -> float | None:
    """
    ROIC计算 — 复现教科书 Ch9 lines 194-234

    ROIC = EBIT × (1 - 实际税率) / (短期有息债务 + 长期有息债务 + 股东权益)

    实际税率 = 所得税费用 / 利润总额
    """
    if ebit is None or ebit == 0:
        return None

    # 实际税率
    if pretax_profit and pretax_profit > 0 and income_tax is not None:
        tax_rate = income_tax / pretax_profit
        tax_rate = max(0, min(0.5, tax_rate))  # 限制在0-50%
    else:
        tax_rate = 0.25

    invested_capital = short_debt + long_debt + equity
    if invested_capital <= 0:
        return None

    return round(ebit * (1 - tax_rate) / invested_capital * 100, 2)


def compute_bargaining_power(
    balance_df: pd.DataFrame | None,
) -> float | None:
    """
    行业话语权分析 — 复现教科书 附录1

    营运资产 = 存货 + 应收账款 + 应收票据 + 预付款项 + 长期应收款
    营运负债 = 应付账款 + 应付票据 + 预收款项 + 应付职工薪酬 + 应交税费

    行业话语权强度 = 营运负债 / 营运资产
    值越高，表示公司对上下游的议价能力越强
    """
    if balance_df is None or balance_df.empty:
        return None

    row = balance_df.iloc[0]

    def _v(cols):
        for c in cols:
            if c in row.index:
                v = row[c]
                if pd.notna(v):
                    return float(v)
        return 0.0

    # 营运资产
    op_assets = (
        _v(["inventories", "存货"]) +
        _v(["accounts_receivable", "acc_receivable", "应收账款"]) +
        _v(["notes_receivable", "notes_receiv", "应收票据"]) +
        _v(["prepayment", "预付款项"]) +
        _v(["long_receivables", "长期应收款"])
    )

    # 营运负债
    op_liabilities = (
        _v(["accounts_payable", "应付账款"]) +
        _v(["notes_payable", "应付票据"]) +
        _v(["advance_receipts", "预收款项"]) +
        _v(["payroll_payable", "应付职工薪酬"]) +
        _v(["tax_payable", "应交税费"])
    )

    if op_assets > 0:
        return round(op_liabilities / op_assets, 2)
    return None


def diagnose_bargaining_power(ratio: float | None) -> str:
    """行业话语权诊断"""
    if ratio is None:
        return "数据不足"
    if ratio > 1.5:
        return "极强（对上下游有显著议价优势）"
    elif ratio > 1.0:
        return "较强（占用上下游资金能力强）"
    elif ratio > 0.5:
        return "中等（行业地位一般）"
    else:
        return "较弱（被上下游占用资金）"


def restructure_balance_sheet(
    balance_df: pd.DataFrame | None,
) -> dict[str, float]:
    """
    资产负债表重构为管理用财务报表 — 复现教科书 附录2

    资产端:
      金融资产、营运资本(营运资产-营运负债)、长期经营资产、长期股权投资
    资本端:
      短期有息债务、长期有息债务、股东权益、长期融资净值
    """
    if balance_df is None or balance_df.empty:
        return {}

    row = balance_df.iloc[0]

    def _v(cols):
        for c in cols:
            if c in row.index:
                v = row[c]
                if pd.notna(v):
                    return float(v)
        return 0.0

    # 资产端
    financial_assets = (
        _v(["money_cap", "货币资金"]) +
        _v(["tradable_financial_assets", "交易性金融资产"])
    )

    op_assets = (
        _v(["inventories", "存货"]) +
        _v(["accounts_receivable", "acc_receivable", "应收账款"]) +
        _v(["notes_receivable", "notes_receiv", "应收票据"]) +
        _v(["prepayment", "预付款项"])
    )
    op_liabilities = (
        _v(["accounts_payable", "应付账款"]) +
        _v(["notes_payable", "应付票据"]) +
        _v(["advance_receipts", "预收款项"])
    )
    working_capital = op_assets - op_liabilities

    long_operating_assets = (
        _v(["fix_assets", "固定资产"]) +
        _v(["intangible_assets", "无形资产"]) +
        _v(["construction_in_process", "在建工程"])
    )

    long_equity_invest = _v(["long_term_equity", "长期股权投资"])

    # 资本端
    st_debt = _v(["st_borrow", "短期借款"])
    lt_debt = _v(["lt_borrow", "长期借款"]) + _v(["bond_payable", "应付债券"])
    equity = _v(["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])
    total_assets_val = _v(["total_assets", "资产总计"])

    return {
        "金融资产": round(financial_assets / 1e8, 2),
        "营运资本": round(working_capital / 1e8, 2),
        "长期经营资产": round(long_operating_assets / 1e8, 2),
        "长期股权投资": round(long_equity_invest / 1e8, 2),
        "短期有息债务": round(st_debt / 1e8, 2),
        "长期有息债务": round(lt_debt / 1e8, 2),
        "股东权益": round(equity / 1e8, 2),
        "总资产": round(total_assets_val / 1e8, 2),
    }
