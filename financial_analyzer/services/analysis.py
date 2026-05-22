"""
统一分析调度器 — 所有分析类型的规范调度入口
桌面端、Web端、API 均通过此模块调度分析
"""
import logging
import numpy as np
from typing import Any, Callable

from ..analyzers.base import BaseAnalyzer
from ..analyzers.market import MarketAnalyzer
from ..analyzers.financial import FinancialStatementAnalyzer
from ..analyzers.profitability import ProfitabilityAnalyzer
from ..analyzers.risk_analyzer import RiskAnalyzer
from ..analyzers.deep_analysis import DeepAnalyzer
from ..analyzers.audit import AuditAnalyzer
from ..analyzers.phase2_analysis import Phase2Analyzer
from ..analyzers.financial_ratios import FinancialRatioAnalyzer
from ..analyzers.combined import CombinedAnalyzer
from ..analyzers.comprehensive import ComprehensiveAnalyzer
from ..analyzers.balance_sheet import BalanceSheetAnalyzer
from ..analyzers.income_statement import IncomeStatementAnalyzer
from ..analyzers.cash_flow import CashFlowAnalyzer
from ..analyzers.shareholder import ShareholderAnalyzer
from ..analyzers.capital_flow import CapitalFlowAnalyzer
from ..data_sources.adapter import DataSourceAdapter
from ..cache.manager import DataCacheManager
from ..pipeline.textbook.ch5_ratio_compute import compute_13_ratios, compute_4_cashflow_metrics
from ..pipeline.textbook.ch6_trend_score import score_trend_all_ratios, composite_trend_score
from ..pipeline.textbook.ch8_cashflow_portrait import (
    multi_year_portrait, stability_assessment, extract_cashflow_signs, classify_portrait,
)
from ..pipeline.textbook.ch9_dupont_roic import (
    dupont_3factor, dupont_5factor, classify_dupont_driver,
    calculate_roic, compute_bargaining_power, diagnose_bargaining_power,
    restructure_balance_sheet,
)
from ..pipeline.textbook.ch12_13_fraud_ml import FraudDetectionPipeline, SKLEARN_AVAILABLE

logger = logging.getLogger(__name__)

# ============================================================================
# 财务比率参考值（行业通用基准）
# ============================================================================

RATIO_REFERENCES = {
    "毛利率": "参考: >40%优秀, 20-40%正常, <20%偏低",
    "净利率": "参考: >20%优秀, 5-20%正常, <5%偏低",
    "净利润率": "参考: >20%优秀, 5-20%正常, <5%偏低",
    "营业利润率": "参考: >25%优秀, 10-25%正常, <10%偏低",
    "ROE": "参考: >20%优秀, 8-20%正常, <8%偏低",
    "ROA": "参考: >10%优秀, 5-10%正常, <5%偏低",
    "流动比率": "参考: >2健康, 1-2可接受, <1有风险",
    "速动比率": "参考: >1健康, 0.5-1可接受, <0.5有风险",
    "资产负债率": "参考: 40-60%合理, >70%高风险, <30%偏保守",
    "存货周转率": "参考: 行业差异大, >5较好",
    "总资产周转率": "参考: >0.8良好, <0.5偏低",
    "应收账款周转率": "参考: >6良好",
    "利息保障倍数": "参考: >3安全, 1.5-3一般, <1.5有风险",
    "营收增长率": "参考: >20%高成长, 10-20%中等, <10%低增长",
    "营业利润增长率": "参考: >20%高成长, 10-20%中等, <10%低增长",
    "净利润增长率": "参考: >20%高成长, 10-20%中等, <10%低增长",
    "总资产增长率": "参考: >20%高速扩张, 10-20%稳健, <10%缓慢",
    "营收三年CAGR": "参考: >20%高成长, 10-20%中等, <10%低增长",
    "现金流利润比": "参考: >1良好, <1需关注",
    "收入现金比": "参考: >1良好, <1需关注",
    "现金充足率": "参考: >0.5充裕, <0.2紧张",
    "产权比率": "参考: <1较为稳健, >2较高杠杆",
}


# ============================================================================
# Runner 工厂函数
# ============================================================================

