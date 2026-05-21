"""
分析调度服务 — Web 层适配器

委托到 financial_analyzer.services.analysis (统一分析调度)，
保留 Web 层专有的 UI 辅助函数（分析列表、管线分组）。
"""
import logging
from typing import Any

from financial_analyzer.services.analysis import (
    AnalysisDispatcher, ANALYSIS_MAP,
    _run_comprehensive, _run_ratio_analyzer, _run_textbook_ratios,
    _run_trend_score, _run_cashflow_portrait, _run_dupont_roic, _run_fraud_ml,
    _make_analyzer, _make_phase2_runner, _make_audit_runner,
)
from financial_analyzer.data_sources.adapter import DataSourceAdapter
from financial_analyzer.cache.manager import DataCacheManager

logger = logging.getLogger(__name__)


class AnalysisService(AnalysisDispatcher):
    """Web 层分析服务 — 继承统一调度器，保持向后兼容"""

    def __init__(self, adapter: DataSourceAdapter, cache: DataCacheManager):
        super().__init__(adapter, cache)


# ============================================================================
# Web 层 UI 辅助函数（分析列表分组、管线阶段）
# ============================================================================

def get_pipeline_stages() -> list[dict]:
    """5阶段递进式分析管线（38项）"""
    return [
        ("1. 数据概览", "market_overview", [
            ("market_overview", "行情概览"), ("price_trend", "价格趋势"),
            ("technical", "技术指标"), ("combined", "量价结合"),
        ]),
        ("2. 财务体检", "ratio_analysis", [
            ("ratio_analysis", "财务比率分析"), ("textbook_ratios", "13项核心比率 (Ch5)"),
            ("trend_score", "趋势评分 (Ch6)"), ("cashflow_portrait", "现金流画像 (Ch8)"),
            ("income_statement", "利润表"), ("balance_sheet", "资产负债表"),
            ("cashflow", "现金流量表"), ("profitability", "盈利能力"),
            ("operational", "营运能力"), ("solvency", "偿债能力"),
            ("growth", "成长能力"),
        ]),
        ("3. 深度诊断", "dupont", [
            ("dupont", "杜邦分析"), ("dupont_roic", "增强杜邦+ROIC (Ch9)"),
            ("fcf", "自由现金流"), ("quadrant", "现金流象限"),
            ("moat", "护城河评估"), ("deep_comprehensive", "综合深度报告"),
            ("pe_valuation", "PE估值分析"), ("pe_percentile", "PE历史分位"),
            ("pb_roe", "PB-ROE模型"), ("ev_ebitda", "EV/EBITDA"),
        ]),
        ("4. 风险审查", "audit_full", [
            ("audit_full", "综合审计报告"), ("fraud_ml", "ML舞弊检测 (Ch12-13)"),
            ("audit_asset", "资产端信号"), ("audit_profit", "利润端信号"),
            ("audit_cashflow", "现金流信号"), ("audit_cross", "勾稽关系验证"),
            ("risk", "风险评估"), ("zscore", "Z-score"),
            ("fscore", "F-score"), ("mscore", "M-score"),
        ]),
        ("5. 估值评级", "comprehensive", [
            ("comprehensive", "综合投资评级"), ("pe_valuation", "PE估值分析"),
            ("pe_percentile", "PE历史分位"), ("pb_roe", "PB-ROE模型"),
            ("ev_ebitda", "EV/EBITDA"), ("shareholder_return", "股东回报"),
            ("quality", "财报质量"),
        ]),
    ]


def get_analysis_list() -> list[dict]:
    """分析类型列表（扁平8组结构，向后兼容）"""
    return [
        ("行情分析", [
            ("market_overview", "行情概览"), ("price_trend", "价格趋势"),
            ("technical", "技术指标"),
        ]),
        ("财务报表", [
            ("income_statement", "利润表"), ("balance_sheet", "资产负债表"),
            ("cashflow", "现金流量表"),
        ]),
        ("能力分析", [
            ("profitability", "盈利能力"), ("operational", "营运能力"),
            ("solvency", "偿债能力"), ("growth", "成长能力"),
        ]),
        ("综合评估", [
            ("combined", "量价结合"), ("risk", "风险评估"),
        ]),
        ("财务比率", [
            ("ratio_analysis", "财务比率分析"),
        ]),
        ("财务审计", [
            ("audit_asset", "资产端信号"), ("audit_profit", "利润端信号"),
            ("audit_cashflow", "现金流信号"), ("audit_cross", "勾稽关系验证"),
            ("audit_full", "综合审计报告"),
        ]),
        ("深度分析", [
            ("dupont", "杜邦分析"), ("zscore", "Z-score"),
            ("fscore", "F-score"), ("mscore", "M-score"),
            ("fcf", "自由现金流"), ("quadrant", "现金流象限"),
            ("moat", "护城河评估"), ("deep_comprehensive", "综合深度报告"),
        ]),
        ("估值与质量", [
            ("pe_valuation", "PE估值分析"), ("pe_percentile", "PE历史分位"),
            ("pb_roe", "PB-ROE模型"), ("ev_ebitda", "EV/EBITDA"),
            ("shareholder_return", "股东回报"), ("quality", "财报质量"),
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
