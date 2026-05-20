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
            ("pe_valuation", "PE估值分析"),
            ("pe_percentile", "PE历史分位"),
            ("pb_roe", "PB-ROE模型"),
            ("ev_ebitda", "EV/EBITDA"),
            ("shareholder_return", "股东回报"),
            ("quality", "财报质量"),
        ]),
    ]
