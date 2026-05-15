"""
盈利能力、营运能力、偿债能力、成长能力分析器
降级策略：缺少某个数据源时，能算什么算什么，不整体失败
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import SEPARATOR_LIGHT
from ..logging_config import get_logger

logger = get_logger(__name__)


class ProfitabilityAnalyzer(BaseAnalyzer):
    """盈利/营运/偿债/成长能力分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def analyze_profitability(self) -> str:
        """盈利能力分析（降级：financial 不可用时从 income 计算）"""
        result = RF.header("盈利能力分析报告")

        df_fin, _ = self._fetch_data("financial")
        df_income, _ = self._fetch_data("income")

        # --- ROE 分析（优先用 financial，否则从 income + balance 估算）---
        has_fin = df_fin is not None and not df_fin.empty
        has_income = df_income is not None and not df_income.empty

        if has_fin:
            annual_fin = df_fin[df_fin["end_date"].str.endswith("1231")].head(5)
            if annual_fin.empty:
                annual_fin = df_fin.head(5)

            result += RF.section("净资产收益率(ROE)分析")
            result += f"{'报告期':<12}{'ROE':>12}{'ROE(摊薄)':>12}{'变化':>12}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            roes = []
            for _, row in annual_fin.iterrows():
                end_date = row.get("end_date", "N/A")
                roe = row.get("roe")
                roe_dt = row.get("roe_dt")
                roes.append(roe)
                change = None
                if len(roes) > 1 and roes[-2] and roes[-2] != 0:
                    change = roe - roes[-2] if roe else None
                result += (
                    f"{end_date:<12}"
                    f"{FC.format_percentage(roe):>12}"
                    f"{FC.format_percentage(roe_dt):>12}"
                    f"{FC.format_change(change):>12}\n"
                )
            result += "\n"
        else:
            roes = []
            result += RF.section("ROE 分析")
            result += "  ⚠ 财务指标数据不可用，ROE 无法计算\n"
            result += "  提示：请检查数据源是否返回了财务指标数据\n\n"

        # --- 净利率 / 毛利率分析（从 income 计算，不依赖 financial）---
        result += RF.section("利润率分析")
        if has_income:
            annual_inc = df_income[df_income["end_date"].str.endswith("1231")].head(5)
            if annual_inc.empty:
                annual_inc = df_income.head(5)

            result += f"{'报告期':<12}{'净利率':>12}{'毛利率':>12}{'营业利润率':>12}\n"
            result += f"{SEPARATOR_LIGHT}\n"

            for _, row in annual_inc.iterrows():
                end_date = row.get("end_date", "N/A")
                revenue = row.get("total_revenue") or row.get("revenue")
                net_profit = row.get("net_profit")
                op_cost = row.get("oper_cost") or row.get("营业支出")
                op_profit = row.get("operate_profit")

                net_margin = (net_profit / revenue * 100) if net_profit and revenue and revenue > 0 else None
                gross_margin = ((revenue - op_cost) / revenue * 100) if revenue and op_cost and revenue > 0 else None
                op_margin = (op_profit / revenue * 100) if op_profit and revenue and revenue > 0 else None

                result += (
                    f"{end_date:<12}"
                    f"{FC.format_percentage(net_margin):>12}"
                    f"{FC.format_percentage(gross_margin):>12}"
                    f"{FC.format_percentage(op_margin):>12}\n"
                )
        else:
            result += "  ❌ 未获取到利润表数据\n"

        # --- 分析结论 ---
        result += "\n" + RF.section("分析结论")
        if roes and roes[0]:
            roe = roes[0]
            if roe > 20:
                result += f"  ✓ ROE {roe:.1f}%，盈利能力优秀\n"
            elif roe > 10:
                result += f"  ○ ROE {roe:.1f}%，盈利能力良好\n"
            elif roe > 5:
                result += f"  ⚠ ROE {roe:.1f}%，盈利能力一般\n"
            else:
                result += f"  ✗ ROE {roe:.1f}%，盈利能力较弱\n"
        elif has_income:
            # 从 income 数据给结论
            annual_inc = df_income[df_income["end_date"].str.endswith("1231")].head(1)
            if not annual_inc.empty:
                row = annual_inc.iloc[0]
                revenue = row.get("total_revenue") or row.get("revenue")
                net_profit = row.get("net_profit")
                if net_profit and revenue and revenue > 0:
                    nm = net_profit / revenue * 100
                    if nm > 20:
                        result += f"  ✓ 净利率 {nm:.1f}%，盈利能力优秀\n"
                    elif nm > 10:
                        result += f"  ○ 净利率 {nm:.1f}%，盈利能力良好\n"
                    elif nm > 0:
                        result += f"  ⚠ 净利率 {nm:.1f}%，盈利能力一般\n"
                    else:
                        result += f"  ✗ 净利率 {nm:.1f}%，处于亏损状态\n"

        result += RF.footer()
        return result

    def analyze_operation_ability(self) -> str:
        """营运能力分析（降级：financial 不可用时从 balance+income 估算）"""
        result = RF.header("营运能力分析报告")

        df_fin, _ = self._fetch_data("financial")
        has_fin = df_fin is not None and not df_fin.empty

        if has_fin:
            annual = df_fin[df_fin["end_date"].str.endswith("1231")].head(5)
            if annual.empty:
                annual = df_fin.head(5)

            # 应收账款周转
            result += RF.section("应收账款周转分析")
            result += f"{'报告期':<12}{'周转率(次)':>14}{'周转天数':>12}\n"
            result += f"{SEPARATOR_LIGHT}\n"
            for _, row in annual.iterrows():
                end_date = row.get("end_date", "N/A")
                ar_turnover = row.get("ar_turnover")
                ar_days = row.get("ar_turnover_days")
                result += (
                    f"{end_date:<12}"
                    f"{FC.format_value(ar_turnover, 2):>14}"
                    f"{FC.format_value(ar_days, 0, '天'):>12}\n"
                )

            result += "\n"
            result += RF.section("存货周转分析")
            result += f"{'报告期':<12}{'周转率(次)':>14}{'周转天数':>12}\n"
            result += f"{SEPARATOR_LIGHT}\n"
            # 尝试从 financial 取，没有则从 balance+income 计算
            df_balance, _ = self._fetch_data("balance")
            df_income, _ = self._fetch_data("income")
            for _, row in annual.iterrows():
                end_date = row.get("end_date", "N/A")
                inv_turnover = row.get("inv_turnover")
                inv_days = row.get("inv_turnover_days")
                # 降级：从 balance + income 计算存货周转
                if inv_turnover is None and df_balance is not None and df_income is not None:
                    bal_row = df_balance[df_balance["end_date"] == end_date]
                    inc_row = df_income[df_income["end_date"] == end_date]
                    if not bal_row.empty and not inc_row.empty:
                        inv = bal_row.iloc[0].get("inventories")
                        op_cost = inc_row.iloc[0].get("oper_cost")
                        if inv and inv > 0 and op_cost:
                            inv_turnover = op_cost / inv
                            inv_days = 365 / inv_turnover if inv_turnover > 0 else None
                result += (
                    f"{end_date:<12}"
                    f"{FC.format_value(inv_turnover, 2):>14}"
                    f"{FC.format_value(inv_days, 0, '天'):>12}\n"
                )

            result += "\n"
            result += RF.section("总资产周转分析")
            result += f"{'报告期':<12}{'总资产周转率':>14}\n"
            result += f"{SEPARATOR_LIGHT}\n"
            for _, row in annual.iterrows():
                end_date = row.get("end_date", "N/A")
                ta_turnover = row.get("ta_turnover") or row.get("assets_turn")
                result += f"{end_date:<12}{FC.format_value(ta_turnover, 2):>14}\n"
        else:
            # 降级：从 balance + income 手动计算
            df_balance, _ = self._fetch_data("balance")
            df_income, _ = self._fetch_data("income")
            has_balance = df_balance is not None and not df_balance.empty
            has_income = df_income is not None and not df_income.empty

            if has_balance and has_income:
                result += RF.section("营运能力估算（从原始报表计算）")
                result += f"{'报告期':<12}{'应收周转率':>12}{'存货周转率':>12}{'总资产周转率':>12}\n"
                result += f"{SEPARATOR_LIGHT}\n"

                bal_annual = df_balance[df_balance["end_date"].str.endswith("1231")].head(5)
                inc_annual = df_income[df_income["end_date"].str.endswith("1231")].head(5)

                for _, bal_row in bal_annual.iterrows():
                    end_date = bal_row.get("end_date", "N/A")
                    # 匹配 income 行
                    inc_row = inc_annual[inc_annual["end_date"] == end_date]
                    if inc_row.empty:
                        result += f"{end_date:<12}{'N/A':>12}{'N/A':>12}{'N/A':>12}\n"
                        continue
                    inc_row = inc_row.iloc[0]

                    revenue = inc_row.get("total_revenue") or inc_row.get("revenue")
                    op_cost = inc_row.get("oper_cost") or inc_row.get("营业支出")
                    total_assets = bal_row.get("total_assets")
                    ar = bal_row.get("accounts_receivable")
                    inv = bal_row.get("inventories")

                    ar_turnover = FC.safe_divide(revenue, ar) if revenue and ar else None
                    inv_turnover = FC.safe_divide(op_cost, inv) if op_cost and inv else None
                    ta_turnover = FC.safe_divide(revenue, total_assets) if revenue and total_assets else None

                    result += (
                        f"{end_date:<12}"
                        f"{FC.format_value(ar_turnover, 2):>12}"
                        f"{FC.format_value(inv_turnover, 2):>12}"
                        f"{FC.format_value(ta_turnover, 2):>12}\n"
                    )

                result += "\n  ⚠ 以上数据从利润表和资产负债表估算，可能与专业指标有偏差\n"
            else:
                result += "  ❌ 无法计算营运能力指标：缺少资产负债表或利润表数据\n"

        result += RF.footer()
        return result

    def analyze_solvency(self) -> str:
        """偿债能力分析（依赖 balance，通常可用）"""
        result = RF.header("偿债能力分析报告")

        df_balance, _ = self._fetch_data("balance")
        if df_balance is None or df_balance.empty:
            return result + "❌ 未获取到资产负债表数据"

        annual = df_balance[df_balance["end_date"].str.endswith("1231")].head(5)
        if annual.empty:
            annual = df_balance.head(5)

        result += RF.section("短期偿债能力")
        result += f"{'报告期':<12}{'流动比率':>12}{'速动比率':>12}{'现金比率':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for _, row in annual.iterrows():
            end_date = row.get("end_date", "N/A")
            ca = row.get("total_cur_assets")
            cl = row.get("total_cur_liab")
            inv = row.get("inventories")
            cash = row.get("money_cap")
            cr = FC.safe_divide(ca, cl)
            qa = (ca - inv) if ca and inv else ca
            qr = FC.safe_divide(qa, cl)
            cash_r = FC.safe_divide(cash, cl)
            result += (
                f"{end_date:<12}"
                f"{FC.format_value(cr, 2):>12}"
                f"{FC.format_value(qr, 2):>12}"
                f"{FC.format_value(cash_r, 2):>12}\n"
            )

        result += "\n"
        result += RF.section("长期偿债能力")
        result += f"{'报告期':<12}{'资产负债率':>12}{'产权比率':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for _, row in annual.iterrows():
            end_date = row.get("end_date", "N/A")
            total_assets = row.get("total_assets")
            total_liab = row.get("total_liab")
            equity = row.get("total_hldr_eqy_exc_min_int") or row.get("total_equity")
            dr = FC.safe_divide(total_liab, total_assets)
            if dr is not None:
                dr *= 100  # 转换为百分比
            de = FC.safe_divide(total_liab, equity)
            result += (
                f"{end_date:<12}"
                f"{FC.format_percentage(dr):>12}"
                f"{FC.format_value(de, 2):>12}\n"
            )

        result += RF.footer()
        return result

    def analyze_growth_ability(self) -> str:
        """成长能力分析（依赖 income，通常可用）"""
        result = RF.header("成长能力分析报告")

        df_income, _ = self._fetch_data("income")
        if df_income is None or df_income.empty:
            return result + "❌ 未获取到利润表数据"

        annual = df_income[df_income["end_date"].str.endswith("1231")].head(5)
        if annual.empty:
            annual = df_income.head(5)

        # 营收增长
        result += RF.section("营收增长分析")
        result += f"{'报告期':<12}{'营业收入':>14}{'同比增长':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        revenues = []
        for _, row in annual.iterrows():
            revenues.append(row.get("total_revenue") or row.get("revenue"))

        for i, (_, row) in enumerate(annual.iterrows()):
            end_date = row.get("end_date", "N/A")
            rev = revenues[i]
            rev_str = FC.format_value(rev / 1e8, 2, "亿") if rev else "N/A"
            yoy = None
            if i < len(revenues) - 1 and revenues[i] and revenues[i + 1]:
                yoy = (revenues[i] - revenues[i + 1]) / abs(revenues[i + 1]) * 100
            result += f"{end_date:<12}{rev_str:>14}{FC.format_change(yoy):>12}\n"

        result += "\n"
        result += RF.section("净利润增长分析")
        result += f"{'报告期':<12}{'净利润':>14}{'同比增长':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        profits = []
        for _, row in annual.iterrows():
            profits.append(row.get("net_profit"))

        for i, (_, row) in enumerate(annual.iterrows()):
            end_date = row.get("end_date", "N/A")
            p = profits[i]
            p_str = FC.format_value(p / 1e8, 2, "亿") if p else "N/A"
            yoy = None
            if i < len(profits) - 1 and profits[i] and profits[i + 1]:
                yoy = (profits[i] - profits[i + 1]) / abs(profits[i + 1]) * 100
            result += f"{end_date:<12}{p_str:>14}{FC.format_change(yoy):>12}\n"

        result += "\n"
        result += RF.section("复合增长率")
        if len(revenues) >= 2 and revenues[0] and revenues[-1]:
            cagr = FC.calc_cagr(revenues, len(revenues) - 1)
            if cagr is not None:
                result += f"  营收CAGR({len(revenues)-1}年): {cagr:.2f}%\n"
        if len(profits) >= 2 and profits[0] and profits[-1]:
            cagr = FC.calc_cagr(profits, len(profits) - 1)
            if cagr is not None:
                result += f"  净利润CAGR({len(profits)-1}年): {cagr:.2f}%\n"

        result += RF.footer()
        return result
