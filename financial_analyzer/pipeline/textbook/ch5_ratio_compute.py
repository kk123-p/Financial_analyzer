"""
Ch5 财务静态分析 — 13项核心财务比率
=====================================
整合《Python大数据财务分析》第5章 "5.5 综合案例" (lines 111-165)

原始教科书算法：
  从利润表、资产负债表、现金流量表中提取数据，
  计算13项核心财务比率，输出为财务比率表。

适配改造：
  - 输入从 Tushare Excel 文件 → 改为项目标准化的 DataFrame dict
  - 列名从中文重命名 → 改为项目 adapter 归一化的英文字段名
  - 输出从 Excel Sheet → 改为 dict[str, float]
"""
from typing import Any
import pandas as pd
import numpy as np


# 教科书定义的字段别名映射（Tushare中文名 → 归一化英文字段名）
FIELD_MAP = {
    # 利润表
    "营业收入": "revenue",
    "营业成本": "operating_cost",
    "营业利润": "operate_profit",
    "净利润": "net_profit",
    "利润总额": "total_profit",
    "所得税费用": "income_tax",
    "财务费用": "interest_expense",
    "管理费用": "admin_expense",
    "销售费用": "selling_expense",
    # 资产负债表
    "资产总计": "total_assets",
    "流动资产合计": "total_current_assets",
    "流动负债合计": "total_current_liab",
    "存货": "inventories",
    "应收账款": "accounts_receivable",
    "股东权益合计": "total_equity",
    "负债合计": "total_liab",
    "预付款项": "prepayment",
    # 现金流量表
    "经营活动现金流量净额": "n_cashflow_act",
    "销售商品、提供劳务收到的现金": "c_fr_sale_sg",
    "期末现金及现金等价物余额": "cce",
    # 有息负债 (来自Tushare字段)
    "短期借款": "st_borrow",
    "长期借款": "lt_borrow",
    "应付债券": "bond_payable",
}


