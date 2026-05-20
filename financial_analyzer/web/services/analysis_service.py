"""分析调度服务 — 将分析类型字符串映射到现有分析器"""
import logging
from typing import Any

import pandas as pd

from financial_analyzer.analyzers.base import BaseAnalyzer
from financial_analyzer.analyzers.market import MarketAnalyzer
from financial_analyzer.analyzers.technical import TechnicalAnalyzer
from financial_analyzer.analyzers.financial import FinancialStatementAnalyzer
from financial_analyzer.analyzers.profitability import ProfitabilityAnalyzer
from financial_analyzer.analyzers.risk_analyzer import RiskAnalyzer
from financial_analyzer.analyzers.deep_analysis import DeepAnalyzer
from financial_analyzer.analyzers.audit import AuditAnalyzer
from financial_analyzer.analyzers.phase2_analysis import Phase2Analyzer
from financial_analyzer.analyzers.financial_ratios import FinancialRatioAnalyzer
from financial_analyzer.analyzers.combined import CombinedAnalyzer
from financial_analyzer.analyzers.comprehensive import ComprehensiveAnalyzer
from financial_analyzer.data_sources.adapter import DataSourceAdapter
from financial_analyzer.cache.manager import DataCacheManager
from financial_analyzer.pipeline.textbook.ch5_ratio_compute import (
    compute_13_ratios, compute_4_cashflow_metrics,
)
from financial_analyzer.pipeline.textbook.ch6_trend_score import (
    score_trend_all_ratios, composite_trend_score,
)
from financial_analyzer.pipeline.textbook.ch8_cashflow_portrait import (
    multi_year_portrait, stability_assessment, extract_cashflow_signs, classify_portrait,
)
from financial_analyzer.pipeline.textbook.ch9_dupont_roic import (
    dupont_3factor, dupont_5factor, classify_dupont_driver,
    calculate_roic, compute_bargaining_power, diagnose_bargaining_power,
    restructure_balance_sheet,
)
from financial_analyzer.pipeline.textbook.ch12_13_fraud_ml import (
    FraudDetectionPipeline, SKLEARN_AVAILABLE,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """分析调度器 — 复用所有现有分析器"""

    def __init__(self, adapter: DataSourceAdapter, cache: DataCacheManager):
        self.adapter = adapter
        self.cache = cache

    def run(self, analysis_type: str, data: dict, stock_code: str) -> str:
        """运行指定分析，返回格式化文本结果"""
        fn = _ANALYSIS_MAP.get(analysis_type)
        if fn is None:
            return f"未知的分析类型: {analysis_type}"

        try:
            return fn(data, stock_code, self.adapter, self.cache)
        except Exception as e:
            logger.error(f"分析 {analysis_type} 失败: {e}", exc_info=True)
            return f"分析失败: {e}"


# ============================================================================
# 分析类型 → 函数映射 (38 个分析项)
# ============================================================================

def _make_analyzer(cls, method_name: str):
    """工厂函数: 创建分析器实例并调用指定方法"""
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


def _run_ratio_analyzer(data: dict, stock_code: str, adapter, cache) -> str:
    fa = FinancialRatioAnalyzer(data, stock_code)
    result = fa.analyze()
    lines = ["═══════════════════ 财务比率分析 ═══════════════════", ""]

    def _flatten_ratio_dict(d: dict, indent: int = 0) -> None:
        """递归展平嵌套的比率字典，类似桌面UI的 _format_ratio_table"""
        prefix = "  " * indent + "  "
        # 收集所有指标项：先展平子字典（如"短期偿债"、"长期偿债"、"指标"、"杜邦拆解"）
        for k, v in d.items():
            if k in ("评级",):
                continue
            if isinstance(v, dict):
                lines.append(f"{prefix}▸ {k}:")
                _flatten_sub_items(v, indent + 1)
            elif isinstance(v, (int, float)):
                lines.append(f"{prefix}{k}: {v:.2f}" if isinstance(v, float) and v == int(v) is False else f"{prefix}{k}: {v}")
            else:
                lines.append(f"{prefix}{k}: {v}")

    def _flatten_sub_items(d: dict, indent: int) -> None:
        """展平子指标项"""
        prefix = "  " * indent + "    "
        for k, v in d.items():
            if k in ("评级", "ROE验证"):
                continue
            if isinstance(v, dict):
                _flatten_sub_items(v, indent)
            elif isinstance(v, float):
                # 格式化浮点数，保留合理精度
                if abs(v) < 0.01:
                    lines.append(f"{prefix}{k}: {v:.4f}")
                elif abs(v) < 1:
                    lines.append(f"{prefix}{k}: {v:.3f}")
                else:
                    lines.append(f"{prefix}{k}: {v:.2f}")
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


def _make_phase2_runner(method_name: str):
    """工厂: 创建 Phase2Analyzer 并调用指定方法"""
    def runner(data: dict, stock_code: str, adapter, cache) -> str:
        pa = Phase2Analyzer(data, stock_code, adapter)
        return getattr(pa, method_name)()
    return runner


def _make_audit_runner(categories: list = None):
    """工厂: 创建 AuditAnalyzer 并调用 analyze_audit，可选按维度过滤"""
    def runner(data: dict, stock_code: str, adapter, cache) -> str:
        analyzer = AuditAnalyzer(data, stock_code, adapter, cache)
        return analyzer.analyze_audit(categories=categories)
    return runner


def _run_comprehensive(data: dict, stock_code: str, adapter, cache) -> str:
    """综合投资分析 — 7维金字塔评分 + DCF估值"""
    analyzer = ComprehensiveAnalyzer(data, stock_code, adapter, cache)
    thesis = analyzer.analyze()

    # 格式化为可读文本报告
    lines = [
        "═══════════════════ 综合投资分析报告 ═══════════════════",
        "",
        f"  公司: {thesis.company_name} ({thesis.stock_code})",
        f"  行业: {thesis.industry}",
        f"  当前股价: {thesis.current_price:.2f} 元",
        "",
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
        "",
        "▌ 七维评分卡",
        f"  L1 商业模式:    {'█' * int(thesis.business_score / 10) + '░' * (10 - int(thesis.business_score / 10))} {thesis.business_score:.0f}/100",
        f"  L2 会计质量:    {'█' * int(thesis.accounting_quality_score / 10) + '░' * (10 - int(thesis.accounting_quality_score / 10))} {thesis.accounting_quality_score:.0f}/100",
        f"  L3 财务健康:    {'█' * int(thesis.financial_health_score / 10) + '░' * (10 - int(thesis.financial_health_score / 10))} {thesis.financial_health_score:.0f}/100",
        f"  L4 盈利能力:    {'█' * int(thesis.profitability_score / 10) + '░' * (10 - int(thesis.profitability_score / 10))} {thesis.profitability_score:.0f}/100",
        f"  L5 成长质量:    {'█' * int(thesis.growth_quality_score / 10) + '░' * (10 - int(thesis.growth_quality_score / 10))} {thesis.growth_quality_score:.0f}/100",
        f"  L6 估值吸引力:  {'█' * int(thesis.valuation_score / 10) + '░' * (10 - int(thesis.valuation_score / 10))} {thesis.valuation_score:.0f}/100",
        "",
        "▌ 核心指标",
    ])

    for key, val in thesis.key_metrics.items():
        if isinstance(val, float):
            lines.append(f"  {key}: {val:.2f}")
        else:
            lines.append(f"  {key}: {val}")

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
        lines.append("\n▌ 雷达图数据（可用于可视化）")
        for dim, score in thesis.radar_data.items():
            lines.append(f"  {dim}: {score:.0f}")

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_textbook_ratios(data: dict, stock_code: str, adapter, cache) -> str:
    """Ch5 13项核心财务比率 + Ch8 现金流质量指标"""
    income_df = data.get("income")
    balance_df = data.get("balance")
    cashflow_df = data.get("cashflow")

    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据，无法计算财务比率"

    ratios = compute_13_ratios(income_df, balance_df, cashflow_df)
    cf_metrics = compute_4_cashflow_metrics(income_df, balance_df, cashflow_df)

    lines = ["═══════════ 13项核心财务比率 (Ch5 教科书算法) ═══════════", ""]

    profitability = ["毛利率", "营业利润率", "净利润率", "ROE"]
    operational = ["存货周转率", "总资产周转率", "应收账款周转率"]
    solvency = ["流动比率", "速动比率", "利息保障倍数"]
    growth = ["营收增长率", "营业利润增长率", "净利润增长率"]

    lines.append("▌ 盈利能力")
    for k in profitability:
        if k in ratios:
            lines.append(f"  {k}: {ratios[k]:.2f}%")

    lines.append("\n▌ 营运能力")
    for k in operational:
        if k in ratios:
            lines.append(f"  {k}: {ratios[k]:.2f} 次")

    lines.append("\n▌ 偿债能力")
    for k in solvency:
        if k in ratios:
            lines.append(f"  {k}: {ratios[k]:.2f}")

    lines.append("\n▌ 成长能力")
    for k in growth:
        if k in ratios:
            lines.append(f"  {k}: {ratios[k]:.2f}%")

    if cf_metrics:
        lines.append("\n▌ 现金流质量 (Ch8)")
        cf_ratio = cf_metrics.pop("现金流利润比", None)
        cash_revenue = cf_metrics.pop("收入现金比", None)
        cash_coverage = cf_metrics.pop("现金充足率", None)
        fcf_val = cf_metrics.pop("自由现金流(亿元)", None)
        if cf_ratio is not None:
            lines.append(f"  现金流利润比: {cf_ratio:.2f}")
        if cash_revenue is not None:
            lines.append(f"  收入现金比: {cash_revenue:.2f}")
        if cash_coverage is not None:
            lines.append(f"  现金充足率: {cash_coverage:.2f}")
        if fcf_val is not None:
            lines.append(f"  自由现金流: {fcf_val} 亿")

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_cashflow_portrait(data: dict, stock_code: str, adapter, cache) -> str:
    """Ch8 现金流5型画像 — 多年变迁 + 稳定性评估"""
    cf_df = data.get("cashflow")

    if cf_df is None or cf_df.empty:
        return "错误：缺少现金流量表数据"

    portraits = multi_year_portrait(cf_df, years=5)
    stability = stability_assessment(portraits)

    lines = ["═══════════ 现金流5型画像 (Ch8 教科书算法) ═══════════", ""]

    if portraits:
        lines.append(f"  数据跨度: {len(portraits)} 期")
        lines.append(f"  稳定性评估: {stability}")
        lines.append("")
        lines.append(f"  {'期间':<14s} {'经营CF':>14s} {'投资CF':>14s} {'筹资CF':>14s} {'画像':<20s}")
        lines.append("  " + "─" * 80)
        for p in portraits:
            ocf_s = f"{p['ocf']/1e8:.2f}亿" if p.get("ocf") and abs(p["ocf"]) > 1e4 else f"{p.get('ocf', 0) or 0:.2f}"
            icf_s = f"{p['icf']/1e8:.2f}亿" if p.get("icf") and abs(p["icf"]) > 1e4 else f"{p.get('icf', 0) or 0:.2f}"
            fin_s = f"{p['fin_cf']/1e8:.2f}亿" if p.get("fin_cf") and abs(p["fin_cf"]) > 1e4 else f"{p.get('fin_cf', 0) or 0:.2f}"
            lines.append(f"  {p['period']:<14s} {ocf_s:>14s} {icf_s:>14s} {fin_s:>14s} {p.get('type_cn', '?')}")
    else:
        lines.append("  无可用数据")

    # 最新一期画像详解
    if cf_df is not None and not cf_df.empty:
        signs = extract_cashflow_signs(cf_df)
        portrait = classify_portrait(signs.get("ocf"), signs.get("icf"), signs.get("fcf"))
        if portrait.get("type") != "unknown":
            lines.append("")
            lines.append(f"  最新画像: {portrait['type_cn']}")
            lines.append(f"  解读: {portrait['description']}")
            if portrait.get("danger"):
                lines.append(f"  ⚠️ 风险提示: 经营现金流为负，需警惕流动性风险")

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_trend_score(data: dict, stock_code: str, adapter, cache) -> str:
    """Ch6 逐年改善度趋势评分"""
    income_df = data.get("income")
    balance_df = data.get("balance")

    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"

    # 为每期计算比率，按日期匹配资产负债表
    date_col = "end_date" if "end_date" in income_df.columns else (
        "f_ann_date" if "f_ann_date" in income_df.columns else None
    )

    ratios_history = []
    for i in range(len(income_df)):
        inc_slice = income_df.iloc[i:i + 1]
        # 尝试匹配同期的资产负债表行
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

    lines = ["═══════════ 财务趋势评分 (Ch6 教科书算法) ═══════════", ""]
    lines.append(f"  综合趋势评分: {composite:.1f}/100")
    lines.append(f"  数据跨度: {len(ratios_history)} 期")
    lines.append("")

    for name, score in sorted(trend_scores.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
        lines.append(f"  {name:<12s}  {bar}  {score:.1f}")

    lines.append("")
    lines.append("  ≥80 持续改善 | ≥60 总体向好 | ≥40 波动持平 | ≥20 趋势走弱 | <20 持续恶化")
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_dupont_roic(data: dict, stock_code: str, adapter, cache) -> str:
    """Ch9 增强杜邦分析 + ROIC + 行业话语权 + 资产负债表重构"""
    income_df = data.get("income")
    balance_df = data.get("balance")

    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"
    if balance_df is None or balance_df.empty:
        return "错误：缺少资产负债表数据"

    inc_latest = income_df.iloc[0]
    bal_latest = balance_df.iloc[0]

    # 提取关键字段
    net_profit = _extract_val(inc_latest, ["net_profit", "n_income_attr_p", "净利润"])
    revenue = _extract_val(inc_latest, ["revenue", "total_revenue", "营业收入"])
    total_assets = _extract_val(bal_latest, ["total_assets", "资产总计"])
    equity = _extract_val(bal_latest, ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])
    pretax_profit = _extract_val(inc_latest, ["total_profit", "利润总额"])
    op_profit = _extract_val(inc_latest, ["operate_profit", "营业利润"])
    income_tax = _extract_val(inc_latest, ["income_tax", "所得税费用"])
    interest_exp = _extract_val(inc_latest, ["interest_expense", "fin_exp", "财务费用"])

    # 有息负债
    st_debt = _extract_val(bal_latest, ["st_borrow", "短期借款"]) or 0
    lt_debt = (_extract_val(bal_latest, ["lt_borrow", "长期借款"]) or 0) + (
        _extract_val(bal_latest, ["bond_payable", "应付债券"]) or 0)
    total_equity = equity or 0
    invested_capital = st_debt + lt_debt + total_equity

    ebit = (op_profit or 0) + abs(interest_exp or 0)

    lines = ["═══════════ 增强杜邦分析 (Ch9 教科书算法) ═══════════", ""]

    # 三因子杜邦
    result_3f = dupont_3factor(net_profit, revenue, total_assets, equity)
    if result_3f:
        lines.append("▌ 杜邦三因子分解")
        lines.append(f"  ROE: {result_3f.get('ROE', 'N/A')}%")
        lines.append(f"  销售净利率: {result_3f.get('销售净利率', 'N/A')}%")
        lines.append(f"  总资产周转率: {result_3f.get('总资产周转率', 'N/A')}")
        lines.append(f"  权益乘数: {result_3f.get('权益乘数', 'N/A')}")

        # 盈利模式分类
        nm = result_3f.get("销售净利率", 0)
        at = result_3f.get("总资产周转率", 0)
        em = result_3f.get("权益乘数", 0)
        driver = classify_dupont_driver(nm, at, em)
        lines.append(f"  盈利模式: {driver}")
        lines.append("")

    # 五因子杜邦
    result_5f = dupont_5factor(net_profit, pretax_profit, ebit, revenue, total_assets, equity)
    if result_5f:
        lines.append("▌ 杜邦五因子分解")
        lines.append(f"  ROE: {result_5f.get('ROE', 'N/A')}%")
        lines.append(f"  税负效应: {result_5f.get('税负效应', 'N/A')}")
        lines.append(f"  利息效应: {result_5f.get('利息效应', 'N/A')}")
        lines.append(f"  营业利润率: {result_5f.get('营业利润率', 'N/A')}%")
        lines.append(f"  总资产周转率: {result_5f.get('总资产周转率', 'N/A')}")
        lines.append(f"  权益乘数: {result_5f.get('权益乘数', 'N/A')}")
        lines.append("")

    # ROIC
    roic = calculate_roic(ebit, income_tax, pretax_profit, st_debt, lt_debt, total_equity)
    if roic is not None:
        lines.append("▌ ROIC (投入资本回报率)")
        lines.append(f"  ROIC: {roic:.2f}%")
        lines.append(f"  NOPLAT/投入资本 = EBIT×(1-税率)/(有息负债+权益)")
        lines.append("")

    # 行业话语权
    bargaining = compute_bargaining_power(balance_df)
    bargaining_diag = diagnose_bargaining_power(bargaining)
    lines.append("▌ 行业话语权 (附录1)")
    lines.append(f"  话语权指数: {bargaining:.2f}" if bargaining is not None else "  话语权指数: N/A")
    lines.append(f"  诊断: {bargaining_diag}")
    lines.append("  (营运负债/营运资产，越高对上下游议价越强)")
    lines.append("")

    # 资产负债表重构
    restructured = restructure_balance_sheet(balance_df)
    if restructured:
        lines.append("▌ 管理用资产负债表重构 (附录2)")
        lines.append(f"  金融资产: {restructured.get('金融资产', 'N/A')} 亿")
        lines.append(f"  营运资本: {restructured.get('营运资本', 'N/A')} 亿")
        lines.append(f"  长期经营资产: {restructured.get('长期经营资产', 'N/A')} 亿")
        lines.append(f"  长期股权投资: {restructured.get('长期股权投资', 'N/A')} 亿")
        lines.append(f"  短期有息债务: {restructured.get('短期有息债务', 'N/A')} 亿")
        lines.append(f"  长期有息债务: {restructured.get('长期有息债务', 'N/A')} 亿")
        lines.append(f"  股东权益: {restructured.get('股东权益', 'N/A')} 亿")

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_fraud_ml(data: dict, stock_code: str, adapter, cache) -> str:
    """Ch12-13 ML舞弊检测管线"""
    if not SKLEARN_AVAILABLE:
        return "ML舞弊检测不可用：scikit-learn 未安装。请执行 pip install scikit-learn xgboost imbalanced-learn"

    income_df = data.get("income")
    balance_df = data.get("balance")
    cashflow_df = data.get("cashflow")

    if income_df is None or income_df.empty:
        return "错误：缺少利润表数据"

    lines = ["═══════════ ML舞弊检测 (Ch12-13 教科书算法) ═══════════", ""]

    # 从现有数据提取特征
    ratios = compute_13_ratios(income_df, balance_df, cashflow_df)
    cf_metrics = compute_4_cashflow_metrics(income_df, balance_df, cashflow_df)

    company_features = {
        "roe": ratios.get("ROE", 0),
        "roa": _estimate_roa(ratios, income_df, balance_df),
        "gross_margin": ratios.get("毛利率", 0),
        "net_margin": ratios.get("净利润率", 0),
        "current_ratio": ratios.get("流动比率", 0),
        "quick_ratio": ratios.get("速动比率", 0),
        "debt_to_assets": _estimate_debt_ratio(balance_df),
        "asset_turnover": ratios.get("总资产周转率", 0),
        "inventory_turnover": ratios.get("存货周转率", 0),
        "receivable_turnover": ratios.get("应收账款周转率", 0),
        "revenue_growth": ratios.get("营收增长率", 0),
        "profit_growth": ratios.get("净利润增长率", 0),
        "ocf_to_profit": cf_metrics.get("现金流利润比", 0),
        "revenue_cash_ratio": cf_metrics.get("收入现金比", 0),
        "accrual_ratio": _estimate_accrual_ratio(income_df, balance_df, cashflow_df),
        "goodwill_to_equity": _estimate_goodwill_ratio(balance_df),
    }

    pipeline = FraudDetectionPipeline()

    # 尝试加载预训练模型
    from pathlib import Path
    model_paths = [
        Path.home() / ".financialanalyzer" / "fraud_models.pkl",
        Path(__file__).parent.parent.parent / "pipeline" / "textbook" / "fraud_models.pkl",
    ]
    loaded = False
    for mp in model_paths:
        if mp.exists():
            if pipeline.load(str(mp)):
                loaded = True
                lines.append(f"  已加载预训练模型: {mp}")
                break

    if not loaded:
        lines.append("  ⚠️ 未找到预训练模型文件")
        lines.append("  请先训练模型: pipeline.train('DATA.xlsx') → pipeline.save('fraud_models.pkl')")
        lines.append("  模型搜索路径:")
        for mp in model_paths:
            lines.append(f"    - {mp}")
        lines.append("")
        lines.append("▌ 特征值一览 (用于训练参考)")
        for k, v in company_features.items():
            lines.append(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
        lines.append("\n═══════════════════════════════════════════════════")
        return "\n".join(lines)

    result = pipeline.predict(company_features)

    lines.append(f"  综合欺诈概率: {result.fraud_probability:.2%}")
    lines.append(f"  风险等级: {result.fraud_risk_level}")
    lines.append("")

    if result.model_votes:
        lines.append("▌ 模型投票")
        for model, prob in result.model_votes.items():
            if prob is not None:
                bar = "█" * int(prob * 20) + "░" * (20 - int(prob * 20))
                lines.append(f"  {model:<16s}  {bar}  {prob:.2%}")

    if result.top_risk_features:
        lines.append("")
        lines.append("▌ 关键风险因子")
        for feat in result.top_risk_features:
            lines.append(f"  ⚠ {feat}")

    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _extract_val(row, cols: list[str]) -> float | None:
    """从DataFrame行中按优先级提取数值"""
    if row is None:
        return None
    for c in cols:
        if c in row.index:
            v = row[c]
            try:
                if pd.notna(v):
                    return float(v)
            except (ValueError, TypeError):
                continue
    return None


def _estimate_roa(ratios: dict, income_df, balance_df) -> float:
    """估算ROA = 净利润/总资产"""
    if balance_df is None or balance_df.empty:
        return 0
    np_val = ratios.get("净利润率", 0)
    revenue = _extract_val(income_df.iloc[0] if income_df is not None and not income_df.empty else None,
                           ["revenue", "total_revenue", "营业收入"])
    ta = _extract_val(balance_df.iloc[0], ["total_assets", "资产总计"])
    if np_val and revenue and ta and ta > 0:
        net_profit = np_val / 100 * revenue
        return round(net_profit / ta * 100, 2)
    return 0


def _estimate_debt_ratio(balance_df) -> float:
    """资产负债率"""
    if balance_df is None or balance_df.empty:
        return 0
    tl = _extract_val(balance_df.iloc[0], ["total_liab", "负债合计"])
    ta = _extract_val(balance_df.iloc[0], ["total_assets", "资产总计"])
    if tl and ta and ta > 0:
        return round(tl / ta * 100, 2)
    return 0


def _estimate_accrual_ratio(income_df, balance_df, cashflow_df) -> float:
    """应计比率 = (净利润 - 经营CF) / 总资产"""
    if income_df is None or income_df.empty:
        return 0
    np_val = _extract_val(income_df.iloc[0], ["net_profit", "n_income_attr_p", "净利润"])
    ocf = None
    if cashflow_df is not None and not cashflow_df.empty:
        ocf = _extract_val(cashflow_df.iloc[0], ["n_cashflow_act", "经营活动现金流量净额"])
    ta = None
    if balance_df is not None and not balance_df.empty:
        ta = _extract_val(balance_df.iloc[0], ["total_assets", "资产总计"])
    if np_val and ocf is not None and ta and ta > 0:
        return round((np_val - ocf) / ta, 4)
    return 0


def _estimate_goodwill_ratio(balance_df) -> float:
    """商誉/净资产比"""
    if balance_df is None or balance_df.empty:
        return 0
    gw = _extract_val(balance_df.iloc[0], ["goodwill", "商誉"])
    eq = _extract_val(balance_df.iloc[0], ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"])
    if gw and eq and eq > 0:
        return round(gw / eq * 100, 2)
    return 0


_ANALYSIS_MAP: dict[str, Any] = {
    # 行情分析
    "market_overview": _make_analyzer(MarketAnalyzer, "analyze_market_overview"),
    "price_trend": _make_analyzer(MarketAnalyzer, "analyze_price_trend"),
    "technical": _make_analyzer(TechnicalAnalyzer, "analyze_technical_indicators"),
    # 财务报表
    "income_statement": _make_analyzer(FinancialStatementAnalyzer, "analyze_income_statement"),
    "balance_sheet": _make_analyzer(FinancialStatementAnalyzer, "analyze_balance_sheet"),
    "cashflow": _make_analyzer(FinancialStatementAnalyzer, "analyze_cashflow_statement"),
    # 能力分析
    "profitability": _make_analyzer(ProfitabilityAnalyzer, "analyze_profitability"),
    "operational": _make_analyzer(ProfitabilityAnalyzer, "analyze_operation_ability"),
    "solvency": _make_analyzer(ProfitabilityAnalyzer, "analyze_solvency"),
    "growth": _make_analyzer(ProfitabilityAnalyzer, "analyze_growth_ability"),
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
    "dupont": _make_analyzer(DeepAnalyzer, "analyze_dupont"),
    "zscore": _make_analyzer(DeepAnalyzer, "analyze_zscore"),
    "fscore": _make_analyzer(DeepAnalyzer, "analyze_fscore"),
    "mscore": _make_analyzer(DeepAnalyzer, "analyze_mscore"),
    "fcf": _make_analyzer(DeepAnalyzer, "analyze_free_cashflow"),
    "quadrant": _make_analyzer(DeepAnalyzer, "analyze_cashflow_quadrant"),
    "moat": _make_analyzer(DeepAnalyzer, "analyze_moat"),
    "deep_comprehensive": _make_analyzer(DeepAnalyzer, "generate_comprehensive_report"),
    # 估值与质量
    "pe_valuation": _make_phase2_runner("valuation_analysis"),
    "pe_percentile": _make_phase2_runner("pe_percentile_analysis"),
    "pb_roe": _make_phase2_runner("pb_roe_analysis"),
    "ev_ebitda": _make_phase2_runner("ev_ebitda_analysis"),
    "shareholder_return": _make_phase2_runner("shareholder_return_analysis"),
    "quality": _make_phase2_runner("financial_quality_analysis"),
    # 综合投资分析 (v11 新)
    "comprehensive": _run_comprehensive,
    # 教科书算法模块 (Ch5-Ch13 pipeline)
    "textbook_ratios": _run_textbook_ratios,
    "trend_score": _run_trend_score,
    "cashflow_portrait": _run_cashflow_portrait,
    "dupont_roic": _run_dupont_roic,
    "fraud_ml": _run_fraud_ml,
}


def get_pipeline_stages() -> list[dict]:
    """返回5阶段递进式分析管线（整合全部38项分析）

    结构: [(stage_label, entry_key, [(item_key, item_label), ...]), ...]
    entry_key 为阶段入口分析（一键运行全部子项）
    """
    return [
        ("1. 数据概览", "market_overview", [
            ("market_overview", "行情概览"),
            ("price_trend", "价格趋势"),
            ("technical", "技术指标"),
            ("combined", "量价结合"),
        ]),
        ("2. 财务体检", "ratio_analysis", [
            ("ratio_analysis", "财务比率分析"),
            ("textbook_ratios", "13项核心比率 (Ch5)"),
            ("trend_score", "趋势评分 (Ch6)"),
            ("cashflow_portrait", "现金流画像 (Ch8)"),
            ("income_statement", "利润表"),
            ("balance_sheet", "资产负债表"),
            ("cashflow", "现金流量表"),
            ("profitability", "盈利能力"),
            ("operational", "营运能力"),
            ("solvency", "偿债能力"),
            ("growth", "成长能力"),
        ]),
        ("3. 深度诊断", "dupont", [
            ("dupont", "杜邦分析"),
            ("dupont_roic", "增强杜邦+ROIC (Ch9)"),
            ("fcf", "自由现金流"),
            ("quadrant", "现金流象限"),
            ("moat", "护城河评估"),
            ("deep_comprehensive", "综合深度报告"),
            ("pe_valuation", "PE估值分析"),
            ("pe_percentile", "PE历史分位"),
            ("pb_roe", "PB-ROE模型"),
            ("ev_ebitda", "EV/EBITDA"),
        ]),
        ("4. 风险审查", "audit_full", [
            ("audit_full", "综合审计报告"),
            ("fraud_ml", "ML舞弊检测 (Ch12-13)"),
            ("audit_asset", "资产端信号"),
            ("audit_profit", "利润端信号"),
            ("audit_cashflow", "现金流信号"),
            ("audit_cross", "勾稽关系验证"),
            ("risk", "风险评估"),
            ("zscore", "Z-score"),
            ("fscore", "F-score"),
            ("mscore", "M-score"),
        ]),
        ("5. 估值评级", "comprehensive", [
            ("comprehensive", "综合投资评级"),
            ("pe_valuation", "PE估值分析"),
            ("pe_percentile", "PE历史分位"),
            ("pb_roe", "PB-ROE模型"),
            ("ev_ebitda", "EV/EBITDA"),
            ("shareholder_return", "股东回报"),
            ("quality", "财报质量"),
        ]),
    ]


def get_analysis_list() -> list[dict]:
    """返回分析类型列表（向后兼容 — 保留原有扁平8组结构）"""
    return [
        ("行情分析", [
            ("market_overview", "行情概览"),
            ("price_trend", "价格趋势"),
            ("technical", "技术指标"),
        ]),
        ("财务报表", [
            ("income_statement", "利润表"),
            ("balance_sheet", "资产负债表"),
            ("cashflow", "现金流量表"),
        ]),
        ("能力分析", [
            ("profitability", "盈利能力"),
            ("operational", "营运能力"),
            ("solvency", "偿债能力"),
            ("growth", "成长能力"),
        ]),
        ("综合评估", [
            ("combined", "量价结合"),
            ("risk", "风险评估"),
        ]),
        ("财务比率", [
            ("ratio_analysis", "财务比率分析"),
        ]),
        ("财务审计", [
            ("audit_asset", "资产端信号"),
            ("audit_profit", "利润端信号"),
            ("audit_cashflow", "现金流信号"),
            ("audit_cross", "勾稽关系验证"),
            ("audit_full", "综合审计报告"),
        ]),
        ("深度分析", [
            ("dupont", "杜邦分析"),
            ("zscore", "Z-score"),
            ("fscore", "F-score"),
            ("mscore", "M-score"),
            ("fcf", "自由现金流"),
            ("quadrant", "现金流象限"),
            ("moat", "护城河评估"),
            ("deep_comprehensive", "综合深度报告"),
        ]),
        ("估值与质量", [
            ("pe_valuation", "PE估值分析"),
            ("pe_percentile", "PE历史分位"),
            ("pb_roe", "PB-ROE模型"),
            ("ev_ebitda", "EV/EBITDA"),
            ("shareholder_return", "股东回报"),
            ("quality", "财报质量"),
        ]),
        ("综合投资分析", [
            ("comprehensive", "综合投资评级"),
        ]),
        ("教科书算法 (Ch5-Ch13)", [
            ("textbook_ratios", "13项核心比率 (Ch5)"),
            ("trend_score", "趋势评分 (Ch6)"),
            ("cashflow_portrait", "现金流画像 (Ch8)"),
            ("dupont_roic", "增强杜邦+ROIC (Ch9)"),
            ("fraud_ml", "ML舞弊检测 (Ch12-13)"),
        ]),
    ]
