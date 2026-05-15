"""
财务异常排查分析器（重构版）
==============================
使用插件式信号注册系统，支持6维度32个信号检测。
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..calculator.signals import (
    AuditEngine, AuditResult, DimensionScore,
    SignalLevel, SignalCategory, SignalRegistry,
    AuditThresholds, DEFAULT_THRESHOLDS,
    CATEGORY_NAMES, CATEGORY_ICONS, LEVEL_ICONS,
)
from ..config import SEPARATOR_LIGHT
from ..logging_config import get_logger

import unicodedata

logger = get_logger(__name__)


def _cjk_ljust(s, width):
    s = str(s)
    cjk_count = sum(1 for c in s if unicodedata.east_asian_width(c) in ('F', 'W'))
    return s + ' ' * max(0, width - len(s) - cjk_count)


def _cjk_rjust(s, width):
    s = str(s)
    cjk_count = sum(1 for c in s if unicodedata.east_asian_width(c) in ('F', 'W'))
    return ' ' * max(0, width - len(s) - cjk_count) + s


class AuditAnalyzer(BaseAnalyzer):
    """财务异常排查分析器（重构版）"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager,
                 thresholds: AuditThresholds = None):
        super().__init__(data, stock_code, data_adapter, cache_manager)
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def _get_basic_info(self) -> dict:
        info = {}
        stock_basic = self.data.get("stock_basic")
        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            info["name"] = sb.get("name", "N/A")
            info["industry"] = sb.get("industry", "N/A")
        basic = self.data.get("basic")
        if basic is not None and not basic.empty:
            b = basic.iloc[0]
            info["pe"] = b.get("pe") or b.get("pe_ttm")
            info["pb"] = b.get("pb")
        return info

    def _get_annual(self, data_type, years=5):
        df = self.data.get(data_type)
        if df is None or df.empty:
            df, _ = self._fetch_data(data_type, years)
        if df is None or df.empty:
            import pandas as pd
            return pd.DataFrame()
        annual = df[df["end_date"].str.endswith("1231")].drop_duplicates("end_date").head(years)
        if annual.empty:
            annual = df.drop_duplicates("end_date").head(years)
        return annual

    def _build_period(self, row_dict: dict) -> dict:
        """从原始数据构建 period dict（兼容多数据源字段名）"""
        p = dict(row_dict)
        aliases = {
            "equity": ["total_hldr_eqy_exc_min_int", "total_equity"],
            "inventory": ["inventories"],
            "accounts_receivable": ["accounts_receiv", "acc_receivable"],
            "cash": ["money_cap"],
            "net_ppe": ["fix_assets"],
            "revenue": ["total_revenue"],
            "net_profit": ["n_income", "n_income_attr_p"],
            "op_cost": ["oper_cost"],
            "pre_tax_profit": ["total_profit"],
            "tax_expense": ["income_tax"],
            "interest_expense": ["fin_exp"],
            "current_assets": ["total_cur_assets"],
            "current_liab": ["total_cur_liab"],
            "op_cashflow": ["n_cashflow_act"],
            "inv_cf": ["n_cashflow_inv_act"],
            "fin_cf": ["n_cash_flows_fnc_act", "n_cash_finance_act"],
            "capex": ["c_pay_acq_const_fiolta", "c_pay_acq_const_fiamt"],
        }
        for target, candidates in aliases.items():
            if target not in p:
                for c in candidates:
                    if c in row_dict and row_dict[c] is not None:
                        p[target] = row_dict[c]
                        break
        return p

    def _build_multi_year(self, years=5) -> list:
        """构建多年数据列表"""
        df_balance = self._get_annual("balance", years)
        df_income = self._get_annual("income", years)
        df_cashflow = self._get_annual("cashflow", years)
        df_fin = self._get_annual("financial", years)

        periods = []
        for i in range(min(years, len(df_balance))):
            data = {}
            if not df_balance.empty and i < len(df_balance):
                data.update(df_balance.iloc[i].to_dict())
            if not df_income.empty and i < len(df_income):
                data.update(df_income.iloc[i].to_dict())
            if not df_cashflow.empty and i < len(df_cashflow):
                data.update(df_cashflow.iloc[i].to_dict())
            if not df_fin.empty and i < len(df_fin):
                data.update(df_fin.iloc[i].to_dict())
            periods.append(self._build_period(data))
        return periods

    def _prepare_context(self) -> dict:
        """准备上下文数据（M-score, Z-score, 杜邦分析等）"""
        ctx = {
            "stock_code": self.stock_code,
            "basic_info": self._get_basic_info(),
        }

        # 尝试获取已有的深度分析结果
        # M-score
        mscore = self.data.get("mscore_result")
        if mscore:
            ctx["mscore"] = mscore

        # Z-score
        zscore = self.data.get("zscore_result")
        if zscore:
            ctx["zscore"] = zscore

        # 杜邦分析
        dupont = self.data.get("dupont_result")
        if dupont:
            ctx["dupont_analysis"] = dupont

        # 治理相关数据（从外部传入）
        for key in ["audit_opinion", "related_party", "fund_occupation",
                     "executive_changes", "auditor_change",
                     "ar_aging_data", "accounting_changes"]:
            if key in self.data:
                ctx[key] = self.data[key]

        return ctx

    def analyze_audit(self) -> str:
        """生成财务异常排查报告"""
        result = RF.header("财务异常排查报告")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n"
            if basic_info.get("industry"):
                result += f"  行业: {basic_info['industry']}\n"
            result += "\n"

        # 获取数据
        df_balance = self._get_annual("balance", 2)
        df_income = self._get_annual("income", 2)
        df_cashflow = self._get_annual("cashflow", 2)
        df_fin = self._get_annual("financial", 2)

        if df_balance.empty or df_income.empty:
            return result + "  财务数据不足，无法进行异常排查\n"

        cur_end = str(df_balance.iloc[0].get("end_date", ""))
        signal_count = len(SignalRegistry.list_signals())
        result += f"  分析期: {cur_end}\n"
        result += f"  检测信号: {signal_count} 个 | 检测维度: 6 个\n\n"

        # 构建当期/上期数据
        cur_data = {}
        prev_data = {}
        for df_src in [df_balance, df_income, df_cashflow, df_fin]:
            if not df_src.empty:
                cur_data.update(df_src.iloc[0].to_dict())
                if len(df_src) > 1:
                    prev_data.update(df_src.iloc[1].to_dict())

        current = self._build_period(cur_data)
        previous = self._build_period(prev_data) if prev_data else None

        # 构建多年数据
        multi_year = self._build_multi_year(5)

        # 构建上下文
        ctx = self._prepare_context()
        ctx["multi_year_data"] = multi_year

        # 运行审计引擎
        engine = AuditEngine(current, previous, ctx, self.thresholds)
        audit = engine.run()

        # ===== 总览 =====
        result += RF.section("🔍 综合风险评估")
        result += f"  {audit.risk_icon} 风险等级: {audit.risk_level}  (综合得分: {audit.total_score}/100)\n"
        result += f"  发现信号: {len(audit.all_signals)} 个"
        result += f" (高风险 {audit.high_count} | 中风险 {audit.medium_count} | 低风险 {audit.low_count})\n"
        result += f"  注册信号: {signal_count} 个已执行检测\n\n"

        # 各维度得分
        result += RF.section("各维度评分")
        for cat in SignalCategory:
            dim = audit.dimensions.get(cat.value)
            if dim:
                icon = CATEGORY_ICONS.get(cat, "📊")
                name = CATEGORY_NAMES.get(cat, cat.value)
                s = dim.score
                bar = "█" * (s // 10) + "░" * ((100 - s) // 10)
                sig_count = len(dim.signals)
                result += f"  {icon} {name:<12} {bar} {s:>5.0f}/100"
                if sig_count > 0:
                    result += f"  ({sig_count}个信号)"
                result += "\n"
        result += "\n"

        # ===== 雷达图数据预览 =====
        if audit.radar_data:
            result += RF.section("📊 雷达图数据")
            for name, score in audit.radar_data.items():
                result += f"  {name}: {score:.0f}\n"
            result += "\n"

        # ===== 详细信号 =====
        if audit.all_signals:
            result += RF.section("⚠️ 异常信号详情")

            # 按等级排序：HIGH > MEDIUM > LOW
            sorted_signals = sorted(audit.all_signals,
                                    key=lambda s: {"high": 0, "medium": 1, "low": 2, "info": 3}.get(s.level.value, 9))

            for i, sig in enumerate(sorted_signals, 1):
                level_icon = LEVEL_ICONS.get(sig.level, "⚪")
                cat_name = CATEGORY_NAMES.get(sig.category, "")
                result += f"\n  {level_icon} [{i}] {sig.name}"
                result += f"  ({cat_name})\n"
                result += f"     当前值: {sig.value}\n"
                result += f"     标  准: {sig.threshold}\n"
                result += f"     结  论: {sig.conclusion}\n"
                if sig.detail:
                    result += f"     补  充: {sig.detail}\n"
        else:
            result += RF.section("✅ 异常信号详情")
            result += "  未发现明显异常信号\n"

        # ===== 各维度详细数据 =====
        for cat in SignalCategory:
            dim = audit.dimensions.get(cat.value)
            if dim and dim.details:
                icon = CATEGORY_ICONS.get(cat, "📊")
                name = CATEGORY_NAMES.get(cat, cat.value)
                result += f"\n{RF.section(f'{icon} {name} - 检测数据')}\n"
                for d in dim.details:
                    result += f"  · {d}\n"

        # ===== 热力图数据 =====
        if audit.heatmap_data:
            result += f"\n{RF.section('🔥 信号热力图')}\n"
            for item in audit.heatmap_data:
                level_icon = LEVEL_ICONS.get(SignalLevel(item["level"]), "⚪")
                result += f"  {level_icon} {item['name']:<16} [{item['category']}] 权重={item['weight']}\n"

        # ===== 建议 =====
        result += f"\n{RF.section('📋 排查建议')}\n"
        for rec in audit.recommendations:
            result += f"  {rec}\n"

        result += "\n  * 本报告基于公开财务数据自动生成，仅供参考，不构成投资建议。\n"
        result += f"  * 检测模型: 插件式信号引擎 ({signal_count}个信号 × 6个维度)\n"
        result += f"  * 支持信号: 资产端 | 利润端 | 现金流 | 勾稽验证 | 治理披露 | 模型预警\n"

        result += RF.footer()
        return result

    def get_audit_result(self) -> AuditResult:
        """
        获取结构化审计结果（供UI可视化使用）

        Returns:
            AuditResult 对象，包含 radar_data, heatmap_data 等
        """
        df_balance = self._get_annual("balance", 2)
        df_income = self._get_annual("income", 2)
        df_cashflow = self._get_annual("cashflow", 2)
        df_fin = self._get_annual("financial", 2)

        if df_balance.empty or df_income.empty:
            return None

        cur_data = {}
        prev_data = {}
        for df_src in [df_balance, df_income, df_cashflow, df_fin]:
            if not df_src.empty:
                cur_data.update(df_src.iloc[0].to_dict())
                if len(df_src) > 1:
                    prev_data.update(df_src.iloc[1].to_dict())

        current = self._build_period(cur_data)
        previous = self._build_period(prev_data) if prev_data else None
        multi_year = self._build_multi_year(5)
        ctx = self._prepare_context()
        ctx["multi_year_data"] = multi_year

        engine = AuditEngine(current, previous, ctx, self.thresholds)
        return engine.run()
