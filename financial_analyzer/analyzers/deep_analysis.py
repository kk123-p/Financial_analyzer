"""
深度分析器 - 整合专业级财务分析模型
杜邦分析、Z-score、F-score、M-score、自由现金流、现金流象限、护城河
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..calculator.deep_analysis import DeepAnalysisCalculator as DAC
from ..utils.helpers import cjk_ljust, cjk_rjust
from ..config import SEPARATOR_LIGHT, SEPARATOR_HEAVY, DCF_SCENARIOS, DCF_GROWTH_YEARS
from ..logging_config import get_logger

import pandas as pd
import numpy as np

logger = get_logger(__name__)


class DeepAnalyzer(BaseAnalyzer):
    """深度财务分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    # ========================================================================
    # 数据准备辅助方法
    # ========================================================================

    def _get_annual_data(self, data_type: str, years: int = 5) -> pd.DataFrame:
        """获取年报数据（优先从 self.data 取，没有再调适配器）"""
        # 先检查 self.data 中是否已有数据
        df = self.data.get(data_type)
        if df is None or df.empty:
            df, _ = self._fetch_data(data_type, years=years)
        if df is None or df.empty:
            return pd.DataFrame()
        annual = df[df["end_date"].str.endswith("1231")].head(years)
        if annual.empty:
            annual = df.head(years)
        return annual

    @staticmethod
    def _get_field(row, *candidates, default=None, _context=""):
        """从 row 中按优先级取字段值（兼容不同数据源的列名差异）"""
        for key in candidates:
            val = row.get(key)
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                return val
        # 所有候选字段都未匹配时记录诊断信息
        if candidates:
            available = [k for k in row.index if row.get(k) is not None]
            logger.debug(f"字段映射未命中 {_context}: 尝试了 {list(candidates)}, 可用字段: {available[:10]}")
        return default

    def _build_periods_data(self, years: int = 5) -> list:
        """构建多年数据列表，用于趋势分析"""
        df_income = self._get_annual_data("income", years)
        df_balance = self._get_annual_data("balance", years)
        df_cashflow = self._get_annual_data("cashflow", years)
        df_fin = self._get_annual_data("financial", years)

        if df_balance.empty:
            return []

        periods = []
        # 以 balance 的 end_date 为基准
        for _, bal_row in df_balance.iterrows():
            end_date = str(bal_row.get("end_date", ""))
            period = {"end_date": end_date}

            # 资产负债表数据（兼容 tushare / akshare 字段名）
            period["total_assets"] = self._get_field(bal_row, "total_assets")
            period["total_liab"] = self._get_field(bal_row, "total_liab")
            period["equity"] = self._get_field(
                bal_row, "total_hldr_eqy_exc_min_int", "total_equity", "equity")
            period["current_assets"] = self._get_field(
                bal_row, "total_cur_assets", "current_assets")
            period["current_liab"] = self._get_field(
                bal_row, "total_cur_liab", "current_liab", "total_cur_liab")
            period["inventory"] = self._get_field(bal_row, "inventories", "inventory")
            period["accounts_receivable"] = self._get_field(
                bal_row, "accounts_receivable", "accounts_receiv", "acc_receivable")
            period["cash"] = self._get_field(bal_row, "money_cap", "cash")
            period["retained_earnings"] = self._get_field(
                bal_row, "retained_earnings", "undistr_porfit")
            period["net_ppe"] = self._get_field(
                bal_row, "fix_assets", "net_ppe", "fix_assets_total")
            period["other_assets"] = self._get_field(
                bal_row, "total_nca", "other_assets")

            # 利润表数据
            if not df_income.empty:
                inc_row = df_income[df_income["end_date"] == end_date]
                if not inc_row.empty:
                    inc = inc_row.iloc[0]
                    period["revenue"] = self._get_field(
                        inc, "total_revenue", "revenue")
                    period["net_profit"] = self._get_field(
                        inc, "net_profit", "n_income", "n_income_attr_p")
                    period["op_cost"] = self._get_field(
                        inc, "oper_cost", "oper_cost", "total_cogs")
                    rev = period["revenue"]
                    cost = period["op_cost"]
                    period["gross_profit"] = (rev - cost) if rev and cost else None
                    period["ebit"] = self._get_field(
                        inc, "ebit", "operate_profit")
                    period["interest_expense"] = self._get_field(
                        inc, "fin_exp", "interest_expense")
                    period["tax_expense"] = self._get_field(
                        inc, "income_tax", "tax_expense")
                    period["pre_tax_profit"] = self._get_field(
                        inc, "total_profit", "pretax_profit")
                    sell = self._get_field(inc, "sell_exp", default=0) or 0
                    admin = self._get_field(inc, "admin_exp", default=0) or 0
                    period["sga_expense"] = sell + admin
                    period["depreciation"] = self._get_field(
                        inc, "fa_depr", "assets_depr", "depreciation")

            # 现金流量表数据
            if not df_cashflow.empty:
                cf_row = df_cashflow[df_cashflow["end_date"] == end_date]
                if not cf_row.empty:
                    cf = cf_row.iloc[0]
                    period["op_cashflow"] = self._get_field(
                        cf, "n_cashflow_act", "op_cashflow")
                    period["inv_cf"] = self._get_field(
                        cf, "n_cashflow_inv_act", "inv_cashflow")
                    period["fin_cf"] = self._get_field(
                        cf, "n_cash_flows_fnc_act", "n_cash_finance_act", "fin_cashflow")
                    period["capex"] = self._get_field(
                        cf, "c_pay_acq_const_fiolta", "c_pay_acq_const_fiamt", "capex")
                    # tushare 直接提供 free_cashflow
                    if period["capex"] is None:
                        fcf_direct = self._get_field(cf, "free_cashflow")
                        if fcf_direct is not None and period["op_cashflow"]:
                            period["capex"] = period["op_cashflow"] - fcf_direct

            # 财务指标数据
            if not df_fin.empty:
                fin_row = df_fin[df_fin["end_date"] == end_date]
                if not fin_row.empty:
                    fin = fin_row.iloc[0]
                    period["roe"] = self._get_field(fin, "roe")
                    # 股本信息
                    period["shares"] = self._get_field(
                        fin, "total_share")
                    # 营运资本 (tushare fina_indicator 直接提供)
                    if period.get("working_capital") is None:
                        period["working_capital"] = self._get_field(
                            fin, "working_capital")

            periods.append(period)

        return periods

    def _get_basic_info(self) -> dict:
        """获取股票基本信息"""
        info = {}
        # 1. 从 stock_basic 获取公司信息
        stock_basic = self.data.get("stock_basic")
        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            info["name"] = sb.get("name", "N/A")
            info["industry"] = sb.get("industry", "N/A")
        # 2. 从 basic (daily_basic) 获取行情数据
        basic = self.data.get("basic")
        if basic is not None and not basic.empty:
            b = basic.iloc[0]
            info["market_cap"] = b.get("total_mv")
            info["pe"] = b.get("pe") or b.get("pe_ttm")
            info["pb"] = b.get("pb")
            info["shares"] = b.get("total_share") or b.get("float_share")
        # 3. 从 daily_basic 补充
        daily_basic = self.data.get("daily_basic")
        if daily_basic is not None and not daily_basic.empty:
            db = daily_basic.iloc[0]
            info["market_cap"] = info.get("market_cap") or db.get("total_mv")
            info["pe"] = info.get("pe") or db.get("pe") or db.get("pe_ttm")
            info["pb"] = info.get("pb") or db.get("pb")
            info["shares"] = info.get("shares") or db.get("total_share") or db.get("float_share")
        return info

    # ========================================================================
    # 1. 杜邦分析
    # ========================================================================

    def analyze_dupont(self) -> str:
        """杜邦分析报告（增强版）"""
        result = RF.header("杜邦分析报告")
        periods = self._build_periods_data(5)

        if not periods:
            return result + "❌ 数据不足，无法进行杜邦分析\n"

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n"
            if basic_info.get("industry"):
                result += f"  行业: {basic_info['industry']}\n"
            result += "\n"

        # ① 杜邦三因素分解表
        result += RF.section("杜邦三因素分解（近5年）")
        result += f"{cjk_ljust('报告期', 12)}{cjk_rjust('ROE(%)', 10)}{cjk_rjust('净利率(%)', 10)}{cjk_rjust('资产周转(次)', 14)}{cjk_rjust('权益乘数', 10)}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        dupont_data = []
        for p in periods:
            dp = DAC.dupont_3factor(
                p.get("net_profit"), p.get("revenue"),
                p.get("total_assets"), p.get("equity"),
            )
            dp["end_date"] = p["end_date"]
            dupont_data.append(dp)

            roe_s = FC.format_percentage(dp['roe'])
            nm_s = FC.format_percentage(dp['net_margin'])
            at_s = FC.format_value(dp['asset_turnover'], 2)
            em_s = FC.format_value(dp['equity_multiplier'], 2)
            result += f"{cjk_ljust(p['end_date'], 12)}{cjk_rjust(roe_s, 10)}{cjk_rjust(nm_s, 10)}{cjk_rjust(at_s, 14)}{cjk_rjust(em_s, 10)}\n"

        # ② ROE 驱动因素诊断
        if dupont_data and dupont_data[0]["diagnosis"]:
            result += f"\n{RF.section('ROE 驱动因素诊断')}"
            result += f"  📌 {dupont_data[0]['diagnosis']}\n\n"
            # 各因子详细解读
            dp0 = dupont_data[0]
            if dp0["net_margin"] is not None:
                nm = dp0["net_margin"]
                if nm > 20:
                    result += f"  ✓ 净利率 {nm:.1f}%，盈利空间大，产品/服务定价能力强\n"
                elif nm > 10:
                    result += f"  ○ 净利率 {nm:.1f}%，盈利能力正常\n"
                elif nm > 0:
                    result += f"  ⚠ 净利率 {nm:.1f}%，盈利空间有限，需关注成本控制\n"
                else:
                    result += f"  ✗ 净利率 {nm:.1f}%，处于亏损状态\n"
            if dp0["asset_turnover"] is not None:
                at = dp0["asset_turnover"]
                if at > 1.0:
                    result += f"  ✓ 资产周转率 {at:.2f}次，资产利用效率高\n"
                elif at > 0.5:
                    result += f"  ○ 资产周转率 {at:.2f}次，资产利用效率一般\n"
                else:
                    result += f"  ⚠ 资产周转率 {at:.2f}次，资产较重，周转偏慢\n"
            if dp0["equity_multiplier"] is not None:
                em = dp0["equity_multiplier"]
                if em > 3:
                    result += f"  ⚠ 权益乘数 {em:.2f}，财务杠杆较高，需关注偿债风险\n"
                elif em > 2:
                    result += f"  ○ 权益乘数 {em:.2f}，杠杆适中\n"
                else:
                    result += f"  ✓ 权益乘数 {em:.2f}，财务结构保守\n"

        # ③ 多年趋势分析
        roes = [d["roe"] for d in dupont_data if d["roe"] is not None]
        margins = [d["net_margin"] for d in dupont_data if d["net_margin"] is not None]
        turnovers = [d["asset_turnover"] for d in dupont_data if d["asset_turnover"] is not None]
        multipliers = [d["equity_multiplier"] for d in dupont_data if d["equity_multiplier"] is not None]

        if len(roes) >= 2:
            result += f"\n{RF.section('ROE 趋势分析')}"
            if roes[0] > roes[-1] * 1.1:
                result += f"  📈 ROE 从 {roes[-1]:.1f}% 上升至 {roes[0]:.1f}%，盈利能力改善\n"
            elif roes[0] < roes[-1] * 0.9:
                result += f"  📉 ROE 从 {roes[-1]:.1f}% 下降至 {roes[0]:.1f}%，盈利能力减弱\n"
            else:
                result += f"  ↔️ ROE 在 {roes[0]:.1f}% 附近波动，相对稳定\n"

            # 各因子贡献分析
            result += "\n  各因子变化:\n"
            if len(margins) >= 2:
                delta = margins[0] - margins[-1]
                icon = "📈" if delta > 0 else "📉" if delta < 0 else "↔️"
                result += f"    {icon} 净利率: {margins[-1]:.1f}% → {margins[0]:.1f}% ({delta:+.1f}pp)\n"
            if len(turnovers) >= 2:
                delta = turnovers[0] - turnovers[-1]
                icon = "📈" if delta > 0 else "📉" if delta < 0 else "↔️"
                result += f"    {icon} 资产周转率: {turnovers[-1]:.2f} → {turnovers[0]:.2f} ({delta:+.2f})\n"
            if len(multipliers) >= 2:
                delta = multipliers[0] - multipliers[-1]
                icon = "📈" if delta > 0 else "📉" if delta < 0 else "↔️"
                result += f"    {icon} 权益乘数: {multipliers[-1]:.2f} → {multipliers[0]:.2f} ({delta:+.2f})\n"

            # 因子贡献度估算
            if len(roes) >= 2:
                result += f"\n{RF.section('ROE 变动归因')}"
                roe_change = roes[0] - roes[-1]
                result += f"  ROE 总变动: {roe_change:+.2f}pp\n\n"
                # 使用连环替代法估算各因子贡献
                if len(margins) >= 2 and len(turnovers) >= 2 and len(multipliers) >= 2:
                    nm_old, nm_new = margins[-1], margins[0]
                    at_old, at_new = turnovers[-1], turnovers[0]
                    em_old, em_new = multipliers[-1], multipliers[0]
                    # 净利率贡献 = (新净利率 - 旧净利率) × 旧周转 × 旧杠杆
                    nm_contrib = (nm_new - nm_old) * at_old * em_old / 100 if all(v is not None for v in [nm_new, nm_old, at_old, em_old]) else None
                    # 周转贡献 = 新净利率 × (新周转 - 旧周转) × 旧杠杆
                    at_contrib = nm_new * (at_new - at_old) * em_old / 100 if all(v is not None for v in [nm_new, at_new, at_old, em_old]) else None
                    # 杠杆贡献 = 新净利率 × 新周转 × (新杠杆 - 旧杠杆)
                    em_contrib = nm_new * at_new * (em_new - em_old) / 100 if all(v is not None for v in [nm_new, at_new, em_new, em_old]) else None
                    if nm_contrib is not None:
                        result += f"  净利率贡献:  {nm_contrib:+.2f}pp  (占比 {abs(nm_contrib)/max(abs(roe_change),0.01)*100:.0f}%)\n"
                    if at_contrib is not None:
                        result += f"  周转率贡献:  {at_contrib:+.2f}pp  (占比 {abs(at_contrib)/max(abs(roe_change),0.01)*100:.0f}%)\n"
                    if em_contrib is not None:
                        result += f"  杠杆贡献:    {em_contrib:+.2f}pp  (占比 {abs(em_contrib)/max(abs(roe_change),0.01)*100:.0f}%)\n"

        # ④ 投资启示
        result += f"\n{RF.section('投资启示')}"
        if roes and roes[0] is not None:
            if roes[0] > 20 and len(dupont_data) > 0 and dupont_data[0].get("diagnosis", "").startswith("高利润率"):
                result += "  ✓ 高 ROE + 利润驱动，可能具有品牌/定价优势（宽护城河候选）\n"
            elif roes[0] > 15 and len(dupont_data) > 0 and "高资产周转" in dupont_data[0].get("diagnosis", ""):
                result += "  ✓ 高 ROE + 周转驱动，运营效率优秀（零售/快消特征）\n"
            elif roes[0] > 0 and len(dupont_data) > 0 and "高财务杠杆" in dupont_data[0].get("diagnosis", ""):
                result += "  ⚠ ROE 主要靠杠杆驱动，需关注负债风险\n"
            elif roes[0] < 5:
                result += "  ✗ ROE 偏低，资本回报不足，需关注盈利改善空间\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 2. Altman Z-score
    # ========================================================================

    def analyze_zscore(self) -> str:
        """Altman Z-score 破产预测报告"""
        result = RF.header("Altman Z-score 破产预测报告")
        periods = self._build_periods_data(5)

        if not periods:
            return result + "❌ 数据不足\n"

        basic_info = self._get_basic_info()
        industry = basic_info.get("industry", "")
        is_manufacturer = industry not in ["银行", "金融", "证券", "保险", "房地产"]

        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n"
            result += f"  行业: {industry}  |  模型: {'制造业' if is_manufacturer else '非制造业'}版\n\n"

        # 多年 Z-score 趋势
        result += RF.section("Z-score 趋势（近5年）")
        result += f"{'报告期':<12}{'Z-score':>10}{'区域':>10}{'X1':>10}{'X2':>10}{'X3':>10}{'X4':>10}{'X5':>10}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for p in periods:
            market_cap = basic_info.get("market_cap")
            if market_cap:
                market_cap = market_cap * 10000  # 万元→元

            z = DAC.altman_zscore(
                p.get("total_assets"),
                (p.get("current_assets", 0) or 0) - (p.get("current_liab", 0) or 0),
                p.get("retained_earnings"),
                p.get("ebit"),
                market_cap,
                p.get("total_liab"),
                p.get("revenue"),
                is_manufacturer=is_manufacturer,
            )

            comp = z.get("components", {})
            zone_icon = {"safe": "🟢", "grey": "🟡", "distress": "🔴"}.get(z["zone"], "⚪")

            result += (
                f"{p['end_date']:<12}"
                f"{FC.format_value(z['z_score'], 2):>10}"
                f"{zone_icon}{z['zone_cn']:>8}"
                f"{FC.format_value(comp.get('X1_营运资本/总资产'), 3):>10}"
                f"{FC.format_value(comp.get('X2_留存收益/总资产'), 3):>10}"
                f"{FC.format_value(comp.get('X3_EBIT/总资产'), 3):>10}"
                f"{FC.format_value(comp.get('X4_权益市值/总负债'), 2):>10}"
                f"{FC.format_value(comp.get('X5_营收/总资产'), 2):>10}\n"
            )

        # 最新期详细诊断
        p0 = periods[0]
        market_cap = basic_info.get("market_cap")
        if market_cap:
            market_cap *= 10000
        z_latest = DAC.altman_zscore(
            p0.get("total_assets"),
            (p0.get("current_assets", 0) or 0) - (p0.get("current_liab", 0) or 0),
            p0.get("retained_earnings"),
            p0.get("ebit"),
            market_cap,
            p0.get("total_liab"),
            p0.get("revenue"),
            is_manufacturer=is_manufacturer,
        )

        result += f"\n{RF.section('最新期诊断')}"
        for d in z_latest.get("details", []):
            result += f"  {d}\n"

        # 各因子解读
        comp = z_latest.get("components", {})
        result += f"\n{RF.section('因子解读')}"
        x1 = comp.get("X1_营运资本/总资产")
        if x1 is not None:
            if x1 > 0.1:
                result += f"  X1(营运资本/总资产) = {x1:.3f}，流动性充裕\n"
            elif x1 > 0:
                result += f"  X1(营运资本/总资产) = {x1:.3f}，流动性一般\n"
            else:
                result += f"  X1(营运资本/总资产) = {x1:.3f}，⚠ 流动性不足\n"

        x3 = comp.get("X3_EBIT/总资产")
        if x3 is not None:
            if x3 > 0.1:
                result += f"  X3(EBIT/总资产) = {x3:.3f}，资产盈利能力强\n"
            elif x3 > 0.05:
                result += f"  X3(EBIT/总资产) = {x3:.3f}，资产盈利能力正常\n"
            else:
                result += f"  X3(EBIT/总资产) = {x3:.3f}，⚠ 资产盈利能力较弱\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 3. Piotroski F-score
    # ========================================================================

    def analyze_fscore(self) -> str:
        """Piotroski F-score 财务健康评分报告"""
        result = RF.header("Piotroski F-score 财务健康评分报告")
        periods = self._build_periods_data(5)

        if len(periods) < 2:
            return result + "❌ 需要至少2年数据\n"

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # 多年 F-score 趋势
        result += RF.section("F-score 趋势（近5年）")
        result += f"{'报告期':<12}{'总分':>8}{'盈利(4)':>8}{'杠杆(3)':>8}{'效率(2)':>8}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        fscore_results = []
        for i in range(len(periods) - 1):
            cur = periods[i]
            prev = periods[i + 1]
            fs = DAC.piotroski_fscore(cur, prev)
            fs["end_date"] = cur["end_date"]
            fscore_results.append(fs)

            score_icon = "🟢" if fs["score"] >= 7 else "🟡" if fs["score"] >= 5 else "🔴"
            result += (
                f"{cur['end_date']:<12}"
                f"{score_icon}{fs['score']:>6}"
                f"{fs['profit_score']:>8}"
                f"{fs['leverage_score']:>8}"
                f"{fs['efficiency_score']:>8}\n"
            )

        # 最新期详细诊断
        if fscore_results:
            latest = fscore_results[0]
            result += f"\n{RF.section('最新期详细诊断')}"
            result += f"  综合评分: {latest['score']}/9  — {latest['diagnosis']}\n\n"
            for d in latest.get("details", []):
                result += f"  {d}\n"

            # 趋势判断
            scores = [f["score"] for f in fscore_results]
            if len(scores) >= 2:
                result += f"\n{RF.section('趋势判断')}"
                if scores[0] > scores[-1]:
                    result += f"  📈 F-score 从 {scores[-1]} 上升至 {scores[0]}，财务状况改善\n"
                elif scores[0] < scores[-1]:
                    result += f"  📉 F-score 从 {scores[-1]} 下降至 {scores[0]}，财务状况恶化\n"
                else:
                    result += f"  ↔️ F-score 维持在 {scores[0]}，财务状况稳定\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 4. Beneish M-score
    # ========================================================================

    def analyze_mscore(self) -> str:
        """Beneish M-score 盈余管理检测报告"""
        result = RF.header("Beneish M-score 盈余管理检测报告")
        periods = self._build_periods_data(5)

        if len(periods) < 2:
            return result + "❌ 需要至少2年数据\n"

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # M-score 计算
        result += RF.section("M-score 检测结果")

        mscore_results = []
        for i in range(len(periods) - 1):
            cur = periods[i]
            prev = periods[i + 1]
            ms = DAC.beneish_mscore(cur, prev)
            ms["end_date"] = cur["end_date"]
            mscore_results.append(ms)

        if mscore_results:
            latest = mscore_results[0]
            m_val = latest.get('m_score')
            result += f"  M-score: {m_val:.2f}\n" if m_val is not None else "  M-score: 数据不足\n"
            if latest["manipulator"]:
                result += f"  🔴 结论: M > -1.78，存在盈余管理嫌疑\n\n"
            else:
                result += f"  🟢 结论: M ≤ -1.78，盈余管理风险较低\n\n"

            # 各指标解读
            result += RF.section("各指标分解")
            comps = latest.get("components", {})
            for key, val in comps.items():
                label = key.split("_")[1] if "_" in key else key
                result += f"  {label}: {val:.4f}\n"

            # 详细诊断
            result += f"\n{RF.section('诊断详情')}"
            for d in latest.get("details", []):
                result += f"  {d}\n"

            # M-score 趋势
            if len(mscore_results) >= 2:
                result += f"\n{RF.section('M-score 趋势')}"
                result += f"{'报告期':<12}{'M-score':>12}{'判定':>12}\n"
                result += f"{SEPARATOR_LIGHT}\n"
                for ms in mscore_results:
                    icon = "🔴" if ms["manipulator"] else "🟢"
                    label = "有嫌疑" if ms["manipulator"] else "正常"
                    result += f"{ms['end_date']:<12}{FC.format_value(ms['m_score'], 2):>12}{icon}{label:>10}\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 5. 自由现金流分析 & DCF 估值
    # ========================================================================

    def analyze_free_cashflow(self) -> str:
        """自由现金流分析 & DCF 估值报告"""
        result = RF.header("自由现金流分析报告")
        periods = self._build_periods_data(5)

        if not periods:
            return result + "❌ 数据不足\n"

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # 自由现金流趋势
        fcf_data = []
        for p in periods:
            fcf_data.append({
                "end_date": p["end_date"],
                "op_cashflow": p.get("op_cashflow"),
                "capex": p.get("capex"),
                "revenue": p.get("revenue"),
            })

        fcf_trend = DAC.fcf_trend(fcf_data)

        result += RF.section("自由现金流趋势（近5年）")
        result += f"{'报告期':<12}{'经营现金流':>14}{'资本支出':>14}{'自由现金流':>14}{'FCF/营收':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for p in fcf_trend["periods"]:
            op_str = FC.format_value(p["op_cashflow"] / 1e8, 2, "亿") if p["op_cashflow"] else "N/A"
            capex_str = FC.format_value(p["capex"] / 1e8, 2, "亿") if p["capex"] else "N/A"
            fcf_str = FC.format_value(p["fcf"] / 1e8, 2, "亿") if p["fcf"] else "N/A"
            margin_str = FC.format_percentage(p["fcf_margin"])

            result += f"{p['end_date']:<12}{op_str:>14}{capex_str:>14}{fcf_str:>14}{margin_str:>12}\n"

        result += f"\n  趋势判断: {fcf_trend['trend']}\n"

        # 简化 DCF 估值
        result += f"\n{RF.section('简化 DCF 估值')}"
        fcf_latest = fcf_trend["periods"][0]["fcf"] if fcf_trend["periods"] else None
        shares = basic_info.get("shares")

        if fcf_latest and fcf_latest > 0 and shares and shares > 0:
            # 多情景估值
            scenarios = DCF_SCENARIOS
            result += f"  最新自由现金流: {fcf_latest / 1e8:.2f} 亿元\n"
            result += f"  总股本: {shares / 1e8:.2f} 亿股\n\n"
            result += f"  {'情景':<10}{f'{DCF_GROWTH_YEARS}年增长率':>14}{'永续增长率':>12}{'折现率':>10}{'每股价值':>14}\n"
            result += f"  {SEPARATOR_LIGHT}\n"

            for name, g1, g2, r in scenarios:
                dcf = DAC.simple_dcf(fcf_latest, g1, g2, r, shares)
                val = dcf.get("intrinsic_value_per_share")
                val_str = f"{val:.2f}" if val else "N/A"
                result += f"  {name:<10}{g1:>13}%{g2:>11}%{r:>9}%{val_str:>14}\n"

            # 与当前价格对比
            daily = self.data.get("daily")
            if daily is not None and not daily.empty:
                current_price = daily["close"].iloc[0]
                result += f"\n  当前股价: {current_price:.2f}\n"
                # 使用中性情景作参考
                mid_name, mid_g1, mid_g2, mid_r = DCF_SCENARIOS[1]
                dcf_mid = DAC.simple_dcf(fcf_latest, mid_g1, mid_g2, mid_r, shares)
                mid_val = dcf_mid.get("intrinsic_value_per_share")
                if mid_val:
                    margin = (mid_val - current_price) / current_price * 100
                    if margin > 30:
                        result += f"  📈 中性估值 {mid_val:.2f}，高于当前价 {margin:.1f}%，可能被低估\n"
                    elif margin > 0:
                        result += f"  ○ 中性估值 {mid_val:.2f}，略高于当前价 {margin:.1f}%\n"
                    elif margin > -30:
                        result += f"  ○ 中性估值 {mid_val:.2f}，略低于当前价 {abs(margin):.1f}%\n"
                    else:
                        result += f"  📉 中性估值 {mid_val:.2f}，低于当前价 {abs(margin):.1f}%，可能被高估\n"
        elif fcf_latest and fcf_latest <= 0:
            result += "  ⚠ 自由现金流为负，DCF 模型不适用\n"
            result += "  建议：关注公司何时能转正，或使用其他估值方法\n"
        else:
            result += "  ⚠ 数据不足，无法进行 DCF 估值\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 6. 现金流象限分析
    # ========================================================================

    def analyze_cashflow_quadrant(self) -> str:
        """现金流象限分析报告"""
        result = RF.header("现金流象限分析报告")
        periods = self._build_periods_data(5)

        if not periods:
            return result + "❌ 数据不足\n"

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # 构建象限数据
        quadrant_data = []
        for p in periods:
            quadrant_data.append({
                "end_date": p["end_date"],
                "op_cf": p.get("op_cashflow"),
                "inv_cf": p.get("inv_cf"),
                "fin_cf": p.get("fin_cf"),
            })

        trend = DAC.cashflow_quadrant_trend(quadrant_data)

        # 多年象限变迁
        result += RF.section("现金流象限变迁（近5年）")
        result += f"{'报告期':<12}{'经营CF':>14}{'投资CF':>14}{'筹资CF':>14}{'象限类型':>16}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for p in trend["periods"]:
            op_str = FC.format_value(p["op_cf"] / 1e8, 2, "亿") if p["op_cf"] else "N/A"
            inv_str = FC.format_value(p["inv_cf"] / 1e8, 2, "亿") if p["inv_cf"] else "N/A"
            fin_str = FC.format_value(p["fin_cf"] / 1e8, 2, "亿") if p["fin_cf"] else "N/A"

            result += (
                f"{p['end_date']:<12}{op_str:>14}{inv_str:>14}{fin_str:>14}"
                f"{p['icon']}{p['type']:>14}\n"
            )

        # 趋势总结
        result += f"\n{RF.section('象限变迁趋势')}"
        result += f"  {trend['trend']}\n"

        # 最新期详细解读
        if trend["periods"]:
            latest = trend["periods"][0]
            result += f"\n{RF.section('最新期解读')}"
            result += f"  {latest['icon']} 当前类型: {latest['type']}\n"
            result += f"  {latest['description']}\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 7. 经济护城河评估
    # ========================================================================

    def analyze_moat(self) -> str:
        """经济护城河评估报告"""
        result = RF.header("经济护城河评估报告")
        periods = self._build_periods_data(5)

        if len(periods) < 2:
            return result + "❌ 需要至少2年数据\n"

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        # 护城河评估
        moat_data = []
        for p in periods:
            moat_data.append({
                "end_date": p["end_date"],
                "net_profit": p.get("net_profit"),
                "revenue": p.get("revenue"),
                "op_cost": p.get("op_cost"),
                "total_assets": p.get("total_assets"),
                "equity": p.get("equity"),
            })

        moat = DAC.economic_moat(moat_data)

        # 综合评分
        score = moat["moat_score"]
        moat_icon = {"宽护城河": "🏰", "窄护城河": "🏠", "有限竞争优势": "🏗️", "无明显护城河": "⚠️"}.get(moat["moat_type"], "❓")

        result += RF.section("护城河综合评估")
        result += f"  {moat_icon} 护城河评级: {moat['moat_type']}  (综合得分: {score}/100)\n\n"

        # 评分标准
        result += RF.section("评分标准 (每项 0-25 分，总分 100)")
        result += "  毛利率稳定性: 均值>40%且波动<15%→25分 | >30%且波动<20%→20分 | >20%→12分 | 其他→5分\n"
        result += "  ROE持续性:   连续4年>15%且均值>20%→25分 | 3年>15%→18分 | 1年>15%→10分 | 无→3分\n"
        result += "  营收增长:    CAGR>15%且全部正增长→25分 | >8%且70%正增长→18分 | >0%→10分 | 负增长→3分\n"
        result += "  净利率趋势:  均值>10%且上升→25分 | >8%→18分 | >3%→10分 | 其他→3分\n\n"

        # 各维度得分
        result += RF.section("各维度得分")
        for factor, f_score in moat.get("factors", {}).items():
            bar = "█" * (int(f_score) // 5) + "░" * ((25 - int(f_score)) // 5)
            result += f"  {factor:<16} {bar} {f_score}/25\n"

        # 详细诊断
        result += f"\n{RF.section('详细分析')}"
        for d in moat.get("details", []):
            result += f"  {d}\n"

        # 护城河解读
        result += f"\n{RF.section('投资启示')}"
        if score >= 80:
            result += "  公司具有宽广的经济护城河，长期竞争优势明显。\n"
            result += "  适合长期持有，关注估值是否合理。\n"
        elif score >= 60:
            result += "  公司具有一定护城河，但需关注竞争态势变化。\n"
            result += "  建议定期跟踪毛利率和 ROE 趋势。\n"
        elif score >= 40:
            result += "  公司竞争优势有限，面临一定竞争压力。\n"
            result += "  建议关注行业格局变化和公司应对策略。\n"
        else:
            result += "  公司缺乏明显护城河，竞争激烈。\n"
            result += "  建议谨慎投资，重点关注盈利可持续性。\n"

        result += RF.footer()
        return result

    # ========================================================================
    # 8. 综合深度分析报告（一键生成）
    # ========================================================================

    def generate_comprehensive_report(self) -> str:
        """生成综合深度分析报告"""
        result = RF.header("综合深度财务分析报告")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n"
            result += f"  行业: {basic_info.get('industry', 'N/A')}\n"
            if basic_info.get("pe"):
                result += f"  PE: {basic_info['pe']:.2f}  |  PB: {basic_info.get('pb', 'N/A')}\n"
            result += "\n"

        # 按顺序执行各分析
        sections = [
            ("一、杜邦分析", self.analyze_dupont),
            ("二、Altman Z-score", self.analyze_zscore),
            ("三、Piotroski F-score", self.analyze_fscore),
            ("四、Beneish M-score", self.analyze_mscore),
            ("五、自由现金流 & DCF", self.analyze_free_cashflow),
            ("六、现金流象限", self.analyze_cashflow_quadrant),
            ("七、经济护城河", self.analyze_moat),
        ]

        for title, func in sections:
            try:
                section_result = func()
                # 去掉子报告的 header/footer，嵌入到总报告中
                result += f"\n{'=' * 60}\n"
                result += section_result
            except Exception as e:
                logger.error(f"{title} 分析失败: {e}")
                result += f"\n{title}: ❌ 分析失败 ({str(e)})\n"

        # 总结
        result += f"\n{'=' * 60}\n"
        result += RF.section("综合评价与建议")
        result += "  ⚠️ 以上分析基于公开财务数据，仅供参考，不构成投资建议。\n"
        result += "  建议结合行业前景、管理层质量、估值水平等因素综合判断。\n"

        result += RF.footer()
        return result