def _make_analyzer(cls, method_name: str):
    """工厂: 创建分析器实例并调用指定方法"""
    def runner(data: dict, stock_code: str, adapter, cache) -> str:
        try:
            is_base = issubclass(cls, BaseAnalyzer)
        except TypeError:
            is_base = False
        if is_base:
            analyzer = cls(data, stock_code, adapter, cache)
        else:
            analyzer = cls(data, stock_code)
        return getattr(analyzer, method_name)()
    return runner


def _make_phase2_runner(method_name: str):
    """工厂: 创建 Phase2Analyzer 并调用指定方法"""
    def runner(data: dict, stock_code: str, adapter, cache) -> str:
        pa = Phase2Analyzer(data, stock_code, adapter)
        return getattr(pa, method_name)()
    return runner


def _make_audit_runner(categories: list = None):
    """工厂: 创建 AuditAnalyzer 并调用 analyze_audit"""
    def runner(data: dict, stock_code: str, adapter, cache) -> str:
        analyzer = AuditAnalyzer(data, stock_code, adapter, cache)
        return analyzer.analyze_audit(categories=categories)
    return runner


# ============================================================================
# 特殊分析 Runner（包含格式化逻辑）
# ============================================================================

def _run_ratio_analyzer(data: dict, stock_code: str, adapter, cache) -> str:
    """财务比率分析 — 结构化格式化"""
    fa = FinancialRatioAnalyzer(data, stock_code)
    result = fa.analyze()
    lines = ["═══════════════════ 财务比率分析 ═══════════════════", ""]

    def _flatten_ratio_dict(d: dict, indent: int = 0) -> None:
        prefix = "  " * indent + "  "
        for k, v in d.items():
            if k in ("评级",):
                continue
            if isinstance(v, dict):
                lines.append(f"{prefix}▸ {k}:")
                _flatten_sub_items(v, indent + 1)
            elif isinstance(v, (int, float)):
                val = f"{v:.2f}" if isinstance(v, float) and v == int(v) is False else f"{v}"
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"{prefix}{k}: {val}  ({ref})")
                else:
                    lines.append(f"{prefix}{k}: {val}")
            else:
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"{prefix}{k}: {v}  ({ref})")
                else:
                    lines.append(f"{prefix}{k}: {v}")

    def _flatten_sub_items(d: dict, indent: int) -> None:
        prefix = "  " * indent + "    "
        for k, v in d.items():
            if k in ("评级", "ROE验证"):
                continue
            if isinstance(v, dict):
                _flatten_sub_items(v, indent)
            elif isinstance(v, float):
                if abs(v) < 0.01:
                    val = f"{v:.4f}"
                elif abs(v) < 1:
                    val = f"{v:.3f}"
                else:
                    val = f"{v:.2f}"
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"{prefix}{k}: {val}  ({ref})")
                else:
                    lines.append(f"{prefix}{k}: {val}")
            else:
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"{prefix}{k}: {v}  ({ref})")
                else:
                    lines.append(f"{prefix}{k}: {v}")

    for category, ratios in result.items():
        if category == "综合评分":
            lines.append(f"\n▌ {category}")
            if isinstance(ratios, dict):
                lines.append(f"  总得分: {ratios.get('总分', 'N/A')} / {ratios.get('满分', 'N/A')}")
                pct = ratios.get("得分率", "N/A")
                lines.append(f"  得分率: {pct}%" if pct != "N/A" else f"  得分率: {pct}")
                sub = ratios.get("各项", {})
                if isinstance(sub, dict):
                    for k, v in sub.items():
                        lines.append(f"    {k}: {v}")
                lines.append(f"  综合评级: {ratios.get('评级', 'N/A')}")
        else:
            lines.append(f"\n▌ {category}")
            if isinstance(ratios, dict):
                _flatten_ratio_dict(ratios)
                if "评级" in ratios:
                    lines.append(f"  综合评级: {ratios['评级']}")

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_comprehensive(data: dict, stock_code: str, adapter, cache) -> str:
    """综合投资分析 — 7维金字塔评分"""
    analyzer = ComprehensiveAnalyzer(data, stock_code, adapter, cache)
    thesis = analyzer.analyze()
    return _format_comprehensive(thesis)