def _extract_row_value(row, keys: list[str]) -> float | None:
    """从DataFrame行中按优先级提取数值，仿教科书_get_value逻辑"""
    if row is None:
        return None
    for key in keys:
        if key in row.index:
            val = row[key]
            if pd.notna(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
    return None


def compute_13_ratios(
    income_df: pd.DataFrame | None,
    balance_df: pd.DataFrame | None,
    cashflow_df: pd.DataFrame | None,
) -> dict[str, float]:
    """
    计算13项核心财务比率
    完全复现教科书 Ch5 ratio_sheet() lines 129-146 的逻辑

    Returns:
        {
            "毛利率": float, "营业利润率": float, "净利润率": float, "ROE": float,
            "存货周转率": float, "总资产周转率": float, "应收账款周转率": float,
            "流动比率": float, "速动比率": float, "利息保障倍数": float,
            "营收增长率": float, "营业利润增长率": float, "净利润增长率": float,
        }
    """
    ratios: dict[str, float] = {}
    if income_df is None or income_df.empty:
        return ratios

    latest = income_df.iloc[0]
    prev_income = income_df.iloc[1] if len(income_df) > 1 else None
    latest_bal = balance_df.iloc[0] if balance_df is not None and not balance_df.empty else None
    prev_balance = balance_df.iloc[1] if balance_df is not None and len(balance_df) > 1 else None

    # === 盈利能力 (Ch5 lines 129-132) ===
    revenue = _extract_row_value(latest, ["revenue", "total_revenue", "营业收入"])
    cost = _extract_row_value(latest, ["operating_cost", "oper_cost", "营业成本"])
    op_profit = _extract_row_value(latest, ["operate_profit", "营业利润"])
    net_profit = _extract_row_value(latest, ["net_profit", "n_income_attr_p", "净利润"])
    equity = _extract_row_value(latest_bal, ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])

    if revenue and revenue > 0:
        if cost is not None:
            ratios["毛利率"] = round((revenue - cost) / revenue * 100, 2)
        if op_profit is not None:
            ratios["营业利润率"] = round(op_profit / revenue * 100, 2)
        if net_profit is not None:
            ratios["净利润率"] = round(net_profit / revenue * 100, 2)

    # ROE = 净利润 / 平均股东权益
    if net_profit is not None and equity is not None:
        prev_equity = _extract_row_value(prev_balance, ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])
        avg_equity = ((equity + prev_equity) / 2) if prev_equity else equity
        if avg_equity and avg_equity > 0:
            ratios["ROE"] = round(net_profit / avg_equity * 100, 2)

    # === 营运能力 (Ch5 lines 134-136) ===
    total_assets = _extract_row_value(latest_bal, ["total_assets", "资产总计"])
    inventory = _extract_row_value(latest_bal, ["inventories", "存货"])
    ar = _extract_row_value(latest_bal, ["accounts_receivable", "acc_receivable", "应收账款"])

    # 存货周转率 = 营业成本 / 平均存货
    if cost and inventory and inventory > 0:
        prev_inv = _extract_row_value(prev_balance, ["inventories", "存货"])
        avg_inv = ((inventory + prev_inv) / 2) if prev_inv else inventory
        if avg_inv > 0:
            ratios["存货周转率"] = round(cost / avg_inv, 2)

    # 总资产周转率 = 营业收入 / 平均总资产
    if revenue and total_assets and total_assets > 0:
        prev_ta = _extract_row_value(prev_balance, ["total_assets", "资产总计"])
        avg_ta = ((total_assets + prev_ta) / 2) if prev_ta else total_assets
        if avg_ta > 0:
            ratios["总资产周转率"] = round(revenue / avg_ta, 2)

    # 应收账款周转率 = 营业收入 / 平均应收账款
    if revenue and ar and ar > 0:
        prev_ar = _extract_row_value(prev_balance, ["accounts_receivable", "acc_receivable", "应收账款"])
        avg_ar = ((ar + prev_ar) / 2) if prev_ar else ar
        if avg_ar > 0:
            ratios["应收账款周转率"] = round(revenue / avg_ar, 2)

    # === 偿债能力 (Ch5 lines 138-140) ===
    ca = _extract_row_value(latest_bal, ["total_current_assets", "total_cur_assets", "流动资产合计"])
    cl = _extract_row_value(latest_bal, ["total_current_liab", "total_cur_liab", "流动负债合计"])
    prepay = _extract_row_value(latest_bal, ["prepayment", "预付款项"])

    if ca and cl and cl > 0:
        ratios["流动比率"] = round(ca / cl, 2)
        # 速动比率 = (流动资产 - 存货 - 预付款项) / 流动负债
        quick_assets = ca - (inventory or 0) - (prepay or 0)
        ratios["速动比率"] = round(quick_assets / cl, 2)

    # 利息保障倍数 = EBIT / 利息支出
    interest_exp = _extract_row_value(latest, ["interest_expense", "fin_exp", "财务费用"])
    if op_profit is not None and interest_exp and abs(interest_exp) > 0:
        ebit = op_profit + abs(interest_exp)  # 简化EBIT
        ratios["利息保障倍数"] = round(ebit / abs(interest_exp), 2)

    # === 成长能力 (Ch5 lines 142-146) ===
    if prev_income is not None:
        prev_revenue = _extract_row_value(prev_income, ["revenue", "total_revenue", "营业收入"])
        prev_op = _extract_row_value(prev_income, ["operate_profit", "营业利润"])
        prev_np = _extract_row_value(prev_income, ["net_profit", "n_income_attr_p", "净利润"])

        if revenue and prev_revenue and prev_revenue > 0:
            ratios["营收增长率"] = round((revenue - prev_revenue) / prev_revenue * 100, 2)
        if op_profit is not None and prev_op is not None and prev_op != 0:
            ratios["营业利润增长率"] = round((op_profit - prev_op) / abs(prev_op) * 100, 2)
        if net_profit is not None and prev_np is not None and prev_np != 0:
            ratios["净利润增长率"] = round((net_profit - prev_np) / abs(prev_np) * 100, 2)

    return ratios


