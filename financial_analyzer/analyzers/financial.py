"""
财务报表分析器 - 利润表、资产负债表、现金流量表
修复 #6: analyze_income_statement 中 i 变量未定义的 NameError
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import SEPARATOR_HEAVY, SEPARATOR_LIGHT
from ..logging_config import get_logger
import pandas as pd

logger = get_logger(__name__)


class FinancialStatementAnalyzer(BaseAnalyzer):
    """财务报表分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def analyze_income_statement(self) -> str:
        """利润表深度分析（已修复 NameError）"""
        df_income, error = self._fetch_data("income")

        result = RF.header("利润表深度分析报告")

        if error or df_income is None or df_income.empty:
            return result + f"❌ {error or '未获取到利润表数据'}\n\n提示：利润表数据需要Tushare积分权限。"

        basic_info = self.data.get("basic")
        if basic_info is not None and not basic_info.empty:
            info = basic_info.iloc[0]
            result += f"【股票信息】{info.get('name', 'N/A')} ({info.get('ts_code', 'N/A')})\n\n"

        annual_df = df_income[df_income["end_date"].str.endswith("1231")].head(5)
        if annual_df.empty:
            annual_df = df_income.head(5)

        # 营收分析
        result += RF.section("营业收入分析(近5年年报)")
        result += f"{'报告期':<12}{'营业收入':>14}{'同比增长':>12}{'营业成本':>14}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        revenues = []
        for _, row in annual_df.iterrows():
            end_date = row.get("end_date", "N/A")
            revenue = row.get("total_revenue") or row.get("revenue")
            op_cost = row.get("oper_cost") or row.get("营业支出")
            revenues.append(revenue)

            rev_str = FC.format_value(revenue / 1e8, 2, "亿") if revenue else "N/A"
            cost_str = FC.format_value(op_cost / 1e8, 2, "亿") if op_cost else "N/A"

            yoy = None
            if len(revenues) > 1 and revenues[-2] and revenues[-2] > 0:
                yoy = (revenue - revenues[-2]) / revenues[-2] * 100

            result += f"{end_date:<12}{rev_str:>14}{FC.format_change(yoy):>12}{cost_str:>14}\n"

        result += "\n"

        # 毛利率分析
        result += RF.section("毛利率分析")
        result += f"{'报告期':<12}{'毛利率':>12}{'变化':>12}{'评价':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        gross_margins = []
        for _, row in annual_df.iterrows():
            revenue = row.get("total_revenue") or row.get("revenue")
            op_cost = row.get("oper_cost") or row.get("营业支出")
            if revenue and op_cost and revenue > 0:
                gross_margins.append((revenue - op_cost) / revenue * 100)
            else:
                gross_margins.append(None)

        for i, (_, row) in enumerate(annual_df.iterrows()):
            end_date = row.get("end_date", "N/A")
            gm = gross_margins[i]
            gm_str = FC.format_percentage(gm)

            change = None
            if i < len(gross_margins) - 1 and gross_margins[i] and gross_margins[i + 1]:
                change = gross_margins[i] - gross_margins[i + 1]

            evaluation = "N/A"
            if gm:
                evaluation = "优秀" if gm > 40 else "良好" if gm > 20 else "一般"

            result += f"{end_date:<12}{gm_str:>12}{FC.format_change(change):>12}{evaluation:>12}\n"

        result += "\n"

        # 净利润分析（修复 #6: 使用 enumerate 获取正确的索引）
        result += RF.section("净利润分析")
        result += f"{'报告期':<12}{'净利润':>14}{'同比增长':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        net_profits = []
        for _, row in annual_df.iterrows():
            net_profits.append(row.get("net_profit"))

        for i, (_, row) in enumerate(annual_df.iterrows()):
            end_date = row.get("end_date", "N/A")
            np_val = net_profits[i]
            np_str = FC.format_value(np_val / 1e8, 2, "亿") if np_val else "N/A"

            # 修复: 使用正确的索引 i 和 i+1 进行同比计算
            yoy = None
            if i < len(net_profits) - 1 and net_profits[i] and net_profits[i + 1]:
                yoy = (net_profits[i] - net_profits[i + 1]) / abs(net_profits[i + 1]) * 100

            result += f"{end_date:<12}{np_str:>14}{FC.format_change(yoy):>12}\n"

        result += "\n"

        # 期间费用分析
        result += RF.section("期间费用分析(最新年报)")
        if not annual_df.empty:
            latest = annual_df.iloc[0]
            revenue = latest.get("total_revenue") or latest.get("revenue")
            if revenue and revenue > 0:
                result += f"  营业收入: {revenue / 1e8:.2f} 亿元\n\n"
                # 通用费用项 + 银行特有费用项
                expense_items = [
                    ("销售费用", "sell_exp"), ("管理费用", "admin_exp"),
                    ("业务及管理费用", "admin_exp"),  # 银行
                    ("财务费用", "fin_exp"), ("研发费用", "rd_exp"),
                    ("信用减值损失", "credit_impairment_loss"),  # 银行
                    ("资产减值损失", "asset_impairment_loss"),
                ]
                shown_keys = set()
                for label, key in expense_items:
                    if key in shown_keys:
                        continue
                    val = latest.get(key)
                    if val and not pd.isna(val) and (key != "rd_exp" or val > 0):
                        result += f"  {label}: {val / 1e8:.2f} 亿元 (占营收 {val / revenue * 100:.2f}%)\n"
                        shown_keys.add(key)

        result += "\n"

        # 扣非净利润分析
        result += RF.section("扣非净利润分析")
        result += f"{'报告期':<12}{'净利润':>14}{'扣非净利润':>14}{'扣非占比':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for _, row in annual_df.iterrows():
            end_date = row.get("end_date", "N/A")
            net_profit = row.get("net_profit")
            deduct_profit = row.get("n_income_attr_p") or row.get("归属于母公司所有者的净利润")
            deduct_ratio = None
            if net_profit and deduct_profit and net_profit != 0:
                deduct_ratio = deduct_profit / net_profit * 100
            result += (
                f"{end_date:<12}"
                f"{FC.format_value(net_profit / 1e8, 2, '亿') if net_profit else 'N/A':>14}"
                f"{FC.format_value(deduct_profit / 1e8, 2, '亿') if deduct_profit else 'N/A':>14}"
                f"{FC.format_percentage(deduct_ratio):>12}\n"
            )

        result += "\n"

        # 分析结论
        result += RF.section("分析结论")
        if len(revenues) >= 2 and revenues[0] and revenues[-1]:
            rev_cagr = FC.calc_cagr(revenues, len(revenues) - 1)
            if rev_cagr is not None:
                if rev_cagr > 15:
                    result += f"  ✓ 营收复合增长率 {rev_cagr:.1f}%，增长强劲\n"
                elif rev_cagr > 5:
                    result += f"  ✓ 营收复合增长率 {rev_cagr:.1f}%，稳健增长\n"
                elif rev_cagr > 0:
                    result += f"  ⚠ 营收复合增长率 {rev_cagr:.1f}%，增长缓慢\n"
                else:
                    result += f"  ✗ 营收复合增长率 {rev_cagr:.1f}%，营收下滑\n"

        if gross_margins and gross_margins[0]:
            gm = gross_margins[0]
            if gm > 40:
                result += f"  ✓ 毛利率 {gm:.1f}%，产品竞争力强\n"
            elif gm > 20:
                result += f"  ○ 毛利率 {gm:.1f}%，处于正常水平\n"
            else:
                result += f"  ⚠ 毛利率 {gm:.1f}%，盈利空间有限\n"

        return result

    def analyze_balance_sheet(self) -> str:
        """资产负债表深度分析"""
        df_balance, error = self._fetch_data("balance")

        result = RF.header("资产负债表深度分析报告")

        if error or df_balance is None or df_balance.empty:
            return result + f"❌ {error or '未获取到资产负债表数据'}\n\n提示：资产负债表数据需要Tushare积分权限。"

        annual_df = df_balance[df_balance["end_date"].str.endswith("1231")].head(5)
        if annual_df.empty:
            annual_df = df_balance.head(5)

        # 资产结构
        result += RF.section("资产结构分析(近5年年报)")
        result += f"{'报告期':<12}{'总资产':>14}{'流动资产':>14}{'非流动资产':>14}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for _, row in annual_df.iterrows():
            end_date = row.get("end_date", "N/A")
            total_assets = row.get("total_assets")
            cur_assets = row.get("total_cur_assets")
            non_cur = (total_assets - cur_assets) if total_assets and cur_assets else None

            result += (
                f"{end_date:<12}"
                f"{FC.format_value(total_assets / 1e8, 2, '亿') if total_assets else 'N/A':>14}"
                f"{FC.format_value(cur_assets / 1e8, 2, '亿') if cur_assets else 'N/A':>14}"
                f"{FC.format_value(non_cur / 1e8, 2, '亿') if non_cur else 'N/A':>14}\n"
            )

        result += "\n"

        # 负债结构
        result += RF.section("负债结构分析")
        result += f"{'报告期':<12}{'总负债':>14}{'流动负债':>14}{'资产负债率':>12}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        for _, row in annual_df.iterrows():
            end_date = row.get("end_date", "N/A")
            total_liab = row.get("total_liab")
            cur_liab = row.get("total_cur_liab")
            total_assets = row.get("total_assets")
            debt_ratio = (total_liab / total_assets * 100) if total_liab and total_assets else None

            result += (
                f"{end_date:<12}"
                f"{FC.format_value(total_liab / 1e8, 2, '亿') if total_liab else 'N/A':>14}"
                f"{FC.format_value(cur_liab / 1e8, 2, '亿') if cur_liab else 'N/A':>14}"
                f"{FC.format_percentage(debt_ratio):>12}\n"
            )

        result += "\n"

        # 偿债能力
        result += RF.section("偿债能力指标")
        if not annual_df.empty:
            latest = annual_df.iloc[0]
            current_assets = latest.get("total_cur_assets")
            current_liab = latest.get("total_cur_liab")
            inventory = latest.get("inventories")
            total_assets = latest.get("total_assets")
            total_liab = latest.get("total_liab")

            cr = FC.safe_divide(current_assets, current_liab)
            qa = (current_assets - inventory) if current_assets and inventory else current_assets
            qr = FC.safe_divide(qa, current_liab)
            dr = FC.safe_divide(total_liab, total_assets)
            if dr is not None:
                dr *= 100  # 转换为百分比

            result += f"  流动比率: {FC.format_value(cr, 2)}\n"
            result += f"  速动比率: {FC.format_value(qr, 2)}\n"
            result += f"  资产负债率: {FC.format_percentage(dr)}\n"

            if cr and cr >= 2:
                result += "  ✓ 流动比率充足，短期偿债能力强\n"
            elif cr and cr >= 1:
                result += "  ○ 流动比率正常\n"
            elif cr:
                result += "  ⚠ 流动比率偏低，短期偿债压力大\n"

        result += RF.footer()
        return result

    def analyze_cashflow_statement(self) -> str:
        """现金流量表深度分析"""
        df_cashflow, error = self._fetch_data("cashflow")

        result = RF.header("现金流量表深度分析报告")

        if error or df_cashflow is None or df_cashflow.empty:
            return result + f"❌ {error or '未获取到现金流量表数据'}\n\n提示：现金流量表数据需要Tushare积分权限。"

        annual_df = df_cashflow[df_cashflow["end_date"].str.endswith("1231")].head(5)
        if annual_df.empty:
            annual_df = df_cashflow.head(5)

        # 三大现金流
        result += RF.section("三大现金流分析(近5年年报)")
        result += f"{'报告期':<12}{'经营活动':>14}{'投资活动':>14}{'筹资活动':>14}\n"
        result += f"{SEPARATOR_LIGHT}\n"

        op_cashflows = []
        for _, row in annual_df.iterrows():
            end_date = row.get("end_date", "N/A")
            op_cf = row.get("n_cashflow_act")
            inv_cf = row.get("n_cashflow_inv_act")
            fin_cf = row.get("n_cash_finance_act")
            op_cashflows.append(op_cf)

            result += (
                f"{end_date:<12}"
                f"{FC.format_value(op_cf / 1e8, 2, '亿') if op_cf else 'N/A':>14}"
                f"{FC.format_value(inv_cf / 1e8, 2, '亿') if inv_cf else 'N/A':>14}"
                f"{FC.format_value(fin_cf / 1e8, 2, '亿') if fin_cf else 'N/A':>14}\n"
            )

        result += "\n"

        # 现金流质量
        result += RF.section("现金流质量分析")
        if op_cashflows and op_cashflows[0]:
            op_cf = op_cashflows[0]
            if op_cf > 0:
                result += f"  ✓ 经营活动现金流为正 ({op_cf / 1e8:.2f} 亿)\n"
            else:
                result += f"  ⚠ 经营活动现金流为负 ({op_cf / 1e8:.2f} 亿)\n"

            # 自由现金流估算
            if not annual_df.empty:
                latest = annual_df.iloc[0]
                capex = latest.get("c_pay_acq_const_fiamt")
                if capex and op_cf:
                    fcf = op_cf - capex
                    result += f"  自由现金流(估算): {fcf / 1e8:.2f} 亿元\n"
                    if fcf > 0:
                        result += "  ✓ 自由现金流为正，公司有充足现金进行再投资\n"
                    else:
                        result += "  ⚠ 自由现金流为负，可能需要外部融资\n"

        result += RF.footer()
        return result