def _format_comprehensive(thesis) -> str:
    """格式化综合投资分析报告"""
    lines = [
        "═══════════════════ 综合投资分析报告 ═══════════════════", "",
        f"  公司: {thesis.company_name} ({thesis.stock_code})",
        f"  行业: {thesis.industry}",
        f"  当前股价: {thesis.current_price:.2f} 元", "",
        "▌ 综合评级",
        f"  综合评分: {thesis.overall_score:.1f}/100  {thesis.star_rating}",
        f"  投资评级: {thesis.overall_rating}",
    ]
    if thesis.upside_potential != 0:
        direction = "上涨" if thesis.upside_potential > 0 else "下跌"
        lines.append(f"  估测空间: {direction}{abs(thesis.upside_potential):.1f}%")
    if thesis.fair_value_range[0] > 0:
        lines.append(f"  公允价值: {thesis.fair_value_range[0]:.2f} - {thesis.fair_value_range[1]:.2f} 元")

    lines.extend([
        "", "▌ 七维评分卡",
        f"  L1 商业模式:    {'█' * int(thesis.business_score / 10)}{'░' * max(0, 10 - int(thesis.business_score / 10))} {thesis.business_score:.0f}/100",
        f"  L2 会计质量:    {'█' * int(thesis.accounting_quality_score / 10)}{'░' * max(0, 10 - int(thesis.accounting_quality_score / 10))} {thesis.accounting_quality_score:.0f}/100",
        f"  L3 财务健康:    {'█' * int(thesis.financial_health_score / 10)}{'░' * max(0, 10 - int(thesis.financial_health_score / 10))} {thesis.financial_health_score:.0f}/100",
        f"  L4 盈利能力:    {'█' * int(thesis.profitability_score / 10)}{'░' * max(0, 10 - int(thesis.profitability_score / 10))} {thesis.profitability_score:.0f}/100",
        f"  L5 成长质量:    {'█' * int(thesis.growth_quality_score / 10)}{'░' * max(0, 10 - int(thesis.growth_quality_score / 10))} {thesis.growth_quality_score:.0f}/100",
        f"  L6 估值吸引力:  {'█' * int(thesis.valuation_score / 10)}{'░' * max(0, 10 - int(thesis.valuation_score / 10))} {thesis.valuation_score:.0f}/100",
        "", "▌ 核心指标",
    ])
    for key, val in thesis.key_metrics.items():
        lines.append(f"  {key}: {val:.2f}" if isinstance(val, float) else f"  {key}: {val}")
    if thesis.strengths:
        lines.append("\n▌ 投资亮点")
        for s in thesis.strengths:
            lines.append(f"  ✅ {s}")
    if thesis.risks:
        lines.append("\n▌ 风险提示")
        for r in thesis.risks:
            lines.append(f"  ⚠️ {r}")
    if thesis.catalysts:
        lines.append("\n▌ 催化剂")
        for c in thesis.catalysts:
            lines.append(f"  📈 {c}")
    if thesis.radar_data:
        lines.append("\n▌ 雷达图数据")
        for dim, score in thesis.radar_data.items():
            lines.append(f"  {dim}: {score:.0f}")
    # 追加13项核心比率 (Ch5)
    lines.append("")
    lines.extend(_textbook_ratios_lines(data))
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _textbook_ratios_lines(data) -> list[str]:
    """Ch5 13项核心财务比率 — 返回行列表，供合并使用"""
    income_df, balance_df, cashflow_df = data.get("income"), data.get("balance"), data.get("cashflow")
    lines = ["▌ 13项核心比率 (Ch5)"]
    if income_df is None or income_df.empty:
        lines.append("  错误：缺少利润表数据")
        return lines
    ratios = compute_13_ratios(income_df, balance_df, cashflow_df)
    cf_metrics = compute_4_cashflow_metrics(income_df, balance_df, cashflow_df)
    for group, keys in [("盈利能力", ["毛利率", "营业利润率", "净利润率", "ROE"]),
                         ("营运能力", ["存货周转率", "总资产周转率", "应收账款周转率"]),
                         ("偿债能力", ["流动比率", "速动比率", "利息保障倍数"]),
                         ("成长能力", ["营收增长率", "营业利润增长率", "净利润增长率"])]:
        lines.append(f"  ▸ {group}")
        for k in keys:
            if k in ratios:
                unit = '%' if '率' in k or 'ROE' in k or '增长' in k else ' 次'
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"    {k}: {ratios[k]:.2f}{unit}  ({ref})")
                else:
                    lines.append(f"    {k}: {ratios[k]:.2f}{unit}")
    if cf_metrics:
        lines.append("  ▸ 现金流质量")
        for k in ["现金流利润比", "收入现金比", "现金充足率"]:
            if k in cf_metrics:
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"    {k}: {cf_metrics[k]:.2f}  ({ref})")
                else:
                    lines.append(f"    {k}: {cf_metrics[k]:.2f}")
        fcf = cf_metrics.get("自由现金流(亿元)")
        if fcf is not None:
            lines.append(f"    自由现金流: {fcf} 亿")
    return lines


