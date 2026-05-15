"""
财务风险评估模型 - 支持多市场
"""
from ..logging_config import get_logger

logger = get_logger(__name__)


class RiskAssessmentModel:
    """财务风险评估模型"""

    INDUSTRY_THRESHOLDS = {
        "银行": {"debt_ratio_max": 95, "current_ratio_min": 0, "quick_ratio_min": 0},
        "房地产": {"debt_ratio_max": 80, "current_ratio_min": 1.2, "quick_ratio_min": 0.5},
        "制造业": {"debt_ratio_max": 70, "current_ratio_min": 1.5, "quick_ratio_min": 1.0},
        "科技": {"debt_ratio_max": 60, "current_ratio_min": 1.5, "quick_ratio_min": 1.0},
        "医药": {"debt_ratio_max": 60, "current_ratio_min": 1.5, "quick_ratio_min": 1.0},
        "消费": {"debt_ratio_max": 65, "current_ratio_min": 1.3, "quick_ratio_min": 0.8},
        "金融": {"debt_ratio_max": 90, "current_ratio_min": 0, "quick_ratio_min": 0},
        "能源": {"debt_ratio_max": 65, "current_ratio_min": 1.2, "quick_ratio_min": 0.8},
        "公用事业": {"debt_ratio_max": 70, "current_ratio_min": 1.0, "quick_ratio_min": 0.7},
        "default": {"debt_ratio_max": 70, "current_ratio_min": 1.5, "quick_ratio_min": 1.0},
    }

    RISK_WEIGHTS = {
        "solvency": 0.30,
        "profit_quality": 0.30,
        "operation": 0.20,
        "warning": 0.20,
    }

    def __init__(self, industry: str = "default", market: str = "CN"):
        self.industry = industry
        self.market = market
        self.thresholds = self.INDUSTRY_THRESHOLDS.get(
            industry, self.INDUSTRY_THRESHOLDS["default"]
        )
        if market == "US":
            self.thresholds = self.thresholds.copy()
            self.thresholds["debt_ratio_max"] = min(self.thresholds["debt_ratio_max"] + 10, 95)

    def assess_solvency_risk(self, current_ratio, quick_ratio, cash_ratio,
                             debt_ratio, interest_coverage) -> dict:
        """偿债风险评估"""
        result = {"score": 0, "max_score": 100, "details": [], "warnings": []}
        score = 0

        if current_ratio is not None:
            if current_ratio >= self.thresholds["current_ratio_min"] * 1.5:
                score += 25
                result["details"].append(f"流动比率({current_ratio:.2f})优秀，短期偿债能力强")
            elif current_ratio >= self.thresholds["current_ratio_min"]:
                score += 15
                result["details"].append(f"流动比率({current_ratio:.2f})正常，短期偿债能力一般")
            else:
                result["warnings"].append(f"⚠️ 流动比率({current_ratio:.2f})偏低，短期偿债压力大")

        if quick_ratio is not None:
            if quick_ratio >= self.thresholds["quick_ratio_min"] * 1.5:
                score += 25
                result["details"].append(f"速动比率({quick_ratio:.2f})优秀")
            elif quick_ratio >= self.thresholds["quick_ratio_min"]:
                score += 15
                result["details"].append(f"速动比率({quick_ratio:.2f})正常")
            else:
                result["warnings"].append(f"⚠️ 速动比率({quick_ratio:.2f})偏低")

        if debt_ratio is not None:
            if debt_ratio <= self.thresholds["debt_ratio_max"] * 0.7:
                score += 25
                result["details"].append(f"资产负债率({debt_ratio:.1f}%)较低，财务杠杆保守")
            elif debt_ratio <= self.thresholds["debt_ratio_max"]:
                score += 15
                result["details"].append(f"资产负债率({debt_ratio:.1f}%)处于正常范围")
            else:
                result["warnings"].append(f"⚠️ 资产负债率({debt_ratio:.1f}%)偏高，长期偿债压力大")

        if interest_coverage is not None:
            if interest_coverage >= 5:
                score += 25
                result["details"].append(f"利息保障倍数({interest_coverage:.1f})优秀")
            elif interest_coverage >= 2:
                score += 15
                result["details"].append(f"利息保障倍数({interest_coverage:.1f})正常")
            elif interest_coverage > 0:
                result["warnings"].append(f"⚠️ 利息保障倍数({interest_coverage:.1f})偏低")
            else:
                result["warnings"].append(f"🚨 利息保障倍数({interest_coverage:.1f})为负")

        result["score"] = score
        return result

    def assess_profit_quality_risk(self, net_profit, deduct_profit, op_cashflow,
                                   gross_margin, net_margin) -> dict:
        """盈利质量风险评估"""
        result = {"score": 0, "max_score": 100, "details": [], "warnings": []}
        score = 0

        if net_profit is not None and deduct_profit is not None and net_profit != 0:
            deduct_ratio = deduct_profit / net_profit * 100
            if deduct_ratio >= 90:
                score += 30
                result["details"].append(f"扣非净利润占比({deduct_ratio:.1f}%)高，盈利质量优秀")
            elif deduct_ratio >= 70:
                score += 20
                result["details"].append(f"扣非净利润占比({deduct_ratio:.1f}%)正常")
            elif deduct_ratio >= 50:
                score += 10
                result["warnings"].append(f"⚠️ 扣非净利润占比({deduct_ratio:.1f}%)偏低")
            else:
                result["warnings"].append(f"🚨 扣非净利润占比({deduct_ratio:.1f}%)过低")

        if op_cashflow is not None and net_profit is not None and net_profit > 0:
            cash_profit_ratio = op_cashflow / net_profit
            if cash_profit_ratio >= 1.2:
                score += 40
                result["details"].append(f"经营现金流/净利润({cash_profit_ratio:.2f})优秀")
            elif cash_profit_ratio >= 0.8:
                score += 25
                result["details"].append(f"经营现金流/净利润({cash_profit_ratio:.2f})正常")
            elif cash_profit_ratio > 0:
                score += 10
                result["warnings"].append(f"⚠️ 经营现金流/净利润({cash_profit_ratio:.2f})偏低")
            else:
                result["warnings"].append("🚨 经营现金流为负，利润质量存疑")

        if gross_margin is not None:
            if gross_margin >= 40:
                score += 15
                result["details"].append(f"毛利率({gross_margin:.1f}%)较高")
            elif gross_margin >= 20:
                score += 10
                result["details"].append(f"毛利率({gross_margin:.1f}%)正常")
            else:
                result["warnings"].append(f"⚠️ 毛利率({gross_margin:.1f}%)偏低")

        if net_margin is not None:
            if net_margin >= 15:
                score += 15
                result["details"].append(f"净利率({net_margin:.1f}%)优秀")
            elif net_margin >= 5:
                score += 10
                result["details"].append(f"净利率({net_margin:.1f}%)正常")
            elif net_margin > 0:
                score += 5
                result["warnings"].append(f"⚠️ 净利率({net_margin:.1f}%)偏低")
            else:
                result["warnings"].append("🚨 净利率为负，处于亏损状态")

        result["score"] = score
        return result

    def assess_operation_risk(self, ar_turnover, inv_turnover, ar_days, inv_days) -> dict:
        """营运风险评估"""
        result = {"score": 0, "max_score": 100, "details": [], "warnings": []}
        score = 0

        if ar_turnover is not None:
            if ar_turnover >= 10:
                score += 50
                result["details"].append(f"应收账款周转率({ar_turnover:.1f}次)优秀")
            elif ar_turnover >= 5:
                score += 35
                result["details"].append(f"应收账款周转率({ar_turnover:.1f}次)正常")
            elif ar_turnover >= 2:
                score += 20
                result["warnings"].append(f"⚠️ 应收账款周转率({ar_turnover:.1f}次)偏低")
            else:
                result["warnings"].append(f"🚨 应收账款周转率({ar_turnover:.1f}次)过低")
        elif ar_days is not None:
            if ar_days <= 30:
                score += 50
                result["details"].append(f"应收账款周转天数({ar_days:.0f}天)优秀")
            elif ar_days <= 60:
                score += 35
                result["details"].append(f"应收账款周转天数({ar_days:.0f}天)正常")
            elif ar_days <= 90:
                score += 20
                result["warnings"].append(f"⚠️ 应收账款周转天数({ar_days:.0f}天)偏长")
            else:
                result["warnings"].append(f"🚨 应收账款周转天数({ar_days:.0f}天)过长")

        if inv_turnover is not None:
            if inv_turnover >= 8:
                score += 50
                result["details"].append(f"存货周转率({inv_turnover:.1f}次)优秀")
            elif inv_turnover >= 4:
                score += 35
                result["details"].append(f"存货周转率({inv_turnover:.1f}次)正常")
            elif inv_turnover >= 2:
                score += 20
                result["warnings"].append(f"⚠️ 存货周转率({inv_turnover:.1f}次)偏低")
            else:
                result["warnings"].append(f"🚨 存货周转率({inv_turnover:.1f}次)过低")
        elif inv_days is not None:
            if inv_days <= 45:
                score += 50
                result["details"].append(f"存货周转天数({inv_days:.0f}天)优秀")
            elif inv_days <= 90:
                score += 35
                result["details"].append(f"存货周转天数({inv_days:.0f}天)正常")
            elif inv_days <= 180:
                score += 20
                result["warnings"].append(f"⚠️ 存货周转天数({inv_days:.0f}天)偏长")
            else:
                result["warnings"].append(f"🚨 存货周转天数({inv_days:.0f}天)过长")

        result["score"] = score
        return result

    def check_warning_signals(self, balance_df, income_df, cashflow_df, fina_df) -> tuple:
        """检查风险预警信号"""
        warnings = []
        warning_score = 100

        if balance_df is not None and not balance_df.empty:
            latest = balance_df.iloc[0]
            total_assets = latest.get("total_assets")
            total_liab = latest.get("total_liab")
            if total_assets and total_liab:
                debt_ratio = total_liab / total_assets * 100
                if debt_ratio > self.thresholds["debt_ratio_max"]:
                    warnings.append(f"🚨 资产负债率({debt_ratio:.1f}%)超过行业阈值")
                    warning_score -= 20

            from ..calculator.financial import FinancialCalculator
            current_ratio = FinancialCalculator.safe_divide(
                latest.get("total_cur_assets"), latest.get("total_cur_liab")
            )
            if current_ratio and current_ratio < self.thresholds["current_ratio_min"]:
                warnings.append(f"⚠️ 流动比率({current_ratio:.2f})低于行业阈值")
                warning_score -= 15

        if income_df is not None and not income_df.empty:
            latest = income_df.iloc[0]
            net_profit = latest.get("net_profit")
            if net_profit and net_profit < 0:
                warnings.append("🚨 净利润为负，公司处于亏损状态")
                warning_score -= 25
            revenue = latest.get("total_revenue")
            if revenue and revenue < 0:
                warnings.append("🚨 营业收入为负")
                warning_score -= 20

        if cashflow_df is not None and not cashflow_df.empty:
            latest = cashflow_df.iloc[0]
            op_cashflow = latest.get("n_cashflow_act")
            if op_cashflow and op_cashflow < 0:
                warnings.append("⚠️ 经营活动现金流为负")
                warning_score -= 15

        if fina_df is not None and not fina_df.empty:
            latest = fina_df.iloc[0]
            roe = latest.get("roe")
            if roe and roe < 5:
                warnings.append(f"⚠️ ROE({roe:.1f}%)偏低")
                warning_score -= 10

        return warnings, max(warning_score, 0)

    def calculate_total_risk_score(self, solvency_result, profit_quality_result,
                                   operation_result, warning_score) -> int:
        """计算综合风险评分"""
        total_score = 0
        if solvency_result:
            total_score += solvency_result["score"] * self.RISK_WEIGHTS["solvency"]
        if profit_quality_result:
            total_score += profit_quality_result["score"] * self.RISK_WEIGHTS["profit_quality"]
        if operation_result:
            total_score += operation_result["score"] * self.RISK_WEIGHTS["operation"]
        total_score += warning_score * self.RISK_WEIGHTS["warning"]
        return int(total_score)

    def get_risk_level(self, score: int) -> tuple[str, str]:
        """根据评分获取风险等级"""
        if score >= 80:
            return "低风险", "🟢"
        elif score >= 60:
            return "中风险", "🟡"
        elif score >= 40:
            return "较高风险", "🟠"
        else:
            return "高风险", "🔴"
