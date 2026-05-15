"""
Audit Calculator - 桥接新审计引擎
===================================
保留原有接口（run_full_audit, asset_signals 等），
内部调用新的插件式信号引擎。
兼容 UI 调用，无需修改 UI 代码。
"""
import pandas as pd
import numpy as np
from ..logging_config import get_logger
from .signals import (
    AuditEngine, AuditResult, SignalRegistry,
    SignalLevel, SignalCategory, AuditThresholds, DEFAULT_THRESHOLDS,
    CATEGORY_NAMES, CATEGORY_ICONS, LEVEL_ICONS,
)

logger = get_logger(__name__)


class AuditCalculator:
    """财务审计计算器 - 桥接新引擎，兼容旧接口"""

    def __init__(self, data: dict, stock_code: str = ""):
        self.data = data
        self.stock_code = stock_code

    # ====================================================================
    # 旧接口兼容：run_full_audit()
    # ====================================================================
    def run_full_audit(self) -> dict:
        """运行完整审计（兼容旧接口，返回 dict）"""
        result = self._run_engine()

        # 转为旧格式 dict（供 _format_audit_report 使用）
        output = {
            "risk_level": result.risk_level,
            "risk_icon": result.risk_icon,
            "total_score": result.total_score,
            "high_count": result.high_count,
            "medium_count": result.medium_count,
            "low_count": result.low_count,
            "total_signals": len(result.all_signals),
            "all_signals": [],
            "dimensions": {},
            "recommendations": result.recommendations,
            "radar_data": result.radar_data,
            "heatmap_data": result.heatmap_data,
        }

        for sig in result.all_signals:
            output["all_signals"].append({
                "id": sig.id,
                "name": sig.name,
                "category": sig.category.value,
                "category_cn": CATEGORY_NAMES.get(sig.category, sig.category.value),
                "level": sig.level.value,
                "level_icon": LEVEL_ICONS.get(sig.level, "⚪"),
                "value": sig.value,
                "threshold": sig.threshold,
                "conclusion": sig.conclusion,
                "detail": sig.detail,
            })

        for cat_str, dim in result.dimensions.items():
            output["dimensions"][cat_str] = {
                "name": CATEGORY_NAMES.get(dim.category, cat_str),
                "icon": CATEGORY_ICONS.get(dim.category, "📊"),
                "score": dim.score,
                "signal_count": len(dim.signals),
                "details": dim.details,
            }

        return output

    # ====================================================================
    # 旧接口兼容：分类信号
    # ====================================================================
    def asset_signals(self) -> dict:
        """资产端信号（兼容旧接口）"""
        return self._run_category(SignalCategory.ASSET)

    def profit_signals(self) -> dict:
        """利润端信号（兼容旧接口）"""
        return self._run_category(SignalCategory.PROFIT)

    def cashflow_signals(self) -> dict:
        """现金流信号（兼容旧接口）"""
        return self._run_category(SignalCategory.CASHFLOW)

    def cross_validation(self) -> dict:
        """勾稽验证信号（兼容旧接口）"""
        return self._run_category(SignalCategory.CROSS_VALIDATION)

    # ====================================================================
    # 新接口：获取结构化结果
    # ====================================================================
    def get_audit_result(self) -> AuditResult:
        """获取结构化审计结果（新接口）"""
        return self._run_engine()

    # ====================================================================
    # 内部方法
    # ====================================================================
    def _run_engine(self) -> AuditResult:
        """运行审计引擎"""
        current, previous = self._build_periods()
        context = self._build_context()
        engine = AuditEngine(current, previous, context)
        return engine.run()

    def _run_category(self, category: SignalCategory) -> dict:
        """运行指定分类的信号"""
        result = self._run_engine()
        dim = result.dimensions.get(category.value)
        if not dim:
            return {"error": "no data"}

        signals = {}
        for i, sig in enumerate(dim.signals):
            signals[sig.id] = {
                "level": sig.level.value,
                "desc": f"{sig.name}: {sig.value}",
                "detail": sig.conclusion,
            }
        if not signals:
            signals["status"] = {"level": "ok", "desc": "各项检测正常", "detail": ""}
        return signals

    def _build_periods(self) -> tuple:
        """构建当期/上期数据"""
        balance = self._get_df("balance")
        income = self._get_df("income")
        cashflow = self._get_df("cashflow")
        fin = self._get_df("financial")

        current = {}
        previous = None

        for df in [balance, income, cashflow, fin]:
            if df is not None and not df.empty:
                current.update(df.iloc[0].to_dict())
                if previous is None and len(df) > 1:
                    previous = {}
                if previous is not None and len(df) > 1:
                    previous.update(df.iloc[1].to_dict())

        # 字段别名
        current = self._add_aliases(current)
        if previous:
            previous = self._add_aliases(previous)

        return current, previous

    def _build_context(self) -> dict:
        """构建上下文"""
        ctx = {
            "stock_code": self.stock_code,
        }

        # 多年数据
        multi_year = self._build_multi_year(5)
        if multi_year:
            ctx["multi_year_data"] = multi_year

        # 尝试从 self.data 获取额外数据
        for key in ["mscore_result", "zscore_result", "dupont_result",
                     "audit_opinion", "related_party", "fund_occupation",
                     "executive_changes", "auditor_change",
                     "ar_aging_data", "accounting_changes"]:
            val = self.data.get(key)
            if val:
                # 映射到context的key
                ctx_key = key.replace("_result", "")
                ctx[ctx_key] = val

        return ctx

    def _build_multi_year(self, years=5) -> list:
        """构建多年数据列表"""
        balance = self._get_df("balance", years)
        income = self._get_df("income", years)
        cashflow = self._get_df("cashflow", years)
        fin = self._get_df("financial", years)

        periods = []
        max_len = max(
            len(balance) if balance is not None else 0,
            len(income) if income is not None else 0,
            len(cashflow) if cashflow is not None else 0,
            len(fin) if fin is not None else 0,
        )

        for i in range(min(years, max_len)):
            data = {}
            for df in [balance, income, cashflow, fin]:
                if df is not None and i < len(df):
                    data.update(df.iloc[i].to_dict())
            periods.append(self._add_aliases(data))
        return periods

    def _get_df(self, data_type: str, years: int = 2) -> pd.DataFrame | None:
        """获取年报数据"""
        df = self.data.get(data_type)
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return None
        if isinstance(df, pd.DataFrame) and "end_date" in df.columns:
            annual = df[df["end_date"].str.endswith("1231")].drop_duplicates("end_date").head(years)
            if annual.empty:
                annual = df.drop_duplicates("end_date").head(years)
            return annual
        return df

    def _add_aliases(self, d: dict) -> dict:
        """添加字段别名"""
        aliases = {
            "equity": ["total_hldr_eqy_exc_min_int", "total_equity"],
            "inventory": ["inventories"],
            "accounts_receivable": ["accounts_receiv", "acc_receivable"],
            "cash": ["money_cap"],
            "net_ppe": ["fix_assets"],
            "revenue": ["total_revenue"],
            "net_profit": ["n_income", "n_income_attr_p"],
            "op_cost": ["oper_cost"],
            "op_cashflow": ["n_cashflow_act"],
            "inv_cf": ["n_cashflow_inv_act"],
            "fin_cf": ["n_cash_flows_fnc_act", "n_cash_finance_act"],
        }
        p = dict(d)
        for target, candidates in aliases.items():
            if target not in p:
                for c in candidates:
                    if c in d and d[c] is not None:
                        try:
                            v = float(d[c])
                            if not pd.isna(v):
                                p[target] = v
                                break
                        except (ValueError, TypeError):
                            pass
        return p
