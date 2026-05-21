"""
资产负债表分析器 — 基于《大数据财务分析框架》第三章
涵盖：资产项目 / 负债项目 / 所有者权益 / 偿债能力 / 营运能力 / 资产与资本结构
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import SEPARATOR_LIGHT
from ..logging_config import get_logger

logger = get_logger(__name__)


class BalanceSheetAnalyzer(BaseAnalyzer):
    """资产负债表综合分析器"""

    def analyze(self) -> str:
        result = RF.header("资产负债表综合分析报告")
        try:
            balance, _ = self._fetch_data("balance")
        except Exception:
            balance = self.data.get("balance")
        if balance is None or balance.empty:
            return result + "\n❌ 未获取到资产负债表数据，无法进行分析"

        result += self._analyze_asset_items(balance)
        result += self._analyze_liability_items(balance)
        result += self._analyze_equity_structure(balance)
        result += self._analyze_solvency(balance)
        result += self._analyze_operational_efficiency(balance)
        result += self._analyze_asset_structure(balance)
        result += self._analyze_capital_structure(balance)
        result += RF.footer()
        return result

    # ========================================================================
    # 2. 资产项目分析
    # ========================================================================

    def _analyze_asset_items(self, balance) -> str:
        result = RF.section("一、资产项目分析")
        try:
            annual = self._get_annual(balance)
            income = self.data.get("income")
            if income is None or income.empty:
                income = None

            # --- 货币资金 ---
            result += "\n" + RF.subsection("1. 货币资金")
            if "money_cap" in annual.columns:
                result += self._trend_table(annual, "money_cap", "货币资金", unit="亿",
                                            divisor=1e8, with_ratio="total_assets")
                latest_mc = FC.safe_divide(
                    self._val(annual.iloc[0], ["money_cap"]),
                    self._val(annual.iloc[0], ["total_assets"]))
                if latest_mc is not None:
                    result += f"  货币资金/总资产: {latest_mc * 100:.1f}%\n"
                    if latest_mc > 0.25:
                        result += "  ✓ 资金充裕，流动性强\n"
                    elif latest_mc < 0.05:
                        result += "  ⚠ 货币资金占比偏低，需关注流动性风险\n"
                # 存贷双高检测
                st_loan = self._val(annual.iloc[0], ["short_term_loans", "st_borrow"])
                lt_loan = self._val(annual.iloc[0], ["long_term_loans", "lt_borrow"])
                money = self._val(annual.iloc[0], ["money_cap"])
                ta = self._val(annual.iloc[0], ["total_assets"])
                if money and ta and ta > 0:
                    if money / ta > 0.15 and ((st_loan or 0) + (lt_loan or 0)) / ta > 0.15:
                        result += "  ⚠ 「存贷双高」异常：货币资金和有息负债同时处于高位，需警惕\n"
            else:
                result += "  货币资金数据不可用\n"

            # --- 应收款项 ---
            result += "\n" + RF.subsection("2. 应收款项")
            if "accounts_receivable" in annual.columns:
                result += self._trend_table(annual, "accounts_receivable", "应收账款", unit="亿",
                                            divisor=1e8, with_ratio="total_assets")
                if income is not None and not income.empty:
                    inc_annual = self._get_annual(income)
                    if not inc_annual.empty:
                        ar = self._val(annual.iloc[0], ["accounts_receivable"])
                        rev = self._val(inc_annual.iloc[0], ["total_revenue", "revenue"])
                        if ar and rev and rev > 0:
                            ar_ratio = ar / rev * 100
                            result += f"  应收账款/营收: {ar_ratio:.1f}%\n"
                            if ar_ratio > 50:
                                result += "  ⚠ 应收账款占营收比重过高，回款压力大\n"
                            elif ar_ratio < 10:
                                result += "  ✓ 应收账款占比较低，回款良好\n"
                        # 应收vs营收增速对比
                        if len(annual) >= 2 and len(inc_annual) >= 2:
                            ar_prev = self._val(annual.iloc[1], ["accounts_receivable"])
                            rev_prev = self._val(inc_annual.iloc[1], ["total_revenue", "revenue"])
                            if ar and ar_prev and ar_prev > 0 and rev and rev_prev and rev_prev > 0:
                                ar_growth = (ar - ar_prev) / ar_prev * 100
                                rev_growth = (rev - rev_prev) / rev_prev * 100
                                result += f"  应收增速: {ar_growth:.1f}% | 营收增速: {rev_growth:.1f}%\n"
                                if ar_growth > rev_growth + 20:
                                    result += "  ⚠ 应收增速远超营收增速，可能虚增收入或信用政策过于宽松\n"
            else:
                result += "  应收账款数据不可用\n"

            # --- 存货 ---
            result += "\n" + RF.subsection("3. 存货")
            if "inventories" in annual.columns:
                result += self._trend_table(annual, "inventories", "存货", unit="亿",
                                            divisor=1e8, with_ratio="total_assets")
                if income is not None and not income.empty:
                    inc_annual = self._get_annual(income)
                    if not inc_annual.empty:
                        inv = self._val(annual.iloc[0], ["inventories"])
                        cost = self._val(inc_annual.iloc[0], ["oper_cost", "operate_cost"])
                        if inv and cost and cost > 0:
                            ratio = inv / cost * 100
                            result += f"  存货/营业成本: {ratio:.1f}%\n"
                            if ratio > 50:
                                result += "  ⚠ 存货相对营业成本偏高，可能存在滞销或跌价风险\n"
                        # 存货vs成本增速对比
                        if len(annual) >= 2 and len(inc_annual) >= 2:
                            inv_prev = self._val(annual.iloc[1], ["inventories"])
                            cost_prev = self._val(inc_annual.iloc[1], ["oper_cost", "operate_cost"])
                            if inv and inv_prev and inv_prev > 0 and cost and cost_prev and cost_prev > 0:
                                inv_growth = (inv - inv_prev) / inv_prev * 100
                                cost_growth = (cost - cost_prev) / cost_prev * 100
                                if inv_growth > cost_growth + 20:
                                    result += "  ⚠ 存货增速远超成本增速，库存积压风险\n"
            else:
                result += "  存货数据不可用\n"

            # --- 固定资产与无形资产 ---
            result += "\n" + RF.subsection("4. 固定资产与无形资产")
            fixed_col = None
            for c in ["fixed_assets", "fix_assets", "固定资产"]:
                if c in annual.columns:
                    fixed_col = c
                    break
            if fixed_col:
                result += self._trend_table(annual, fixed_col, "固定资产", unit="亿",
                                            divisor=1e8, with_ratio="total_assets")
                fa = self._val(annual.iloc[0], [fixed_col])
                ta_val = self._val(annual.iloc[0], ["total_assets"])
                if fa and ta_val and ta_val > 0:
                    ratio = fa / ta_val * 100
                    result += f"  固定资产/总资产: {ratio:.1f}%\n"
                    if ratio > 50:
                        result += "  → 重资产运营模式，折旧压力大，经营杠杆高\n"
                    elif ratio < 20:
                        result += "  → 轻资产运营模式，灵活性强\n"
            else:
                result += "  固定资产数据不可用\n"

            if "goodwill" in annual.columns and "商誉" in str(annual.columns):
                pass  # handled below
            gw_val = None
            for c in ["goodwill", "商誉"]:
                if c in annual.columns:
                    gw_val = self._val(annual.iloc[0], [c])
                    break
            if gw_val is not None and gw_val > 0:
                eq = self._val(annual.iloc[0], ["total_equity", "total_hldr_eqy_exc_min_int"])
                if eq and eq > 0:
                    result += f"\n  商誉: {gw_val / 1e8:.2f}亿 | 商誉/净资产: {gw_val / eq * 100:.1f}%\n"
                    if gw_val / eq > 0.3:
                        result += "  ⚠ 商誉占净资产比例过高，减值风险大\n"

        except Exception as e:
            logger.warning(f"资产项目分析异常: {e}")
            result += f"\n  ⚠ 资产项目分析异常: {e}\n"
        return result

    # ========================================================================
    # 3. 负债项目分析
    # ========================================================================

    def _analyze_liability_items(self, balance) -> str:
        result = RF.section("二、负债项目分析")
        try:
            annual = self._get_annual(balance)

            result += "\n" + RF.subsection("1. 流动负债")
            cols_cur = [c for c in ["total_cur_liab", "total_current_liab"] if c in annual.columns]
            if cols_cur:
                result += self._trend_table(annual, cols_cur[0], "流动负债", unit="亿", divisor=1e8)

            st_loan_col = None
            for c in ["short_term_loans", "st_borrow", "短期借款"]:
                if c in annual.columns:
                    st_loan_col = c
                    break
            if st_loan_col and cols_cur:
                stl = self._val(annual.iloc[0], [st_loan_col])
                tcl = self._val(annual.iloc[0], cols_cur)
                if stl and tcl and tcl > 0:
                    result += f"  短期借款/流动负债: {stl / tcl * 100:.1f}%\n"
                    if stl / tcl > 0.5:
                        result += "  ⚠ 短期借款占比偏高，再融资压力大\n"

            result += "\n" + RF.subsection("2. 非流动负债")
            cols_ncl = [c for c in ["total_ncl", "total_non_current_liab"] if c in annual.columns]
            if cols_ncl:
                result += self._trend_table(annual, cols_ncl[0], "非流动负债", unit="亿", divisor=1e8)

            lt_loan_col = None
            for c in ["long_term_loans", "lt_borrow", "长期借款"]:
                if c in annual.columns:
                    lt_loan_col = c
                    break
            if lt_loan_col and cols_ncl:
                ltl = self._val(annual.iloc[0], [lt_loan_col])
                ncl = self._val(annual.iloc[0], cols_ncl)
                if ltl and ncl and ncl > 0:
                    result += f"  长期借款/非流动负债: {ltl / ncl * 100:.1f}%\n"

            # 有息负债率
            tl = self._val(annual.iloc[0], ["total_liab"])
            stl_v = self._val(annual.iloc[0], [st_loan_col]) if st_loan_col else 0
            ltl_v = self._val(annual.iloc[0], [lt_loan_col]) if lt_loan_col else 0
            if tl and tl > 0:
                ib_debt = (stl_v or 0) + (ltl_v or 0)
                result += f"\n  有息负债率: {ib_debt / tl * 100:.1f}%（有息负债/总负债）\n"
                if ib_debt / tl > 0.6:
                    result += "  ⚠ 有息负债占比较高，利息负担重\n"

        except Exception as e:
            logger.warning(f"负债项目分析异常: {e}")
            result += f"\n  ⚠ 负债项目分析异常: {e}\n"
        return result

    # ========================================================================
    # 4. 所有者权益分析
    # ========================================================================

    def _analyze_equity_structure(self, balance) -> str:
        result = RF.section("三、所有者权益分析")
        try:
            annual = self._get_annual(balance)
            latest = annual.iloc[0]

            eq_col = None
            for c in ["total_equity", "total_hldr_eqy_exc_min_int", "股东权益合计"]:
                if c in annual.columns:
                    eq_col = c
                    break
            if not eq_col:
                result += "  股东权益数据不可用\n"
                return result

            result += self._trend_table(annual, eq_col, "股东权益合计", unit="亿", divisor=1e8)

            # 每股净资产
            eq_val = self._val(latest, [eq_col])
            if eq_val:
                share_count = self._find_total_share()
                if share_count and share_count > 0:
                    bvps = eq_val / share_count
                    result += f"  每股净资产(BVPS): {bvps:.2f} 元\n"

            # 权益构成
            re_val = None
            for c in ["retained_earnings", "undistr_porfit", "未分配利润"]:
                if c in annual.columns:
                    re_val = self._val(latest, [c])
                    break
            if re_val is not None and eq_val and eq_val > 0:
                result += f"  未分配利润/股东权益: {re_val / eq_val * 100:.1f}%\n"
                if re_val / eq_val > 0.5:
                    result += "  ✓ 留存收益充裕，内源融资能力强\n"

            # 少数股东权益
            minority = None
            for c in ["minority_interest", "minority_int", "少数股东权益"]:
                if c in annual.columns:
                    minority = self._val(latest, [c])
                    break
            if minority is not None and eq_val and eq_val > 0:
                if minority > 0:
                    result += f"  少数股东权益占比: {minority / (eq_val + minority) * 100:.1f}%\n"

            # 资本积累趋势
            if len(annual) >= 3 and eq_col in annual.columns:
                vals = [self._val(annual.iloc[i], [eq_col]) for i in range(min(3, len(annual)))]
                vals = [v for v in vals if v]
                if len(vals) >= 2 and vals[-1] and vals[-1] > 0:
                    cagr = ((vals[0] / vals[-1]) ** (1 / (len(vals) - 1)) - 1) * 100
                    result += f"  股东权益{len(vals)}年CAGR: {cagr:.1f}%\n"

        except Exception as e:
            logger.warning(f"所有者权益分析异常: {e}")
            result += f"\n  ⚠ 所有者权益分析异常: {e}\n"
        return result

    # ========================================================================
    # 5. 偿债能力分析
    # ========================================================================

    def _analyze_solvency(self, balance) -> str:
        result = RF.section("四、偿债能力分析")
        try:
            annual = self._get_annual(balance)
            income = self.data.get("income")
            cashflow = self.data.get("cashflow")

            result += "\n" + RF.subsection("1. 短期偿债能力")
            result += f"{'报告期':<12}{'流动比率':>10}{'速动比率':>10}{'现金比率':>10}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                ca = self._val(row, ["total_cur_assets", "total_current_assets"])
                cl = self._val(row, ["total_cur_liab", "total_current_liab"])
                inv = self._val(row, ["inventories", "inventory"])
                cash = self._val(row, ["money_cap"])
                cr = FC.safe_divide(ca, cl)
                qa = (ca - inv) if ca and inv else ca
                qr = FC.safe_divide(qa, cl)
                cash_r = FC.safe_divide(cash, cl)
                result += (f"{ed:<12}{FC.format_value(cr, 2):>10}"
                           f"{FC.format_value(qr, 2):>10}{FC.format_value(cash_r, 2):>10}\n")

            latest = annual.iloc[0]
            cr_latest = FC.safe_divide(
                self._val(latest, ["total_cur_assets"]),
                self._val(latest, ["total_cur_liab"]))
            if cr_latest:
                if cr_latest > 2:
                    result += "  ✓ 流动比率优秀（>2），短期偿债能力强\n"
                elif cr_latest > 1:
                    result += "  ○ 流动比率一般（1-2），短期偿债能力尚可\n"
                else:
                    result += "  ⚠ 流动比率偏低（<1），存在短期偿债压力\n"

            result += "\n" + RF.subsection("2. 长期偿债能力")
            result += f"{'报告期':<12}{'资产负债率':>12}{'产权比率':>10}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                ta = self._val(row, ["total_assets"])
                tl = self._val(row, ["total_liab"])
                eq = self._val(row, ["total_equity", "total_hldr_eqy_exc_min_int"])
                dr = FC.safe_divide(tl, ta)
                dr_pct = dr * 100 if dr else None
                er = FC.safe_divide(tl, eq)
                result += (f"{ed:<12}{FC.format_percentage(dr_pct):>12}"
                           f"{FC.format_value(er, 2):>10}\n")

            # 利息保障倍数
            if income is not None and not income.empty:
                inc_annual = self._get_annual(income)
                latest_inc = inc_annual.iloc[0] if not inc_annual.empty else None
                if latest_inc is not None:
                    ebit = self._val(latest_inc, ["operate_profit", "营业利润"])
                    fin_exp = self._val(latest_inc, ["fin_exp", "财务费用"])
                    if ebit and fin_exp and fin_exp != 0:
                        icr = (ebit + abs(fin_exp)) / abs(fin_exp)
                        result += f"\n  利息保障倍数: {icr:.1f}倍\n"
                        if icr > 5:
                            result += "  ✓ 利息保障倍数充足\n"
                        elif icr < 1:
                            result += "  ⚠ 利息保障倍数<1，利润不足以覆盖利息\n"

        except Exception as e:
            logger.warning(f"偿债能力分析异常: {e}")
            result += f"\n  ⚠ 偿债能力分析异常: {e}\n"
        return result

    # ========================================================================
    # 6. 营运能力分析
    # ========================================================================

    def _analyze_operational_efficiency(self, balance) -> str:
        result = RF.section("五、营运能力分析")
        try:
            annual_bal = self._get_annual(balance)
            income = self.data.get("income")
            if income is None or income.empty:
                result += "\n  缺少利润表数据，无法计算营运能力指标\n"
                return result
            inc_annual = self._get_annual(income)

            financial = self.data.get("financial")
            has_fin = financial is not None and not financial.empty

            result += f"\n{'报告期':<12}{'应收周转率':>12}{'存货周转率':>12}{'总资产周转率':>12}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual_bal))):
                bal_row = annual_bal.iloc[i]
                ed = str(bal_row.get("end_date", ""))
                inc_row = inc_annual[inc_annual["end_date"] == ed] if "end_date" in inc_annual.columns else inc_annual.iloc[i:i+1]
                if inc_row.empty:
                    inc_row = inc_annual.iloc[i:i+1] if i < len(inc_annual) else None
                if inc_row is None or inc_row.empty:
                    result += f"{ed:<12}{'N/A':>12}{'N/A':>12}{'N/A':>12}\n"
                    continue
                inc_row = inc_row.iloc[0]

                rev = self._val(inc_row, ["total_revenue", "revenue"])
                cost = self._val(inc_row, ["oper_cost", "operate_cost"])
                ar = self._val(bal_row, ["accounts_receivable"])
                inv = self._val(bal_row, ["inventories"])
                ta = self._val(bal_row, ["total_assets"])

                ar_turn = FC.safe_divide(rev, ar) if rev and ar else None
                inv_turn = FC.safe_divide(cost, inv) if cost and inv else None
                ta_turn = FC.safe_divide(rev, ta) if rev and ta else None

                result += (f"{ed:<12}{FC.format_value(ar_turn, 2):>12}"
                           f"{FC.format_value(inv_turn, 2):>12}"
                           f"{FC.format_value(ta_turn, 2):>12}\n")

            # 注释
            latest_bal = annual_bal.iloc[0]
            latest_inc = inc_annual.iloc[0] if not inc_annual.empty else None
            if latest_inc is not None:
                ta_t = FC.safe_divide(
                    self._val(latest_inc, ["total_revenue", "revenue"]),
                    self._val(latest_bal, ["total_assets"]))
                if ta_t is not None:
                    result += f"\n  总资产周转率(最新): {ta_t:.2f}次\n"
                    if ta_t > 1:
                        result += "  ✓ 资产周转效率高\n"
                    elif ta_t < 0.3:
                        result += "  ⚠ 资产周转率偏低，资产利用效率不足\n"

        except Exception as e:
            logger.warning(f"营运能力分析异常: {e}")
            result += f"\n  ⚠ 营运能力分析异常: {e}\n"
        return result

    # ========================================================================
    # 7. 资产结构分析
    # ========================================================================

    def _analyze_asset_structure(self, balance) -> str:
        result = RF.section("六、资产结构分析")
        try:
            annual = self._get_annual(balance)
            result += f"\n{'报告期':<12}{'流动资产%':>12}{'非流动资产%':>14}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                ta = self._val(row, ["total_assets"])
                ca = self._val(row, ["total_cur_assets"])
                nca = self._val(row, ["total_nca"])
                if not nca and ta and ca:
                    nca = ta - ca

                ca_pct = (ca / ta * 100) if ca and ta else None
                nca_pct = (nca / ta * 100) if nca and ta else None
                result += (f"{ed:<12}{FC.format_percentage(ca_pct, 1):>12}"
                           f"{FC.format_percentage(nca_pct, 1):>14}\n")

            latest = annual.iloc[0]
            fa_val = self._val(latest, ["fixed_assets", "fix_assets"])
            ta_val = self._val(latest, ["total_assets"])
            if fa_val and ta_val and ta_val > 0:
                ratio = fa_val / ta_val * 100
                if ratio > 40:
                    result += f"\n  → 固定资产占比 {ratio:.1f}%，重资产经营模式（经营主导型）\n"
                else:
                    result += f"\n  → 固定资产占比 {ratio:.1f}%，轻资产/投资主导型\n"

        except Exception as e:
            logger.warning(f"资产结构分析异常: {e}")
            result += f"\n  ⚠ 资产结构分析异常: {e}\n"
        return result

    # ========================================================================
    # 8. 资本结构分析
    # ========================================================================

    def _analyze_capital_structure(self, balance) -> str:
        result = RF.section("七、资本结构分析")
        try:
            annual = self._get_annual(balance)
            result += f"\n{'报告期':<12}{'资产负债率':>12}{'权益比率':>12}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                ta = self._val(row, ["total_assets"])
                tl = self._val(row, ["total_liab"])
                eq = self._val(row, ["total_equity", "total_hldr_eqy_exc_min_int"])

                dr = (tl / ta * 100) if tl and ta else None
                er = (eq / ta * 100) if eq and ta else None
                result += (f"{ed:<12}{FC.format_percentage(dr, 1):>12}"
                           f"{FC.format_percentage(er, 1):>12}\n")

            latest = annual.iloc[0]
            dr_latest = FC.safe_divide(
                self._val(latest, ["total_liab"]),
                self._val(latest, ["total_assets"]))
            if dr_latest:
                dr_pct = dr_latest * 100
                if dr_pct > 70:
                    result += f"\n  ⚠ 资产负债率 {dr_pct:.1f}%，财务杠杆偏高\n"
                elif dr_pct < 30:
                    result += f"\n  → 资产负债率 {dr_pct:.1f}%，财务保守，杠杆利用不足\n"
                else:
                    result += f"\n  → 资产负债率 {dr_pct:.1f}%，资本结构合理\n"

        except Exception as e:
            logger.warning(f"资本结构分析异常: {e}")
            result += f"\n  ⚠ 资本结构分析异常: {e}\n"
        return result

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _get_annual(self, df):
        """获取年度数据（优先 end_date 以 1231 结尾的行）"""
        if df is None or df.empty:
            return df
        if "end_date" in df.columns:
            annual = df[df["end_date"].astype(str).str.endswith("1231")]
            if annual.empty:
                annual = df.head(5)
            return annual.sort_values("end_date", ascending=False).reset_index(drop=True)
        return df.head(5)

    def _trend_table(self, df, col: str, label: str, unit: str = "亿",
                     divisor: float = 1e8, with_ratio: str = None) -> str:
        """生成多年趋势表格"""
        result = f"\n{'报告期':<12}{label:>14}"
        if with_ratio:
            result += f"{'占总资产%':>12}"
        result += "\n" + SEPARATOR_LIGHT + "\n"

        for i in range(min(5, len(df))):
            row = df.iloc[i]
            ed = str(row.get("end_date", ""))
            v = self._val(row, [col])
            if v is not None:
                result += f"{ed:<12}{FC.format_value(v / divisor, 2, unit):>14}"
            else:
                result += f"{ed:<12}{'N/A':>14}"
            if with_ratio:
                ta = self._val(row, [with_ratio])
                if v is not None and ta and ta > 0:
                    result += f"{v / ta * 100:>11.1f}%"
                else:
                    result += f"{'N/A':>12}"
            result += "\n"
        return result

    def _find_total_share(self) -> float | None:
        """从 basic / daily_basic 查找总股本"""
        for df_key in ["basic", "daily_basic", "stock_basic"]:
            df = self.data.get(df_key)
            if df is not None and not df.empty:
                v = None
                for c in ["total_share", "total_share_y", "float_share"]:
                    if c in df.columns:
                        v = self._val(df.iloc[0], [c])
                        if v is not None:
                            return v
        return None

    @staticmethod
    def _val(row, keys: list) -> float | None:
        """从行中安全提取数值"""
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