def _run_textbook_ratios(data, stock_code, adapter, cache) -> str:
    """Ch5 13项核心财务比率"""
    income_df, balance_df, cashflow_df = data.get("income"), data.get("balance"), data.get("cashflow")
    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"
    ratios = compute_13_ratios(income_df, balance_df, cashflow_df)
    cf_metrics = compute_4_cashflow_metrics(income_df, balance_df, cashflow_df)
    lines = ["═══════════ 13项核心财务比率 (Ch5) ═══════════", ""]
    for group, keys in [("盈利能力", ["毛利率", "营业利润率", "净利润率", "ROE"]),
                         ("营运能力", ["存货周转率", "总资产周转率", "应收账款周转率"]),
                         ("偿债能力", ["流动比率", "速动比率", "利息保障倍数"]),
                         ("成长能力", ["营收增长率", "营业利润增长率", "净利润增长率"])]:
        lines.append(f"▌ {group}")
        for k in keys:
            if k in ratios:
                unit = '%' if '率' in k or 'ROE' in k or '增长' in k else ' 次'
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"  {k}: {ratios[k]:.2f}{unit}  ({ref})")
                else:
                    lines.append(f"  {k}: {ratios[k]:.2f}{unit}")
    if cf_metrics:
        lines.append("\n▌ 现金流质量 (Ch8)")
        for k in ["现金流利润比", "收入现金比", "现金充足率"]:
            if k in cf_metrics:
                ref = RATIO_REFERENCES.get(k, "")
                if ref:
                    lines.append(f"  {k}: {cf_metrics[k]:.2f}  ({ref})")
                else:
                    lines.append(f"  {k}: {cf_metrics[k]:.2f}")
        fcf = cf_metrics.get("自由现金流(亿元)")
        if fcf is not None:
            lines.append(f"  自由现金流: {fcf} 亿")
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_cashflow_portrait(data, stock_code, adapter, cache) -> str:
    """Ch8 现金流5型画像"""
    cf_df = data.get("cashflow")
    if cf_df is None or cf_df.empty:
        return "错误：缺少现金流量表数据"
    portraits = multi_year_portrait(cf_df, years=5)
    stability = stability_assessment(portraits)
    lines = ["═══════════ 现金流5型画像 (Ch8) ═══════════", ""]
    if portraits:
        lines.append(f"  数据跨度: {len(portraits)} 期 | 稳定性: {stability}\n")
        lines.append(f"  {'期间':<14s} {'经营CF':>14s} {'投资CF':>14s} {'筹资CF':>14s} {'画像':<20s}")
        lines.append("  " + "─" * 80)
        for p in portraits:
            ocf_s = f"{p['ocf']/1e8:.2f}亿" if p.get("ocf") and abs(p["ocf"]) > 1e4 else f"{p.get('ocf', 0) or 0:.2f}"
            icf_s = f"{p['icf']/1e8:.2f}亿" if p.get("icf") and abs(p["icf"]) > 1e4 else f"{p.get('icf', 0) or 0:.2f}"
            fin_s = f"{p['fin_cf']/1e8:.2f}亿" if p.get("fin_cf") and abs(p["fin_cf"]) > 1e4 else f"{p.get('fin_cf', 0) or 0:.2f}"
            lines.append(f"  {p['period']:<14s} {ocf_s:>14s} {icf_s:>14s} {fin_s:>14s} {p.get('type_cn', '?')}")
    signs = extract_cashflow_signs(cf_df)
    portrait = classify_portrait(signs.get("ocf"), signs.get("icf"), signs.get("fcf"))
    if portrait.get("type") != "unknown":
        lines.append(f"\n  最新画像: {portrait['type_cn']} — {portrait['description']}")
        if portrait.get("danger"):
            lines.append("  ⚠️ 经营现金流为负，需警惕流动性风险")
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_trend_score(data, stock_code, adapter, cache) -> str:
    """Ch6 逐年改善度趋势评分"""
    income_df, balance_df = data.get("income"), data.get("balance")
    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"
    date_col = "end_date" if "end_date" in income_df.columns else (
        "f_ann_date" if "f_ann_date" in income_df.columns else None)
    ratios_history = []
    for i in range(len(income_df)):
        inc_slice = income_df.iloc[i:i + 1]
        bal_slice = None
        if date_col and balance_df is not None and not balance_df.empty and date_col in balance_df.columns:
            date_val = inc_slice[date_col].iloc[0] if not inc_slice[date_col].empty else None
            if date_val is not None:
                matched = balance_df[balance_df[date_col] == date_val]
                if not matched.empty:
                    bal_slice = matched.iloc[:1]
        if bal_slice is None:
            bal_slice = balance_df
        ratios = compute_13_ratios(inc_slice, bal_slice, None)
        if ratios:
            ratios_history.append(ratios)
    if len(ratios_history) < 2:
        return f"趋势评分需要至少两期数据，当前仅能计算 {len(ratios_history)} 期比率"
    trend_scores = score_trend_all_ratios(ratios_history)
    composite = composite_trend_score(trend_scores)
    lines = ["═══════════ 财务趋势评分 (Ch6) ═══════════", "",
             f"  综合趋势评分: {composite:.1f}/100 ({len(ratios_history)} 期)", ""]
    for name, score in sorted(trend_scores.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * min(10, int(score / 10)) + "░" * max(0, 10 - int(score / 10))
        lines.append(f"  {name:<12s}  {bar}  {score:.1f}")
    lines.extend(["", "  ≥80 持续改善 | ≥60 总体向好 | ≥40 波动持平 | ≥20 趋势走弱 | <20 持续恶化"])

    # --- 趋势解读：评分依据 + 分组排名 ---
    lines.extend(["", "  ═══ 趋势解读 ═══", ""])
    lines.append("  评分依据: 逐年比较各比率变化方向，当期值 > 上期值(改善)计1分，")
    lines.append("  标准化为 0-100分。综合趋势评分 = 所有比率趋势评分的平均值。")

    # 分组：>=60 改善显著 | 40-60 相对稳定 | <40 趋势走弱
    improving, stable, weakening = [], [], []
    for name, score in sorted(trend_scores.items(), key=lambda x: x[1], reverse=True):
        first_val = ratios_history[-1].get(name)  # 最早一期
        last_val = ratios_history[0].get(name)     # 最新一期
        change_str = ""
        if (first_val is not None and last_val is not None
                and not (isinstance(first_val, float) and (np.isnan(first_val) or np.isinf(first_val)))
                and not (isinstance(last_val, float) and (np.isnan(last_val) or np.isinf(last_val)))):
            if abs(first_val) > 1e-9:
                pct = (last_val - first_val) / abs(first_val) * 100
                if abs(pct) < 10000:
                    sign = "+" if pct > 0 else ""
                    change_str = f" ({sign}{pct:.1f}%)"
            elif abs(last_val - first_val) > 1e-9:
                change_str = f" ({first_val:.2f}→{last_val:.2f})"
        entry = f"    {name}: {score:.1f}{change_str}"
        if score >= 60:
            improving.append(entry)
        elif score >= 40:
            stable.append(entry)
        else:
            weakening.append(entry)

    if improving:
        lines.append(f"\n  改善最显著 ({len(improving)}项) — 趋势持续向好:")
        lines.extend(improving)
    if stable:
        lines.append(f"\n  相对稳定 ({len(stable)}项) — 波动或持平:")
        lines.extend(stable)
    if weakening:
        lines.append(f"\n  趋势走弱 ({len(weakening)}项) — 需关注:")
        lines.extend(weakening)

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_dupont_roic(data, stock_code, adapter, cache) -> str:
    """Ch9 增强杜邦分析 + ROIC + 行业话语权"""
    income_df, balance_df = data.get("income"), data.get("balance")
    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"
    if balance_df is None or balance_df.empty:
        return "错误：缺少资产负债表数据"
    inc, bal = income_df.iloc[0], balance_df.iloc[0]
    np_val = _extract_val(inc, ["net_profit", "n_income_attr_p", "净利润"])
    rev = _extract_val(inc, ["revenue", "total_revenue", "营业收入"])
    ta = _extract_val(bal, ["total_assets", "资产总计"])
    eq = _extract_val(bal, ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])
    pretax = _extract_val(inc, ["total_profit", "利润总额"])
    op_profit = _extract_val(inc, ["operate_profit", "营业利润"])
    income_tax = _extract_val(inc, ["income_tax", "所得税费用"])
    fin_exp = _extract_val(inc, ["interest_expense", "fin_exp", "财务费用"])
    st_debt = _extract_val(bal, ["st_borrow", "短期借款"]) or 0
    lt_debt = (_extract_val(bal, ["lt_borrow", "长期借款"]) or 0) + (_extract_val(bal, ["bond_payable", "应付债券"]) or 0)
    ebit = (op_profit or 0) + abs(fin_exp or 0)
    lines = ["═══════════ 增强杜邦分析 (Ch9) ═══════════", ""]
    r3 = dupont_3factor(np_val, rev, ta, eq)
    if r3:
        lines.extend(["▌ 杜邦三因子分解",
                      f"  ROE: {r3['ROE']}%",
                      f"  销售净利率: {r3['销售净利率']}%",
                      f"  总资产周转率: {r3['总资产周转率']}",
                      f"  权益乘数: {r3['权益乘数']}",
                      f"  盈利模式: {classify_dupont_driver(r3['销售净利率'], r3['总资产周转率'], r3['权益乘数'])}", ""])
    r5 = dupont_5factor(np_val, pretax, ebit, rev, ta, eq)
    if r5:
        lines.extend(["▌ 杜邦五因子分解",
                      f"  ROE: {r5['ROE']}%",
                      f"  税负效应: {r5['税负效应']} | 利息效应: {r5['利息效应']}",
                      f"  营业利润率: {r5['营业利润率']}% | 资产周转率: {r5['总资产周转率']} | 权益乘数: {r5['权益乘数']}", ""])
    roic = calculate_roic(ebit, income_tax, pretax, st_debt, lt_debt, eq)
    if roic is not None:
        lines.append(f"▌ ROIC: {roic:.2f}%\n")
    bp = compute_bargaining_power(balance_df)
    lines.append(f"▌ 行业话语权: {bp:.2f} — {diagnose_bargaining_power(bp)}" if bp is not None else "▌ 行业话语权: N/A")
    restructured = restructure_balance_sheet(balance_df)
    if restructured:
        lines.extend(["", "▌ 管理用资产负债表",
                      f"  金融资产: {restructured.get('金融资产', 'N/A')} 亿",
                      f"  营运资本: {restructured.get('营运资本', 'N/A')} 亿",
                      f"  长期经营资产: {restructured.get('长期经营资产', 'N/A')} 亿"])
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_fraud_ml(data, stock_code, adapter, cache) -> str:
    """Ch12-13 ML舞弊检测"""
    if not SKLEARN_AVAILABLE:
        return "ML舞弊检测不可用：scikit-learn 未安装"
    income_df, balance_df, cashflow_df = data.get("income"), data.get("balance"), data.get("cashflow")
    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"
    ratios = compute_13_ratios(income_df, balance_df, cashflow_df)
    cf_metrics = compute_4_cashflow_metrics(income_df, balance_df, cashflow_df)
    features = {
        "roe": ratios.get("ROE", 0), "roa": _estimate_roa(ratios, income_df, balance_df),
        "gross_margin": ratios.get("毛利率", 0), "net_margin": ratios.get("净利润率", 0),
        "current_ratio": ratios.get("流动比率", 0), "quick_ratio": ratios.get("速动比率", 0),
        "debt_to_assets": _estimate_debt_ratio(balance_df),
        "asset_turnover": ratios.get("总资产周转率", 0),
        "inventory_turnover": ratios.get("存货周转率", 0),
        "receivable_turnover": ratios.get("应收账款周转率", 0),
        "revenue_growth": ratios.get("营收增长率", 0), "profit_growth": ratios.get("净利润增长率", 0),
        "ocf_to_profit": cf_metrics.get("现金流利润比", 0),
        "revenue_cash_ratio": cf_metrics.get("收入现金比", 0),
        "accrual_ratio": _estimate_accrual_ratio(income_df, balance_df, cashflow_df),
        "goodwill_to_equity": _estimate_goodwill_ratio(balance_df),
    }
    pipeline = FraudDetectionPipeline()
    from pathlib import Path
    model_paths = [
        Path.home() / ".financialanalyzer" / "fraud_models.pkl",
        Path(__file__).parent.parent / "pipeline" / "textbook" / "fraud_models.pkl",
    ]
    lines = ["═══════════ ML舞弊检测 (Ch12-13) ═══════════", ""]
    loaded = any(pipeline.load(str(mp)) for mp in model_paths if mp.exists())
    if not loaded:
        lines.extend(["  ⚠️ 未找到预训练模型", "  请先训练: pipeline.train('DATA.xlsx') → pipeline.save('fraud_models.pkl')",
                      "", "▌ 特征值一览"])
        for k, v in features.items():
            lines.append(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
        lines.append("\n═══════════════════════════════════════════════════")
        return "\n".join(lines)
    result = pipeline.predict(features)
    lines.extend([f"  综合欺诈概率: {result.fraud_probability:.2%}", f"  风险等级: {result.fraud_risk_level}", ""])
    if result.model_votes:
        lines.append("▌ 模型投票")
        for model, prob in result.model_votes.items():
            if prob is not None:
                lines.append(f"  {model:<16s}  {'█' * int(prob * 20)}{'░' * max(0, 20 - int(prob * 20))}  {prob:.2%}")
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


# ============================================================================
# 辅助函数
# ============================================================================

def _extract_val(row, cols: list[str]) -> float | None:
    if row is None:
        return None
    for c in cols:
        if c in row.index:
            v = row[c]
            try:
                import pandas as pd
                if pd.notna(v):
                    return float(v)
            except (ValueError, TypeError):
                continue
    return None


def _estimate_roa(ratios, income_df, balance_df) -> float:
    if balance_df is None or balance_df.empty:
        return 0
    np_margin = ratios.get("净利润率", 0)
    rev = _extract_val(income_df.iloc[0], ["revenue", "total_revenue", "营业收入"])
    ta = _extract_val(balance_df.iloc[0], ["total_assets", "资产总计"])
    if np_margin and rev and ta and ta > 0:
        return round(np_margin / 100 * rev / ta * 100, 2)
    return 0


def _estimate_debt_ratio(balance_df) -> float:
    if balance_df is None or balance_df.empty:
        return 0
    tl = _extract_val(balance_df.iloc[0], ["total_liab", "负债合计"])
    ta = _extract_val(balance_df.iloc[0], ["total_assets", "资产总计"])
    return round(tl / ta * 100, 2) if tl and ta and ta > 0 else 0


def _estimate_accrual_ratio(income_df, balance_df, cashflow_df) -> float:
    if income_df is None or income_df.empty:
        return 0
    np_val = _extract_val(income_df.iloc[0], ["net_profit", "n_income_attr_p", "净利润"])
    ocf = _extract_val(cashflow_df.iloc[0], ["n_cashflow_act", "经营活动现金流量净额"]) if cashflow_df is not None and not cashflow_df.empty else None
    ta = _extract_val(balance_df.iloc[0], ["total_assets", "资产总计"]) if balance_df is not None and not balance_df.empty else None
    return round((np_val - ocf) / ta, 4) if np_val and ocf is not None and ta and ta > 0 else 0


def _estimate_goodwill_ratio(balance_df) -> float:
    if balance_df is None or balance_df.empty:
        return 0
    gw = _extract_val(balance_df.iloc[0], ["goodwill", "商誉"])
    eq = _extract_val(balance_df.iloc[0], ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])
    return round(gw / eq * 100, 2) if gw and eq and eq > 0 else 0


