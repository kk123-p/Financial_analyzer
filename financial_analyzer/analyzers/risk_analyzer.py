"""
风险分析调用层 - 连接 RiskAssessmentModel 与 UI
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..risk.assessment import RiskAssessmentModel
from ..config import SEPARATOR_LIGHT
from ..logging_config import get_logger

logger = get_logger(__name__)


class RiskAnalyzer(BaseAnalyzer):
    """风险分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager):
        super().__init__(data, stock_code, data_adapter, cache_manager)
        self._risk_model = None

    def _get_risk_model(self) -> RiskAssessmentModel:
        """获取风险评估模型（懒加载）"""
        if self._risk_model is None:
            industry = "default"
            basic = self.data.get("basic")
            if basic is not None and not basic.empty:
                industry = basic.iloc[0].get("industry", "default")
            self._risk_model = RiskAssessmentModel(industry=industry)
        return self._risk_model

    def _get_latest_financial_data(self) -> dict:
        """获取最新财务数据用于风险评估
        降级策略：financial 不可用时从 income+balance 手动计算"""
        data = {}
        df_fin, _ = self._fetch_data("financial")
        df_balance, _ = self._fetch_data("balance")
        df_income, _ = self._fetch_data("income")
        df_cashflow, _ = self._fetch_data("cashflow")

        if df_balance is not None and not df_balance.empty:
            latest = df_balance.iloc[0]
            data["current_assets"] = latest.get("total_cur_assets")
            data["current_liab"] = latest.get("total_cur_liab")
            data["inventory"] = latest.get("inventories")
            data["total_assets"] = latest.get("total_assets")
            data["total_liab"] = latest.get("total_liab")
            data["equity"] = latest.get("total_hldr_eqy_exc_min_int") or latest.get("total_equity")
            data["cash"] = latest.get("money_cap")

        if df_income is not None and not df_income.empty:
            latest = df_income.iloc[0]
            data["revenue"] = latest.get("total_revenue") or latest.get("revenue")
            data["net_profit"] = latest.get("net_profit")
            data["deduct_profit"] = latest.get("n_income_attr_p")
            data["op_cost"] = latest.get("oper_cost") or latest.get("营业支出")
            data["fin_exp"] = latest.get("fin_exp")

        if df_cashflow is not None and not df_cashflow.empty:
            latest = df_cashflow.iloc[0]
            data["op_cashflow"] = latest.get("n_cashflow_act")

        # 从 income 计算毛利率和净利率（不依赖 financial）
        if data.get("revenue") and data["revenue"] > 0:
            if data.get("op_cost"):
                data["gross_margin"] = (data["revenue"] - data["op_cost"]) / data["revenue"] * 100
            if data.get("net_profit"):
                data["net_margin"] = data["net_profit"] / data["revenue"] * 100

        # 从 financial 获取周转率（如果可用）
        if df_fin is not None and not df_fin.empty:
            latest = df_fin.iloc[0]
            data["ar_turnover"] = latest.get("ar_turnover")
            data["inv_turnover"] = latest.get("inv_turnover")
            data["ar_days"] = latest.get("ar_turnover_days")
            data["inv_days"] = latest.get("inv_turnover_days")

        return data

    def analyze_solvency_risk(self) -> str:
        """偿债风险评估"""
        result = RF.header("偿债风险评估报告")
        model = self._get_risk_model()
        fin_data = self._get_latest_financial_data()

        cr = FC.safe_divide(fin_data.get("current_assets"), fin_data.get("current_liab"))
        qa = (fin_data.get("current_assets", 0) - fin_data.get("inventory", 0)) if fin_data.get("current_assets") else None
        qr = FC.safe_divide(qa, fin_data.get("current_liab"))
        dr = FC.safe_divide(fin_data.get("total_liab"), fin_data.get("total_assets"))
        if dr is not None:
            dr *= 100  # 转换为百分比
        ic = None
        if fin_data.get("fin_exp") and fin_data.get("fin_exp") > 0:
            op_profit = (fin_data.get("revenue", 0) - fin_data.get("op_cost", 0) - fin_data.get("fin_exp", 0))
            ic = FC.safe_divide(op_profit, fin_data.get("fin_exp"))

        assessment = model.assess_solvency_risk(cr, qr, None, dr, ic)

        result += f"综合评分: {assessment['score']}/100\n\n"

        if assessment["details"]:
            result += RF.section("评估详情")
            for d in assessment["details"]:
                result += f"  ✓ {d}\n"

        if assessment["warnings"]:
            result += "\n" + RF.section("风险预警")
            for w in assessment["warnings"]:
                result += f"  {w}\n"

        result += RF.footer()
        return result

    def analyze_profit_quality_risk(self) -> str:
        """盈利质量风险评估"""
        result = RF.header("盈利质量风险评估报告")
        model = self._get_risk_model()
        fin_data = self._get_latest_financial_data()

        assessment = model.assess_profit_quality_risk(
            fin_data.get("net_profit"),
            fin_data.get("deduct_profit"),
            fin_data.get("op_cashflow"),
            fin_data.get("gross_margin"),
            fin_data.get("net_margin"),
        )

        result += f"综合评分: {assessment['score']}/100\n\n"

        if assessment["details"]:
            result += RF.section("评估详情")
            for d in assessment["details"]:
                result += f"  ✓ {d}\n"

        if assessment["warnings"]:
            result += "\n" + RF.section("风险预警")
            for w in assessment["warnings"]:
                result += f"  {w}\n"

        result += RF.footer()
        return result

    def analyze_operation_risk(self) -> str:
        """营运风险评估"""
        result = RF.header("营运风险评估报告")
        model = self._get_risk_model()
        fin_data = self._get_latest_financial_data()

        assessment = model.assess_operation_risk(
            fin_data.get("ar_turnover"),
            fin_data.get("inv_turnover"),
            fin_data.get("ar_days"),
            fin_data.get("inv_days"),
        )

        result += f"综合评分: {assessment['score']}/100\n\n"

        if assessment["details"]:
            result += RF.section("评估详情")
            for d in assessment["details"]:
                result += f"  ✓ {d}\n"

        if assessment["warnings"]:
            result += "\n" + RF.section("风险预警")
            for w in assessment["warnings"]:
                result += f"  {w}\n"

        result += RF.footer()
        return result

    def generate_risk_warning_report(self) -> str:
        """综合风险预警报告"""
        result = RF.header("综合风险预警报告")
        model = self._get_risk_model()

        df_balance, _ = self._fetch_data("balance")
        df_income, _ = self._fetch_data("income")
        df_cashflow, _ = self._fetch_data("cashflow")
        df_fin, _ = self._fetch_data("financial")

        # 预警信号
        warnings, warning_score = model.check_warning_signals(
            df_balance, df_income, df_cashflow, df_fin
        )

        # 偿债风险
        fin_data = self._get_latest_financial_data()
        cr = FC.safe_divide(fin_data.get("current_assets"), fin_data.get("current_liab"))
        qa = (fin_data.get("current_assets", 0) - fin_data.get("inventory", 0)) if fin_data.get("current_assets") else None
        qr = FC.safe_divide(qa, fin_data.get("current_liab"))
        dr = FC.safe_divide(fin_data.get("total_liab"), fin_data.get("total_assets"))
        if dr is not None:
            dr *= 100  # 转换为百分比
        solvency = model.assess_solvency_risk(cr, qr, None, dr, None)

        # 盈利质量
        profit_quality = model.assess_profit_quality_risk(
            fin_data.get("net_profit"), fin_data.get("deduct_profit"),
            fin_data.get("op_cashflow"), fin_data.get("gross_margin"),
            fin_data.get("net_margin"),
        )

        # 营运风险
        operation = model.assess_operation_risk(
            fin_data.get("ar_turnover"), fin_data.get("inv_turnover"),
            fin_data.get("ar_days"), fin_data.get("inv_days"),
        )

        total_score = model.calculate_total_risk_score(solvency, profit_quality, operation, warning_score)
        risk_level, risk_icon = model.get_risk_level(total_score)

        result += f"  {risk_icon} 综合风险评分: {total_score}/100 - {risk_level}\n\n"

        # 评分标准
        result += RF.section("评分权重")
        result += "  偿债风险 30% | 盈利质量 30% | 营运风险 20% | 预警信号 20%\n"
        result += "  综合评分 = 偿债×0.3 + 盈利×0.3 + 营运×0.2 + 预警×0.2\n\n"

        # 各维度评分
        result += RF.section("各维度评分")
        result += f"  偿债风险: {solvency['score']}/100 (权重30%)\n"
        for d in solvency.get('details', []):
            result += f"    {d}\n"
        for w in solvency.get('warnings', []):
            result += f"    {w}\n"

        result += f"  盈利质量: {profit_quality['score']}/100 (权重30%)\n"
        for d in profit_quality.get('details', []):
            result += f"    {d}\n"
        for w in profit_quality.get('warnings', []):
            result += f"    {w}\n"

        result += f"  营运风险: {operation['score']}/100 (权重20%)\n"
        for d in operation.get('details', []):
            result += f"    {d}\n"
        for w in operation.get('warnings', []):
            result += f"    {w}\n"

        result += f"  预警信号: {warning_score}/100 (权重20%)\n"

        # 预警信号
        if warnings:
            result += "\n" + RF.section("风险预警信号")
            for w in warnings:
                result += f"  {w}\n"

        # 建议
        result += "\n" + RF.section("投资建议")
        if total_score >= 80:
            result += "  公司财务状况良好，风险较低。\n"
        elif total_score >= 60:
            result += "  公司存在一定风险，建议关注相关预警信号。\n"
        elif total_score >= 40:
            result += "  公司风险较高，建议谨慎投资。\n"
        else:
            result += "  公司风险极高，建议回避或深入调研。\n"

        result += RF.footer()
        return result
