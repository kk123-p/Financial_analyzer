"""
现金流量表分析器 — 基于《大数据财务分析框架》第五章
涵盖：经营活动现金流 / 投资活动现金流 / 筹资活动现金流 / 生命周期 / 现金流指标
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import SEPARATOR_LIGHT
from ..logging_config import get_logger

logger = get_logger(__name__)


class CashFlowAnalyzer(BaseAnalyzer):
    """现金流量表综合分析器"""

    def analyze(self) -> str:
        result = RF.header("现金流量表综合分析报告")
        try:
            cashflow, _ = self._fetch_data("cashflow")
        except Exception:
            cashflow = self.data.get("cashflow")
        if cashflow is None or cashflow.empty:
            return result + "\n❌ 未获取到现金流量表数据，无法进行分析"

        result += self._analyze_operating_cf(cashflow)
        result += self._analyze_investing_cf(cashflow)
        result += self._analyze_financing_cf(cashflow)
        result += self._analyze_cashflow_summary(cashflow)
        result += self._analyze_life_cycle(cashflow)
        result += self._analyze_cf_indicators(cashflow)
        result += RF.footer()
        return result

    # ========================================================================
    # 2. 经营活动现金流质量分析（造血功能）
    # ========================================================================

    def _analyze_operating_cf(self, cashflow) -> str:
        result = RF.section("一、经营活动现金流质量（造血功能）")
        try:
            annual = self._get_annual(cashflow)
            income = self.data.get("income")

            result += RF.subsection("1. 充足性分析")
            result += f"\n{'报告期':<12}{'经营CF':>14}{'营收':>14}{'OCF/营收':>12}\n{SEPARATOR_LIGHT}\n"

            ocf_vals = []
            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                ocf = self._val(row, ["n_cashflow_act", "经营活动现金流量净额"])
                ocf_vals.append(ocf)

                rev = None
                if income is not None and not income.empty:
                    inc_annual = self._get_annual(income)
                    inc_row = inc_annual[inc_annual["end_date"] == ed] if "end_date" in inc_annual.columns else None
                    if inc_row is not None and not inc_row.empty:
                        rev = self._val(inc_row.iloc[0], ["total_revenue", "revenue"])
                    elif i < len(inc_annual):
                        rev = self._val(inc_annual.iloc[i], ["total_revenue", "revenue"])

                ratio = (ocf / rev) if ocf and rev and rev > 0 else None
                result += (f"{ed:<12}{FC.format_value(ocf / 1e8, 2, '亿') if ocf else 'N/A':>14}"
                           f"{FC.format_value(rev / 1e8, 2, '亿') if rev else 'N/A':>14}"
                           f"{FC.format_value(ratio, 2):>12}\n")

            if ocf_vals and ocf_vals[0]:
                latest_ocf = ocf_vals[0]
                if latest_ocf > 0:
                    all_pos = all(v and v > 0 for v in ocf_vals[:min(3, len(ocf_vals))])
                    if all_pos and len(ocf_vals) >= 3:
                        result += "  ✓ 经营活动现金流持续为正，造血功能稳健\n"
                    else:
                        result += "  ○ 经营现金流为正，但持续性需关注\n"
                else:
                    result += "  ⚠ 经营现金流为负，造血功能不足\n"

            # OCF/净利润
            result += RF.subsection("2. 利润含金量")
            if income is not None and not income.empty:
                inc_annual = self._get_annual(income)
                result += f"\n{'报告期':<12}{'经营CF':>14}{'净利润':>14}{'OCF/NP':>10}\n{SEPARATOR_LIGHT}\n"
                for i in range(min(5, len(annual))):
                    cf_row = annual.iloc[i]
                    ed = str(cf_row.get("end_date", ""))
                    ocf = self._val(cf_row, ["n_cashflow_act", "经营活动现金流量净额"])
                    np_v = None
                    inc_row = inc_annual[inc_annual["end_date"] == ed] if "end_date" in inc_annual.columns else None
                    if inc_row is not None and not inc_row.empty:
                        np_v = self._val(inc_row.iloc[0], ["net_profit", "净利润"])
                    elif i < len(inc_annual):
                        np_v = self._val(inc_annual.iloc[i], ["net_profit", "净利润"])
                    ratio = (ocf / np_v) if ocf and np_v and np_v != 0 else None
                    result += (f"{ed:<12}{FC.format_value(ocf / 1e8, 2, '亿') if ocf else 'N/A':>14}"
                               f"{FC.format_value(np_v / 1e8, 2, '亿') if np_v else 'N/A':>14}"
                               f"{FC.format_value(ratio, 2):>10}\n")

                latest = annual.iloc[0]
                latest_ocf = self._val(latest, ["n_cashflow_act", "经营活动现金流量净额"])
                latest_np = None
                i0 = inc_annual[inc_annual["end_date"] == str(latest.get("end_date", ""))] if "end_date" in inc_annual.columns else None
                if i0 is not None and not i0.empty:
                    latest_np = self._val(i0.iloc[0], ["net_profit", "净利润"])
                elif not inc_annual.empty:
                    latest_np = self._val(inc_annual.iloc[0], ["net_profit", "净利润"])

                if latest_ocf and latest_np and latest_np > 0:
                    ratio = latest_ocf / latest_np
                    if ratio > 1.5:
                        result += f"\n  ✓ OCF/NP={ratio:.2f}，利润现金保障充足\n"
                    elif ratio > 0.8:
                        result += f"\n  ○ OCF/NP={ratio:.2f}，利润有较好的现金保障\n"
                    else:
                        result += f"\n  ⚠ OCF/NP={ratio:.2f}，利润现金保障不足\n"

            # 稳定性
            result += RF.subsection("3. 稳定性分析")
            if len(ocf_vals) >= 3 and all(v is not None for v in ocf_vals[:3]):
                import numpy as np
                vals = [abs(v) for v in ocf_vals[:3] if v]
                if vals:
                    cv = np.std(vals) / np.mean(vals) if np.mean(vals) > 0 else 999
                    if cv < 0.3:
                        result += f"  变异系数: {cv:.2f} → 经营现金流高度稳定\n"
                    elif cv < 0.6:
                        result += f"  变异系数: {cv:.2f} → 经营现金流有一定波动\n"
                    else:
                        result += f"  变异系数: {cv:.2f} → 经营现金流波动较大，需关注\n"
            else:
                result += "  数据不足（需至少3期），无法评估稳定性\n"

        except Exception as e:
            logger.warning(f"经营现金流分析异常: {e}")
            result += f"\n  ⚠ 经营现金流分析异常: {e}\n"
        return result

    # ========================================================================
    # 3. 投资活动现金流质量分析（放血功能）
    # ========================================================================

    def _analyze_investing_cf(self, cashflow) -> str:
        result = RF.section("二、投资活动现金流质量")
        try:
            annual = self._get_annual(cashflow)
            income = self.data.get("income")
            balance = self.data.get("balance")

            result += RF.subsection("1. 投资现金流趋势")
            result += f"\n{'报告期':<12}{'投资CF':>14}{'CAPEX':>14}{'FCF':>14}\n{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                icf = self._val(row, ["n_cashflow_inv_act", "投资活动现金流量净额"])
                capex = self._val(row, ["c_pay_acq_const_fiamt", "c_pay_acq_const_fiolta"])
                ocf = self._val(row, ["n_cashflow_act", "经营活动现金流量净额"])
                fcf = (ocf - abs(capex)) if ocf and capex else (ocf if ocf else None)
                result += (f"{ed:<12}{FC.format_value(icf / 1e8, 2, '亿') if icf else 'N/A':>14}"
                           f"{FC.format_value(capex / 1e8, 2, '亿') if capex else 'N/A':>14}"
                           f"{FC.format_value(fcf / 1e8, 2, '亿') if fcf else 'N/A':>14}\n")

            # 投资模式判断
            icf_vals = [self._val(annual.iloc[i], ["n_cashflow_inv_act", "投资活动现金流量净额"])
                       for i in range(min(5, len(annual)))]
            icf_vals = [v for v in icf_vals if v is not None]
            if icf_vals:
                neg_count = sum(1 for v in icf_vals if v < 0)
                if neg_count >= len(icf_vals) * 0.8:
                    result += "\n  → 投资现金流持续为负：处于扩张阶段，大规模资本开支\n"
                elif all(v > 0 for v in icf_vals):
                    result += "\n  → 投资现金流持续为正：可能处于收缩/回收阶段\n"
                else:
                    result += "\n  → 投资现金流波动：可能存在资产购置与处置交替\n"

            # CAPEX强度
            result += RF.subsection("2. CAPEX 强度分析")
            latest = annual.iloc[0]
            capex_l = self._val(latest, ["c_pay_acq_const_fiamt", "c_pay_acq_const_fiolta"])
            ocf_l = self._val(latest, ["n_cashflow_act", "经营活动现金流量净额"])

            if ocf_l and capex_l and ocf_l > 0:
                capex_ratio = abs(capex_l) / ocf_l
                result += f"  CAPEX/经营CF: {capex_ratio:.2f}\n"
                if capex_ratio > 1:
                    result += "  ⚠ CAPEX超过经营现金流，依赖外部融资维持投资\n"
                elif capex_ratio > 0.5:
                    result += "  → 较大比例的经营现金流用于资本开支\n"
                else:
                    result += "  ✓ CAPEX在经营现金流可覆盖范围内\n"

            if income is not None and not income.empty:
                inc_annual = self._get_annual(income)
                rev_l = self._val(inc_annual.iloc[0], ["total_revenue", "revenue"]) if not inc_annual.empty else None
                if rev_l and capex_l and rev_l > 0:
                    result += f"  CAPEX/营收: {abs(capex_l) / rev_l * 100:.1f}%\n"

            # FCF趋势
            if ocf_l and capex_l:
                fcf_l = ocf_l - abs(capex_l)
                result += f"\n  自由现金流(最新): {fcf_l / 1e8:.2f}亿\n"
                if fcf_l > 0:
                    result += "  ✓ FCF > 0，有剩余现金可用于分红或再投资\n"
                else:
                    result += "  ⚠ FCF < 0，经营现金流不足以覆盖资本开支\n"

        except Exception as e:
            logger.warning(f"投资现金流分析异常: {e}")
            result += f"\n  ⚠ 投资现金流分析异常: {e}\n"
        return result

    # ========================================================================
    # 4. 筹资活动现金流质量分析
    # ========================================================================

    def _analyze_financing_cf(self, cashflow) -> str:
        result = RF.section("三、筹资活动现金流质量")
        try:
            annual = self._get_annual(cashflow)

            result += f"\n{'报告期':<12}{'筹资CF':>14}{'借款净额':>14}\n{SEPARATOR_LIGHT}\n"
            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                fin_cf = self._val(row, ["n_cash_finance_act", "n_cash_flows_fnc_act", "筹资活动现金流量净额"])
                result += f"{ed:<12}{FC.format_value(fin_cf / 1e8, 2, '亿') if fin_cf else 'N/A':>14}"

                # net borrowing estimate
                st_borrow = self._val(row, ["st_borrow_cash", "short_borrow_cash"])
                lt_borrow = self._val(row, ["lt_borrow_cash", "long_borrow_cash"])
                st_repay = self._val(row, ["st_repay_cash", "short_repay_cash"])
                lt_repay = self._val(row, ["lt_repay_cash", "long_repay_cash"])
                net_borrow = None
                if st_borrow or lt_borrow:
                    net_borrow = (st_borrow or 0) + (lt_borrow or 0) - (st_repay or 0) - (lt_repay or 0)
                result += f"{FC.format_value(net_borrow / 1e8, 2, '亿') if net_borrow else 'N/A':>14}\n"

            # 筹资模式判断
            fin_vals = [self._val(annual.iloc[i], ["n_cash_finance_act", "n_cash_flows_fnc_act", "筹资活动现金流量净额"])
                       for i in range(min(5, len(annual)))]
            fin_vals = [v for v in fin_vals if v is not None]

            if fin_vals:
                pos_count = sum(1 for v in fin_vals if v > 0)
                if pos_count >= len(fin_vals) * 0.8:
                    result += "\n  → 筹资现金流持续为正：公司持续对外融资\n"
                elif all(v < 0 for v in fin_vals):
                    result += "\n  → 筹资现金流持续为负：可能在偿还债务或分红回馈股东\n"

            # 融资恰当性
            ocf_l = self._val(annual.iloc[0], ["n_cashflow_act", "经营活动现金流量净额"])
            icf_l = self._val(annual.iloc[0], ["n_cashflow_inv_act", "投资活动现金流量净额"])
            fin_l = self._val(annual.iloc[0], ["n_cash_finance_act", "n_cash_flows_fnc_act", "筹资活动现金流量净额"])

            if ocf_l and icf_l:
                gap = ocf_l + icf_l
                if gap < 0 and fin_l and fin_l > 0:
                    result += f"\n  经营+投资现金流缺口: {abs(gap) / 1e8:.2f}亿 → 需外部融资补足\n"
                    if fin_l > abs(gap) * 1.5:
                        result += "  ⚠ 融资规模远超实际需求，可能存在过度融资\n"
                elif gap > 0 and fin_l and fin_l < 0:
                    result += f"\n  经营+投资现金盈余: {gap / 1e8:.2f}亿 → 用于偿还债务/分红\n"

        except Exception as e:
            logger.warning(f"筹资现金流分析异常: {e}")
            result += f"\n  ⚠ 筹资现金流分析异常: {e}\n"
        return result

    # ========================================================================
    # 5. 三大现金流汇总
    # ========================================================================

    def _analyze_cashflow_summary(self, cashflow) -> str:
        result = RF.section("四、三大现金流汇总")
        try:
            annual = self._get_annual(cashflow)

            result += f"\n{'报告期':<12}{'经营CF':>14}{'投资CF':>14}{'筹资CF':>14}{'净增减':>14}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                ocf = self._val(row, ["n_cashflow_act", "经营活动现金流量净额"])
                icf = self._val(row, ["n_cashflow_inv_act", "投资活动现金流量净额"])
                fin = self._val(row, ["n_cash_finance_act", "n_cash_flows_fnc_act", "筹资活动现金流量净额"])
                net_change = self._val(row, ["cash_equivalent_increase", "现金及现金等价物净增加额"])

                result += (f"{ed:<12}"
                           f"{FC.format_value(ocf / 1e8, 2, '亿') if ocf else 'N/A':>14}"
                           f"{FC.format_value(icf / 1e8, 2, '亿') if icf else 'N/A':>14}"
                           f"{FC.format_value(fin / 1e8, 2, '亿') if fin else 'N/A':>14}"
                           f"{FC.format_value(net_change / 1e8, 2, '亿') if net_change else 'N/A':>14}\n")

            # 三流模式
            latest = annual.iloc[0]
            ocf_l = self._val(latest, ["n_cashflow_act", "经营活动现金流量净额"])
            icf_l = self._val(latest, ["n_cashflow_inv_act", "投资活动现金流量净额"])
            fin_l = self._val(latest, ["n_cash_finance_act", "n_cash_flows_fnc_act", "筹资活动现金流量净额"])

            if ocf_l and icf_l and fin_l:
                signs = ("+" if ocf_l > 0 else "-",
                        "+" if icf_l > 0 else "-",
                        "+" if fin_l > 0 else "-")
                pattern_map = {
                    ("+", "-", "-"): "成熟期特征：主业造血→投资扩张→偿还债务",
                    ("+", "-", "+"): "成长期特征：主业造血+外部融资→大规模投资",
                    ("+", "+", "-"): "成熟后期特征：主业+投资回收→偿还债务",
                    ("+", "+", "+"): "资金充裕，三大活动均现金流入（关注资金效率）",
                    ("-", "-", "+"): "导入期/困境期：依赖外部融资维持经营和投资",
                    ("-", "+", "-"): "收缩期特征：主业亏损→变卖资产偿还债务",
                    ("-", "-", "-"): "危机特征：三流均为负，现金急剧消耗",
                }
                desc = pattern_map.get(signs, "特殊模式，需具体分析")
                result += f"\n  现金流模式: 经营{signs[0]} / 投资{signs[1]} / 筹资{signs[2]}\n"
                result += f"  → {desc}\n"

        except Exception as e:
            logger.warning(f"现金流汇总异常: {e}")
            result += f"\n  ⚠ 现金流汇总异常: {e}\n"
        return result

    # ========================================================================
    # 6. 生命周期分析（复用 Ch8 现金流画像）
    # ========================================================================

    def _analyze_life_cycle(self, cashflow) -> str:
        result = RF.section("五、现金流画像与生命周期")
        try:
            from ..pipeline.textbook.ch8_cashflow_portrait import (
                multi_year_portrait, stability_assessment,
                extract_cashflow_signs, classify_portrait,
            )

            portraits = multi_year_portrait(cashflow, years=5)
            if not portraits:
                return result + "\n  现金流画像数据不足\n"

            stability = stability_assessment(portraits)
            result += f"\n  数据跨度: {len(portraits)} 期 | 稳定性: {stability}\n"
            result += f"\n{'期间':<14s}{'经营CF':>14s}{'投资CF':>14s}{'筹资CF':>14s}{'画像':<20s}\n"
            result += f"  {'─' * 80}\n"

            for p in portraits:
                ocf_s = f"{p['ocf'] / 1e8:.2f}亿" if p.get("ocf") and abs(p["ocf"]) > 1e4 else f"{p.get('ocf', 0) or 0:.2f}"
                icf_s = f"{p['icf'] / 1e8:.2f}亿" if p.get("icf") and abs(p["icf"]) > 1e4 else f"{p.get('icf', 0) or 0:.2f}"
                fin_s = f"{p['fin_cf'] / 1e8:.2f}亿" if p.get("fin_cf") and abs(p["fin_cf"]) > 1e4 else f"{p.get('fin_cf', 0) or 0:.2f}"
                result += f"  {p['period']:<14s} {ocf_s:>14s} {icf_s:>14s} {fin_s:>14s} {p.get('type_cn', '?')}\n"

            signs = extract_cashflow_signs(cashflow)
            portrait = classify_portrait(signs.get("ocf"), signs.get("icf"), signs.get("fcf"))
            if portrait.get("type") != "unknown":
                result += f"\n  最新画像: {portrait['type_cn']} — {portrait['description']}\n"
                if portrait.get("danger"):
                    result += "  ⚠ 经营现金流为负，需警惕流动性风险\n"

        except ImportError:
            result += "\n  (现金流画像模块不可用)\n"
        except Exception as e:
            logger.warning(f"生命周期分析异常: {e}")
            result += f"\n  ⚠ 生命周期分析异常: {e}\n"
        return result

    # ========================================================================
    # 7. 现金流指标体系
    # ========================================================================

    def _analyze_cf_indicators(self, cashflow) -> str:
        result = RF.section("六、现金流量指标体系")
        try:
            annual = self._get_annual(cashflow)
            income = self.data.get("income")
            balance = self.data.get("balance")
            latest = annual.iloc[0]

            result += RF.subsection("1. 短期偿债能力指标")
            ocf_l = self._val(latest, ["n_cashflow_act", "经营活动现金流量净额"])
            cash_l = None
            if balance is not None and not balance.empty:
                bal_annual = self._get_annual(balance)
                if not bal_annual.empty:
                    cl = self._val(bal_annual.iloc[0], ["total_cur_liab", "total_current_liab"])
                    cash_l = self._val(bal_annual.iloc[0], ["money_cap"])

                    if cash_l and cl and cl > 0:
                        result += f"  现金比率: {cash_l / cl:.2f}\n"
                    if ocf_l and cl and cl > 0:
                        result += f"  现金流量比率: {ocf_l / cl:.2f}\n"
                        if ocf_l / cl > 0.5:
                            result += "  ✓ 经营现金流对流动负债覆盖充足\n"
                        elif ocf_l / cl < 0.1:
                            result += "  ⚠ 经营现金流对流动负债覆盖不足\n"

            result += RF.subsection("2. 收益质量指标")
            if income is not None and not income.empty:
                inc_annual = self._get_annual(income)
                if not inc_annual.empty:
                    np_l = self._val(inc_annual.iloc[0], ["net_profit", "净利润"])
                    rev_l = self._val(inc_annual.iloc[0], ["total_revenue", "revenue"])
                    if ocf_l and np_l and np_l != 0:
                        result += f"  经营CF/净利润: {ocf_l / np_l:.2f}\n"
                    if ocf_l and rev_l and rev_l > 0:
                        result += f"  销售现金比率: {ocf_l / rev_l:.2f}\n"

            result += RF.subsection("3. 财务发展能力指标")
            if len(annual) >= 2:
                ocf_prev = self._val(annual.iloc[1], ["n_cashflow_act", "经营活动现金流量净额"])
                if ocf_l and ocf_prev and ocf_prev != 0:
                    ocf_growth = (ocf_l - ocf_prev) / abs(ocf_prev) * 100
                    result += f"  经营CF增长率: {ocf_growth:.1f}%\n"

            # 自由现金流
            capex_l = self._val(latest, ["c_pay_acq_const_fiamt", "c_pay_acq_const_fiolta"])
            if ocf_l and capex_l:
                fcf_l = ocf_l - abs(capex_l)
                result += f"  自由现金流(FCF): {fcf_l / 1e8:.2f}亿\n"
                if len(annual) >= 2:
                    capex_prev = self._val(annual.iloc[1], ["c_pay_acq_const_fiamt", "c_pay_acq_const_fiolta"])
                    if ocf_prev and capex_prev:
                        fcf_prev = ocf_prev - abs(capex_prev)
                        if fcf_prev and fcf_prev != 0:
                            fcf_growth = (fcf_l - fcf_prev) / abs(fcf_prev) * 100
                            result += f"  FCF增长率: {fcf_growth:.1f}%\n"

        except Exception as e:
            logger.warning(f"现金流指标分析异常: {e}")
            result += f"\n  ⚠ 现金流指标分析异常: {e}\n"
        return result

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _get_annual(self, df):
        if df is None or df.empty:
            return df
        if "end_date" in df.columns:
            annual = df[df["end_date"].astype(str).str.endswith("1231")]
            if annual.empty:
                annual = df.head(5)
            return annual.sort_values("end_date", ascending=False).reset_index(drop=True)
        return df.head(5)

    @staticmethod
    def _val(row, keys: list) -> float | None:
        if row is None:
            return None
        for k in keys:
            if k in row.index:
                v = row[k]
                try:
                    import pandas as pd
                    if pd.notna(v):
                        return float(v)
                except (ValueError, TypeError):
                    continue
        return None