def _run_cashflow_combined(data, stock_code, adapter, cache) -> str:
    """现金流综合分析：自由现金流 + 现金流5型画像"""
    da = DeepAnalyzer(data, stock_code, adapter, cache)
    fcf_result = da.analyze_free_cashflow()
    portrait_result = da.analyze_cashflow_quadrant()

    lines = [
        "═══════════ 现金流综合分析 ═══════════",
        "",
        fcf_result,
        "",
        "─" * 55,
        "",
        portrait_result,
        "",
        "═══════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ============================================================================
# 规范分析调度表（单一起源）
# ============================================================================

ANALYSIS_MAP: dict[str, Callable] = {
    # 行情分析
    "market_overview": _make_analyzer(MarketAnalyzer, "analyze_market_overview"),
    "price_trend": _make_analyzer(MarketAnalyzer, "analyze_price_trend"),
    # 财务报表综合分析（含偿债/营运/盈利/成长能力）
    "balance_sheet_analysis": _make_analyzer(BalanceSheetAnalyzer, "analyze"),
    "income_analysis": _make_analyzer(IncomeStatementAnalyzer, "analyze"),
    "cashflow_analysis": _make_analyzer(CashFlowAnalyzer, "analyze"),
    # 综合评估
    "combined": _make_analyzer(CombinedAnalyzer, "analyze_price_financial_combined"),
    "risk": _make_analyzer(RiskAnalyzer, "generate_risk_warning_report"),
    # 财务比率
    "ratio_analysis": _run_ratio_analyzer,
    # 财务审计
    "audit_asset": _make_audit_runner(["asset"]),
    "audit_profit": _make_audit_runner(["profit"]),
    "audit_cashflow": _make_audit_runner(["cashflow"]),
    "audit_cross": _make_audit_runner(["cross"]),
    "audit_full": _make_audit_runner(),
    # 深度分析
    "dupont": _run_dupont_roic,
    "zscore": _make_analyzer(DeepAnalyzer, "analyze_zscore"),
    "fscore": _make_analyzer(DeepAnalyzer, "analyze_fscore"),
    "mscore": _make_analyzer(DeepAnalyzer, "analyze_mscore"),
    "fcf": _run_cashflow_combined,
    "quadrant": _run_cashflow_combined,  # alias
    "moat": _make_analyzer(DeepAnalyzer, "analyze_moat"),
    "deep_comprehensive": _make_analyzer(DeepAnalyzer, "generate_comprehensive_report"),
    # 估值与质量
    "pe_valuation": _make_phase2_runner("valuation_analysis"),
    "pe_percentile": _make_phase2_runner("pe_percentile_analysis"),
    "pb_roe": _make_phase2_runner("pb_roe_analysis"),
    "ev_ebitda": _make_phase2_runner("ev_ebitda_analysis"),
    "shareholder_return": _make_phase2_runner("shareholder_return_analysis"),
    "quality": _make_phase2_runner("financial_quality_analysis"),
    # 综合投资分析
    "comprehensive": _run_comprehensive,
    # 教科书算法
    "textbook_ratios": _run_textbook_ratios,
    "trend_score": _run_trend_score,
    "cashflow_portrait": _run_cashflow_portrait,
    "dupont_roic": _run_dupont_roic,
    "fraud_ml": _run_fraud_ml,
    # 股东与资金面（Phase 1 新增）
    "shareholder": _make_analyzer(ShareholderAnalyzer, "analyze"),
    "capital_flow": _make_analyzer(CapitalFlowAnalyzer, "analyze"),
    "dividend_analysis": _make_phase2_runner("dividend_analysis"),
    "weekly_pe": _make_phase2_runner("weekly_pe_percentile"),
}


class AnalysisDispatcher:
    """统一分析调度器 — 桌面、Web、API 均通过此类调度分析"""

    def __init__(self, adapter: DataSourceAdapter = None, cache: DataCacheManager = None):
        self.adapter = adapter
        self.cache = cache

    def run(self, analysis_type: str, data: dict, stock_code: str) -> str:
        """运行指定分析类型，返回格式化文本结果"""
        fn = ANALYSIS_MAP.get(analysis_type)
        if fn is None:
            return f"未知的分析类型: {analysis_type}"
        try:
            return fn(data, stock_code, self.adapter, self.cache)
        except Exception as e:
            logger.error(f"分析 {analysis_type} 失败: {e}", exc_info=True)
            return f"分析失败: {e}"

    @staticmethod
    def get_available_analyses() -> dict[str, str]:
        """返回所有可用分析类型及名称"""
        return {k: k for k in ANALYSIS_MAP}