def compute_4_cashflow_metrics(
    income_df: pd.DataFrame | None,
    balance_df: pd.DataFrame | None,
    cashflow_df: pd.DataFrame | None,
) -> dict[str, Any]:
    """
    计算4项现金流质量指标 (Ch8 lines 19-37, 97-115, 167-194, 244-262)

    Returns:
        {
            "现金流利润比": float,       # 经营CF/净利润 (Ch8 指标1)
            "收入现金比": float,         # 销售回款/营收 (Ch8 指标2)
            "现金充足率": float,         # 现金/有息负债 (Ch8 指标3)
            "自由现金流": float,         # 经营CF - 投资流出 (Ch8 指标4)
            "现金流肖像": str,           # 妖精/老母鸡/蛮牛/奶牛/危险
        }
    """
    metrics: dict[str, Any] = {}
    if cashflow_df is None or cashflow_df.empty:
        return metrics

    cf_latest = cashflow_df.iloc[0]
    inc_latest = income_df.iloc[0] if income_df is not None and not income_df.empty else None
    bal_latest = balance_df.iloc[0] if balance_df is not None and not balance_df.empty else None

    # 指标1: 经营CF / 净利润 (Ch8 lines 19-37)
    ocf = _extract_row_value(cf_latest, ["n_cashflow_act", "经营活动现金流量净额"])
    net_profit = _extract_row_value(inc_latest, ["net_profit", "n_income_attr_p", "净利润"])
    if ocf and net_profit and net_profit != 0:
        metrics["现金流利润比"] = round(ocf / net_profit, 2)

    # 指标2: 销售回款 / 营业收入 (Ch8 lines 97-115)
    cash_receipts = _extract_row_value(cf_latest, ["c_fr_sale_sg", "销售商品、提供劳务收到的现金"])
    revenue = _extract_row_value(inc_latest, ["revenue", "total_revenue", "营业收入"])
    if cash_receipts and revenue and revenue > 0:
        # 单位修正：若金额相差超过100倍，可能单位不同
        ratio = cash_receipts / revenue
        if ratio > 50:
            ratio = cash_receipts / (revenue * 10000)
        metrics["收入现金比"] = round(ratio, 2)

    # 指标3: 现金充足率 = 期末现金 / (短期借款+长期借款+应付债券) (Ch8 lines 167-194)
    cash_end = _extract_row_value(cf_latest, ["cce", "期末现金及现金等价物余额"])
    st_borrow = _extract_row_value(bal_latest, ["st_borrow", "短期借款"])
    lt_borrow = _extract_row_value(bal_latest, ["lt_borrow", "长期借款"])
    bond = _extract_row_value(bal_latest, ["bond_payable", "应付债券"])
    interest_debt = (st_borrow or 0) + (lt_borrow or 0) + (bond or 0)
    if cash_end and interest_debt > 0:
        metrics["现金充足率"] = round(cash_end / interest_debt, 2)

    # 指标4: 自由现金流 = 经营CF - 投资活动现金流出 (Ch8 lines 244-262)
    invest_out = _extract_row_value(cf_latest, ["c_invest_act", "投资活动现金流出小计"])
    if ocf is not None:
        fcf = ocf - abs(invest_out) if invest_out else ocf
        metrics["自由现金流(亿元)"] = round(fcf / 1e8, 2) if abs(fcf) > 10000 else round(fcf, 2)

    return metrics


def classify_cashflow_portrait(
    ocf: float | None,
    icf: float | None,
    fcf: float | None,
) -> str:
    """现金流5型画像分类 → 委托 ch8_cashflow_portrait.classify_portrait"""
    from .ch8_cashflow_portrait import classify_portrait
    result = classify_portrait(ocf, icf, fcf)
    return result["type_cn"]
