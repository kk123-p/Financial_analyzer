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
from financial_analyzer.data_sources.adapter import DataSourceAdapter
from financial_analyzer.cache.manager import DataCacheManager

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
        # 确定实例化参数
        if issubclass(cls, BaseAnalyzer):
            analyzer = cls(data, stock_code, adapter, cache)
        else:
            analyzer = cls(data, stock_code)
        return getattr(analyzer, method_name)()
    return runner


def _run_ratio_analyzer(data: dict, stock_code: str, adapter, cache) -> str:
    fa = FinancialRatioAnalyzer(data, stock_code)
    result = fa.analyze()
    # 格式化 dict 为文本
    lines = ["═══════════════════ 财务比率分析 ═══════════════════", ""]
    for category, ratios in result.items():
        if category == "综合评分":
            lines.append(f"\n▌ {category}")
            lines.append(f"  总得分: {ratios.get('总分', 'N/A')}")
            lines.append(f"  评级: {ratios.get('评级', 'N/A')}")
        else:
            lines.append(f"\n▌ {category}")
            if isinstance(ratios, dict):
                for k, v in ratios.items():
                    if k != "评级":
                        lines.append(f"  {k}: {v}")
                if "评级" in ratios:
                    lines.append(f"  综合评级: {ratios['评级']}")
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_phase2(data: dict, stock_code: str, adapter, cache) -> str:
    pa = Phase2Analyzer(data, stock_code, adapter)
    result = pa.analyze()
    lines = ["═══════════════════ 估值与质量分析 ═══════════════════", ""]
    for section, content in result.items():
        lines.append(f"\n▌ {section}")
        lines.append(str(content))
    lines.append("\n═══════════════════════════════════════════════════")
    return "\n".join(lines)


def _run_audit_asset(data: dict, stock_code: str, adapter, cache) -> str:
    analyzer = AuditAnalyzer(data, stock_code, adapter, cache)
    return analyzer.analyze_audit()


def _run_audit_full(data: dict, stock_code: str, adapter, cache) -> str:
    analyzer = AuditAnalyzer(data, stock_code, adapter, cache)
    return analyzer.analyze_audit()


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
    "audit_asset": _run_audit_asset,
    "audit_profit": _run_audit_asset,
    "audit_cashflow": _run_audit_asset,
    "audit_cross": _run_audit_asset,
    "audit_full": _run_audit_full,
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
    "peer": _run_phase2,
    "valuation": _run_phase2,
    "shareholder": _run_phase2,
    "quality": _run_phase2,
}


def get_analysis_list() -> list[dict]:
    """返回分析类型列表（用于侧边栏导航）"""
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
            ("peer", "行业对比"),
            ("valuation", "相对估值"),
            ("shareholder", "股东回报"),
            ("quality", "财报质量"),
        ]),
    ]
