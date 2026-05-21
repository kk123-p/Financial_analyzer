"""
利润表分析器 — 基于《大数据财务分析框架》第四章
涵盖：收入分析 / 成本费用分析 / 利润结构 / 利润质量 / 非经常性损益 / 预警信号
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import SEPARATOR_LIGHT
from ..logging_config import get_logger

logger = get_logger(__name__)


class IncomeStatementAnalyzer(BaseAnalyzer):
    """利润表综合分析器"""

    def analyze(self) -> str:
        result = RF.header("利润表综合分析报告")
        try:
            income, _ = self._fetch_data("income")
        except Exception:
            income = self.data.get("income")
        if income is None or income.empty:
            return result + "\n❌ 未获取到利润表数据，无法进行分析"

        result += self._analyze_revenue(income)
        result += self._analyze_cost_expense(income)
        result += self._analyze_profit_structure(income)
        result += self._analyze_profit_quality(income)
        result += self._analyze_deducted_profit(income)
        result += self._check_warning_signals(income)
        result += RF.footer()
        return result

    # ========================================================================
    # 2. 收入分析
    # ========================================================================

    def _analyze_revenue(self, income) -> str:
        result = RF.section("一、收入分析")
        try:
            annual = self._get_annual(income)
            if annual.empty:
                return result + "\n  收入数据不可用\n"

            rev_col = self._find_col(annual, ["total_revenue", "revenue", "营业收入"])
            if not rev_col:
                return result + "\n  收入数据不可用\n"

            result += RF.subsection("1. 营收趋势")
            result += f"\n{'报告期':<12}{'营业收入':>14}{'同比增长':>12}\n{SEPARATOR_LIGHT}\n"
            revs = []
            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                rev = self._val(row, [rev_col])
                revs.append(rev)
                rev_str = FC.format_value(rev / 1e8, 2, "亿") if rev else "N/A"
                yoy = None
                if i < len(revs) - 1 and revs[i] and revs[i + 1]:
                    yoy = (revs[i] - revs[i + 1]) / abs(revs[i + 1]) * 100
                result += f"{ed:<12}{rev_str:>14}{FC.format_change(yoy):>12}\n"

            if len(revs) >= 3 and revs[0] and revs[-1]:
                years = len(revs) - 1
                cagr = ((revs[0] / revs[-1]) ** (1 / years) - 1) * 100
                result += f"\n  营收{years}年CAGR: {cagr:.1f}%\n"

            if len(revs) >= 2 and revs[0] and revs[1]:
                yoy_latest = (revs[0] - revs[1]) / abs(revs[1]) * 100
                if yoy_latest > 20:
                    result += "  ✓ 营收高速增长\n"
                elif yoy_latest > 5:
                    result += "  ○ 营收稳健增长\n"
                elif yoy_latest > 0:
                    result += "  → 营收微增\n"
                else:
                    result += "  ⚠ 营收下滑，需关注\n"

            # 收入含金量
            result += RF.subsection("2. 收入含金量（现金流匹配）")
            cashflow = self.data.get("cashflow")
            if cashflow is not None and not cashflow.empty:
                cf_annual = self._get_annual(cashflow)
                if not cf_annual.empty:
                    cash_rev = self._val(cf_annual.iloc[0], ["cash_received_from_sales",
                                           "c_fr_sale_sg", "销售商品收到的现金"])
                    if cash_rev and revs[0] and revs[0] > 0:
                        ratio = cash_rev / revs[0]
                        # 单位修正
                        if ratio > 100:
                            ratio = cash_rev / (revs[0] * 10000)
                        result += f"  销售收到现金/营业收入: {ratio:.2f}\n"
                        if ratio >= 1.0:
                            result += "  ✓ 收入含金量高，现金流充沛\n"
                        elif ratio >= 0.8:
                            result += "  ○ 收入含金量可接受\n"
                        else:
                            result += "  ⚠ 收入含金量偏低，可能存在大量赊销或收入虚增\n"
            else:
                result += "  现金流量表数据不可用，无法评估收入含金量\n"

        except Exception as e:
            logger.warning(f"收入分析异常: {e}")
            result += f"\n  ⚠ 收入分析异常: {e}\n"
        return result

    # ========================================================================
    # 3. 成本费用分析
    # ========================================================================

    def _analyze_cost_expense(self, income) -> str:
        result = RF.section("二、成本费用分析")
        try:
            annual = self._get_annual(income)
            if annual.empty:
                return result + "\n  数据不可用\n"

            rev_col = self._find_col(annual, ["total_revenue", "revenue"])
            cost_col = self._find_col(annual, ["oper_cost", "operate_cost", "营业成本"])

            result += RF.subsection("1. 毛利率走势")
            if rev_col and cost_col:
                result += f"\n{'报告期':<12}{'毛利率':>12}\n{SEPARATOR_LIGHT}\n"
                for i in range(min(5, len(annual))):
                    row = annual.iloc[i]
                    ed = str(row.get("end_date", ""))
                    rev = self._val(row, [rev_col])
                    cost = self._val(row, [cost_col])
                    gm = None
                    if rev and cost and rev > 0:
                        gm = (rev - cost) / rev * 100
                    result += f"{ed:<12}{FC.format_percentage(gm, 1):>12}\n"

                latest = annual.iloc[0]
                rev_l = self._val(latest, [rev_col])
                cost_l = self._val(latest, [cost_col])
                if rev_l and cost_l and rev_l > 0:
                    gm_l = (rev_l - cost_l) / rev_l * 100
                    if gm_l > 50:
                        result += f"  ✓ 毛利率 {gm_l:.1f}%，产品竞争力强\n"
                    elif gm_l > 20:
                        result += f"  ○ 毛利率 {gm_l:.1f}%，处于合理水平\n"
                    else:
                        result += f"  ⚠ 毛利率 {gm_l:.1f}%，盈利能力薄弱\n"

            result += RF.subsection("2. 期间费用率分析")
            expense_items = [
                ("sell_exp", "销售费用率"),
                ("admin_exp", "管理费用率"),
                ("fin_exp", "财务费用率"),
                ("rd_exp", "研发费用率"),
            ]
            rev_col_name = rev_col
            result += f"\n{'报告期':<12}"
            for _, label in expense_items:
                result += f"{label:>12}"
            result += f"\n{SEPARATOR_LIGHT}\n"

            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                rev = self._val(row, [rev_col_name]) if rev_col_name else None
                result += f"{ed:<12}"
                for col, _ in expense_items:
                    exp = self._val(row, [col])
                    ratio = (exp / rev * 100) if exp and rev and rev > 0 else None
                    result += f"{FC.format_percentage(ratio, 1):>12}"
                result += "\n"

            # 费用率评价
            latest = annual.iloc[0]
            rev_latest = self._val(latest, [rev_col_name]) if rev_col_name else None
            if rev_latest and rev_latest > 0:
                result += "\n"
                rd_exp_v = self._val(latest, ["rd_exp"])
                if rd_exp_v:
                    rd_ratio = rd_exp_v / rev_latest * 100
                    if rd_ratio > 10:
                        result += f"  → 研发费用率 {rd_ratio:.1f}%，研发投入强度高\n"

                sell_v = self._val(latest, ["sell_exp"])
                admin_v = self._val(latest, ["admin_exp"])
                fin_v = self._val(latest, ["fin_exp"])
                total_period = (sell_v or 0) + (admin_v or 0) + (fin_v or 0)
                period_ratio = total_period / rev_latest * 100
                result += f"  三项期间费用合计/营收: {period_ratio:.1f}%\n"
                if period_ratio > 40:
                    result += "  ⚠ 期间费用率偏高，侵蚀利润空间\n"
                elif period_ratio < 15:
                    result += "  ✓ 期间费用控制良好\n"

        except Exception as e:
            logger.warning(f"成本费用分析异常: {e}")
            result += f"\n  ⚠ 成本费用分析异常: {e}\n"
        return result

    # ========================================================================
    # 4. 利润结构分析（五级分解）
    # ========================================================================

    def _analyze_profit_structure(self, income) -> str:
        result = RF.section("三、利润结构分析（五级分解）")
        try:
            annual = self._get_annual(income)
            if annual.empty:
                return result + "\n  数据不可用\n"

            latest = annual.iloc[0]
            rev = self._val(latest, ["total_revenue", "revenue"])
            cost = self._val(latest, ["oper_cost", "operate_cost"])
            sell = self._val(latest, ["sell_exp"])
            admin = self._val(latest, ["admin_exp"])
            fin = self._val(latest, ["fin_exp"])
            rd = self._val(latest, ["rd_exp"])
            op_profit = self._val(latest, ["operate_profit", "营业利润"])
            total_profit_v = self._val(latest, ["total_profit", "利润总额"])
            np_v = self._val(latest, ["net_profit", "净利润"])

            if not rev or rev == 0:
                return result + "\n  营收数据不可用\n"

            lines = []
            # L1: 毛利
            gross = (rev - cost) if cost else None
            lines.append((f"  L1 毛利{'':<10}", f"{FC.format_value(gross / 1e8, 2, '亿') if gross else 'N/A':>14}",
                          f"{gross / rev * 100:.1f}%" if gross else "N/A"))
            # L2: 核心营业利润
            period = (sell or 0) + (admin or 0) + (fin or 0) + (rd or 0)
            core_profit = (gross - period) if gross else None
            label2 = "L2 核心营业利润"
            lines.append((f"  {label2:<14}",
                          f"{FC.format_value(core_profit / 1e8, 2, '亿') if core_profit else 'N/A':>14}",
                          f"{core_profit / rev * 100:.1f}%" if core_profit else "N/A"))
            # L3: 营业利润
            lines.append((f"  L3 营业利润{'':<10}",
                          f"{FC.format_value(op_profit / 1e8, 2, '亿') if op_profit else 'N/A':>14}",
                          f"{op_profit / rev * 100:.1f}%" if op_profit else "N/A"))
            # L4: 利润总额
            lines.append((f"  L4 利润总额{'':<10}",
                          f"{FC.format_value(total_profit_v / 1e8, 2, '亿') if total_profit_v else 'N/A':>14}",
                          f"{total_profit_v / rev * 100:.1f}%" if total_profit_v else "N/A"))
            # L5: 净利润
            lines.append((f"  L5 净利润{'':<12}",
                          f"{FC.format_value(np_v / 1e8, 2, '亿') if np_v else 'N/A':>14}",
                          f"{np_v / rev * 100:.1f}%" if np_v else "N/A"))

            result += f"\n{'':>16}{'绝对额':>14}{'占营收%':>12}\n{SEPARATOR_LIGHT}\n"
            for label, amount, pct in lines:
                result += f"{label}{amount}{pct}\n"

            # 利润侵蚀位置识别
            if core_profit and op_profit:
                gap = core_profit - op_profit
                if abs(gap) > 0 and core_profit > 0:
                    if gap / core_profit > 0.2:
                        result += f"\n  ⚠ 核心利润→营业利润存在较大折损（{gap / 1e8:.2f}亿），关注投资收益/减值/公允价值变动\n"

            if total_profit_v and np_v:
                tax_rate = (total_profit_v - np_v) / total_profit_v * 100 if total_profit_v > 0 else 0
                result += f"\n  实际税率: {tax_rate:.1f}%\n"

            # 多年利润趋势
            result += RF.subsection("多年利润趋势")
            result += f"\n{'报告期':<12}{'毛利':>12}{'营业利润':>12}{'净利润':>12}\n{SEPARATOR_LIGHT}\n"
            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                r = self._val(row, ["total_revenue", "revenue"])
                c = self._val(row, ["oper_cost", "operate_cost"])
                op = self._val(row, ["operate_profit", "营业利润"])
                np_val = self._val(row, ["net_profit", "净利润"])
                g = (r - c) if r and c else None
                result += (f"{ed:<12}{FC.format_value(g / 1e8, 2, '亿') if g else 'N/A':>12}"
                           f"{FC.format_value(op / 1e8, 2, '亿') if op else 'N/A':>12}"
                           f"{FC.format_value(np_val / 1e8, 2, '亿') if np_val else 'N/A':>12}\n")

        except Exception as e:
            logger.warning(f"利润结构分析异常: {e}")
            result += f"\n  ⚠ 利润结构分析异常: {e}\n"
        return result

    # ========================================================================
    # 5. 利润质量分析
    # ========================================================================

    def _analyze_profit_quality(self, income) -> str:
        result = RF.section("四、利润质量分析")
        try:
            annual = self._get_annual(income)
            if annual.empty:
                return result + "\n  数据不可用\n"

            rev_col = self._find_col(annual, ["total_revenue", "revenue"])

            result += RF.subsection("1. 利润率多年趋势")
            result += f"\n{'报告期':<12}{'毛利率':>10}{'净利率':>10}{'营业利润率':>10}\n{SEPARATOR_LIGHT}\n"
            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                rev = self._val(row, [rev_col]) if rev_col else None
                cost = self._val(row, ["oper_cost", "operate_cost"])
                np_v = self._val(row, ["net_profit", "净利润"])
                op = self._val(row, ["operate_profit", "营业利润"])
                gm = (rev - cost) / rev * 100 if rev and cost and rev > 0 else None
                nm = np_v / rev * 100 if np_v and rev and rev > 0 else None
                om = op / rev * 100 if op and rev and rev > 0 else None
                result += (f"{ed:<12}{FC.format_percentage(gm, 1):>10}"
                           f"{FC.format_percentage(nm, 1):>10}{FC.format_percentage(om, 1):>10}\n")

            result += RF.subsection("2. 盈利质量（现金流匹配）")
            cashflow = self.data.get("cashflow")
            if cashflow is not None and not cashflow.empty:
                cf_annual = self._get_annual(cashflow)
                latest = annual.iloc[0]
                np_v = self._val(latest, ["net_profit", "净利润"])
                if not cf_annual.empty:
                    ocf = self._val(cf_annual.iloc[0], ["n_cashflow_act", "经营活动现金流量净额"])
                    if ocf is not None and np_v and np_v > 0:
                        ratio = ocf / np_v
                        result += f"\n  经营现金流/净利润: {ratio:.2f}\n"
                        if ratio >= 1.0:
                            result += "  ✓ 利润含金量高，每1元净利润有充足现金支撑\n"
                        elif ratio >= 0.7:
                            result += "  ○ 利润含金量良好\n"
                        elif ratio >= 0:
                            result += "  ⚠ 利润含金量偏低，部分利润未转化为现金\n"
                        else:
                            result += "  ❌ 经营现金流为负，利润质量严重存疑\n"

                    # 多年OCF/NP趋势
                    result += f"\n{'报告期':<12}{'经营CF':>14}{'净利润':>14}{'OCF/NP':>10}\n{SEPARATOR_LIGHT}\n"
                    for i in range(min(5, len(annual))):
                        inc_row = annual.iloc[i]
                        ed = str(inc_row.get("end_date", ""))
                        np_i = self._val(inc_row, ["net_profit", "净利润"])
                        cf_row = cf_annual[cf_annual["end_date"] == ed] if "end_date" in cf_annual.columns else None
                        ocf_i = None
                        if cf_row is not None and not cf_row.empty:
                            ocf_i = self._val(cf_row.iloc[0], ["n_cashflow_act", "经营活动现金流量净额"])
                        ocf_np = (ocf_i / np_i) if ocf_i and np_i and np_i != 0 else None
                        result += (f"{ed:<12}{FC.format_value(ocf_i / 1e8, 2, '亿') if ocf_i else 'N/A':>14}"
                                   f"{FC.format_value(np_i / 1e8, 2, '亿') if np_i else 'N/A':>14}"
                                   f"{FC.format_value(ocf_np, 2):>10}\n")
            else:
                result += "\n  现金流量表数据不可用\n"

            result += RF.subsection("3. 非经常性损益影响")
            latest = annual.iloc[0]
            credit_imp = self._val(latest, ["credit_impairment_loss"])
            asset_imp = self._val(latest, ["asset_impairment_loss"])
            total_profit_v = self._val(latest, ["total_profit", "利润总额"])

            if total_profit_v and total_profit_v > 0:
                imp_sum = (abs(credit_imp) if credit_imp else 0) + (abs(asset_imp) if asset_imp else 0)
                if imp_sum > 0:
                    result += f"  减值损失合计: {imp_sum / 1e8:.2f}亿 | 占利润总额: {imp_sum / total_profit_v * 100:.1f}%\n"
                    if imp_sum / total_profit_v > 0.3:
                        result += "  ⚠ 减值损失占利润比重过高，利润质量存疑\n"

                minority_v = self._val(latest, ["minority_interest", "少数股东损益"])
                np_attr = self._val(latest, ["n_income_attr_p", "归属于母公司所有者的净利润"])
                if np_attr and np_v and np_v > 0:
                    if np_attr / np_v < 0.7:
                        result += f"  ⚠ 归母净利润/净利润: {np_attr / np_v * 100:.1f}%，少数股东损益占比高\n"

            # ROE
            result += RF.subsection("4. ROE 分析")
            financial = self.data.get("financial")
            balance = self.data.get("balance")
            roe_val = None
            if financial is not None and not financial.empty:
                fin_annual = self._get_annual(financial)
                if not fin_annual.empty and "roe" in fin_annual.columns:
                    roe_val = self._val(fin_annual.iloc[0], ["roe"])
                    result += f"  ROE: {roe_val:.2f}%（来源：财务指标）\n"
            if roe_val is None and balance is not None and not balance.empty:
                bal_annual = self._get_annual(balance)
                if not bal_annual.empty:
                    eq = self._val(bal_annual.iloc[0], ["total_equity", "total_hldr_eqy_exc_min_int"])
                    np_v2 = self._val(annual.iloc[0], ["net_profit", "净利润"])
                    if eq and np_v2 and eq > 0:
                        roe_val = np_v2 / eq * 100
                        result += f"  ROE: {roe_val:.2f}%（估算：净利润/股东权益）\n"
            if roe_val is not None:
                if roe_val > 20:
                    result += "  ✓ ROE优秀\n"
                elif roe_val > 10:
                    result += "  ○ ROE良好\n"
                elif roe_val > 5:
                    result += "  → ROE一般\n"
                else:
                    result += "  ⚠ ROE偏低\n"

        except Exception as e:
            logger.warning(f"利润质量分析异常: {e}")
            result += f"\n  ⚠ 利润质量分析异常: {e}\n"
        return result

    # ========================================================================
    # 6. 扣非净利润分析
    # ========================================================================

    def _analyze_deducted_profit(self, income) -> str:
        result = RF.section("五、归母净利润与少数股东分析")
        try:
            annual = self._get_annual(income)
            if annual.empty:
                return result + "\n  数据不可用\n"

            result += f"\n{'报告期':<12}{'净利润':>14}{'归母净利润':>14}{'归母占比':>10}\n{SEPARATOR_LIGHT}\n"
            for i in range(min(5, len(annual))):
                row = annual.iloc[i]
                ed = str(row.get("end_date", ""))
                np_v = self._val(row, ["net_profit", "净利润"])
                attr = self._val(row, ["n_income_attr_p", "归属于母公司所有者的净利润", "net_profit_attr"])
                ratio = (attr / np_v * 100) if attr and np_v and np_v > 0 else None
                result += (f"{ed:<12}{FC.format_value(np_v / 1e8, 2, '亿') if np_v else 'N/A':>14}"
                           f"{FC.format_value(attr / 1e8, 2, '亿') if attr else 'N/A':>14}"
                           f"{FC.format_percentage(ratio, 1):>10}\n")

            latest = annual.iloc[0]
            np_l = self._val(latest, ["net_profit", "净利润"])
            attr_l = self._val(latest, ["n_income_attr_p", "归属于母公司所有者的净利润"])
            if np_l and attr_l and np_l > 0:
                gap_pct = (np_l - attr_l) / np_l * 100
                if gap_pct > 10:
                    result += f"\n  ⚠ 少数股东损益占比 {gap_pct:.1f}%，归母利润与净利润差距较大\n"

        except Exception as e:
            logger.warning(f"归母净利润分析异常: {e}")
            result += f"\n  ⚠ 归母净利润分析异常: {e}\n"
        return result

    # ========================================================================
    # 7. 预警信号检测（框架7.4节）
    # ========================================================================

    def _check_warning_signals(self, income) -> str:
        result = RF.section("六、利润质量预警信号")
        try:
            annual = self._get_annual(income)
            if len(annual) < 2:
                result += "\n  数据不足（需至少2期），无法检测预警信号\n"
                return result

            warnings = []
            latest = annual.iloc[0]
            prev = annual.iloc[1]
            rev_col = self._find_col(annual, ["total_revenue", "revenue"])

            # 1. 营收增速 vs 应收增速
            balance = self.data.get("balance")
            if balance is not None and not balance.empty and rev_col:
                bal_annual = self._get_annual(balance)
                if len(bal_annual) >= 2:
                    rev_l = self._val(latest, [rev_col])
                    rev_p = self._val(prev, [rev_col])
                    ar_l = self._val(bal_annual.iloc[0], ["accounts_receivable"])
                    ar_p = self._val(bal_annual.iloc[1], ["accounts_receivable"])
                    if all([rev_l, rev_p, ar_l, ar_p]) and rev_p > 0 and ar_p > 0:
                        rev_g = (rev_l - rev_p) / rev_p * 100
                        ar_g = (ar_l - ar_p) / ar_p * 100
                        if ar_g > rev_g + 20:
                            warnings.append(f"应收增速({ar_g:.1f}%)远超营收增速({rev_g:.1f}%)，差{ar_g - rev_g:.0f}pct")

            # 2. 存货周转过慢
            if balance is not None and not balance.empty:
                bal_annual = self._get_annual(balance)
                if not bal_annual.empty:
                    inv_l = self._val(bal_annual.iloc[0], ["inventories"])
                    cost_l = self._val(latest, ["oper_cost", "operate_cost"])
                    if inv_l and cost_l and cost_l > 0 and len(bal_annual) >= 2:
                        inv_p = self._val(bal_annual.iloc[1], ["inventories"])
                        if inv_p and inv_p > 0:
                            inv_g = (inv_l - inv_p) / inv_p * 100
                            if inv_g > 30:
                                warnings.append(f"存货大幅增长({inv_g:.1f}%)，可能存在滞销")

            # 3. 过度依赖非经常性损益
            op_profit_l = self._val(latest, ["operate_profit", "营业利润"])
            total_profit_l = self._val(latest, ["total_profit", "利润总额"])
            if op_profit_l and total_profit_l and total_profit_l > 0:
                if op_profit_l / total_profit_l < 0.5:
                    warnings.append(f"营业利润仅占利润总额{op_profit_l / total_profit_l * 100:.1f}%，过度依赖非经常性损益")

            # 4. 费用异常波动
            if rev_col:
                rev_l = self._val(latest, [rev_col])
                rev_p = self._val(prev, [rev_col])
                if rev_l and rev_p and rev_p > 0:
                    rev_g = (rev_l - rev_p) / rev_p * 100
                    for exp_col, exp_name in [("sell_exp", "销售费用"), ("admin_exp", "管理费用")]:
                        exp_l = self._val(latest, [exp_col])
                        exp_p = self._val(prev, [exp_col])
                        if exp_l and exp_p and exp_p > 0:
                            exp_g = (exp_l - exp_p) / exp_p * 100
                            if exp_g > rev_g + 30:
                                warnings.append(f"{exp_name}增速({exp_g:.1f}%)远超营收增速({rev_g:.1f}%)")

            # 5. 减值损失异常
            credit = self._val(latest, ["credit_impairment_loss"])
            asset_imp = self._val(latest, ["asset_impairment_loss"])
            if credit and total_profit_l and total_profit_l > 0:
                if abs(credit) / total_profit_l > 0.5:
                    warnings.append(f"信用减值损失巨大({credit / 1e8:.2f}亿)，占利润总额{abs(credit) / total_profit_l * 100:.0f}%")
            if asset_imp and total_profit_l and total_profit_l > 0:
                if abs(asset_imp) / total_profit_l > 0.5:
                    warnings.append(f"资产减值损失巨大({asset_imp / 1e8:.2f}亿)")

            if warnings:
                result += "\n"
                for i, w in enumerate(warnings, 1):
                    result += f"  ⚠ {i}. {w}\n"
            else:
                result += "\n  ✓ 未检测到明显的利润质量预警信号\n"

        except Exception as e:
            logger.warning(f"预警信号检测异常: {e}")
            result += f"\n  ⚠ 预警信号检测异常: {e}\n"
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
    def _find_col(df, candidates: list) -> str | None:
        for c in candidates:
            if c in df.columns:
                return c
        return None

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
