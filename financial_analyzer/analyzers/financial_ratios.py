"""
财务比率分析模块 - 五大类财务比率计算
包含：偿债能力、营运能力、盈利能力、发展能力、市场价值比率
"""
import pandas as pd
import numpy as np
from ..logging_config import get_logger

logger = get_logger(__name__)


class FinancialRatioAnalyzer:
    """财务比率分析器 - 计算和评估各类财务指标"""

    def __init__(self, data: dict, stock_code: str = ""):
        self.data = data
        self.stock_code = stock_code
        self._ratios_cache = {}

    def analyze(self) -> dict:
        """执行完整的财务比率分析"""
        result = {
            "偿债能力": self.solvency_ratios(),
            "营运能力": self.efficiency_ratios(),
            "盈利能力": self.profitability_ratios(),
            "发展能力": self.growth_ratios(),
            "市场价值": self.market_value_ratios(),
            "综合评分": self._overall_score(),
        }
        self._ratios_cache = result
        return result

    # ========================================================================
    # 偿债能力比率
    # ========================================================================
    def solvency_ratios(self) -> dict:
        """计算偿债能力比率"""
        result = {"短期偿债": {}, "长期偿债": {}, "评级": ""}

        balance = self._get_balance_sheet()
        income = self._get_income_statement()
        if balance is None or income is None:
            result["评级"] = "数据不足"
            return result

        try:
            latest = balance.iloc[0] if len(balance) > 0 else {}
            latest_income = income.iloc[0] if len(income) > 0 else {}

            # 短期偿债能力
            current_assets = self._get_value(latest, ["total_current_assets", "total_cur_assets", "流动资产合计"])
            current_liab = self._get_value(latest, ["total_current_liab", "total_cur_liab", "流动负债合计"])
            inventory = self._get_value(latest, ["inventories", "存货"])
            cash = self._get_value(latest, ["money_cap", "货币资金"])
            tradable_assets = self._get_value(latest, ["tradable_financial_assets", "交易性金融资产"])

            if current_liab and current_liab > 0:
                # 流动比率
                if current_assets:
                    result["短期偿债"]["流动比率"] = round(current_assets / current_liab, 2)
                # 速动比率
                if current_assets and inventory:
                    result["短期偿债"]["速动比率"] = round((current_assets - inventory) / current_liab, 2)
                # 现金比率
                if cash:
                    cash_equiv = cash + (tradable_assets if tradable_assets else 0)
                    result["短期偿债"]["现金比率"] = round(cash_equiv / current_liab, 2)

            # 长期偿债能力
            total_assets = self._get_value(latest, ["total_assets", "资产总计"])
            total_liab = self._get_value(latest, ["total_liab", "负债合计"])
            total_equity = self._get_value(latest, ["total_equity", "股东权益合计"])
            interest_expense = self._get_value(latest_income, ["interest_expense", "fin_exp", "财务费用"])
            profit_before_interest = self._get_value(latest_income, [
                "operate_profit", "营业利润"
            ])

            if total_assets and total_assets > 0:
                if total_liab:
                    result["长期偿债"]["资产负债率"] = round(total_liab / total_assets * 100, 2)
                if total_equity and total_equity > 0 and total_liab:
                    result["长期偿债"]["产权比率"] = round(total_liab / total_equity, 2)

            if interest_expense and interest_expense > 0 and profit_before_interest:
                ebit = profit_before_interest + interest_expense
                result["长期偿债"]["利息保障倍数"] = round(ebit / interest_expense, 2)

            # 评级
            result["评级"] = self._rate_solvency(result)

        except Exception as e:
            logger.error(f"偿债能力计算异常: {e}")
            result["评级"] = "计算异常"

        return result

    # ========================================================================
    # 营运能力比率
    # ========================================================================
    def efficiency_ratios(self) -> dict:
        """计算营运能力比率"""
        result = {"指标": {}, "评级": ""}

        balance = self._get_balance_sheet()
        income = self._get_income_statement()
        if balance is None or income is None:
            result["评级"] = "数据不足"
            return result

        try:
            latest = balance.iloc[0]
            latest_income = income.iloc[0]

            revenue = self._get_value(latest_income, ["revenue", "营业收入"])
            cost = self._get_value(latest_income, ["operating_cost", "oper_cost", "营业成本"])
            total_assets = self._get_value(latest, ["total_assets", "资产总计"])

            # 应收账款
            ar = self._get_value(latest, ["accounts_receivable", "应收账款"])
            if revenue and ar and ar > 0:
                ar_turnover = revenue / ar
                result["指标"]["应收账款周转率"] = round(ar_turnover, 2)
                result["指标"]["应收账款周转天数"] = round(360 / ar_turnover, 1)

            # 存货
            inventory = self._get_value(latest, ["inventories", "存货"])
            if cost and inventory and inventory > 0:
                inv_turnover = cost / inventory
                result["指标"]["存货周转率"] = round(inv_turnover, 2)
                result["指标"]["存货周转天数"] = round(360 / inv_turnover, 1)

            # 总资产
            if revenue and total_assets and total_assets > 0:
                result["指标"]["总资产周转率"] = round(revenue / total_assets, 2)

            result["评级"] = self._rate_efficiency(result)

        except Exception as e:
            logger.error(f"营运能力计算异常: {e}")
            result["评级"] = "计算异常"

        return result

    # ========================================================================
    # 盈利能力比率
    # ========================================================================
    def profitability_ratios(self) -> dict:
        """计算盈利能力比率"""
        result = {"指标": {}, "杜邦拆解": {}, "评级": ""}

        income = self._get_income_statement()
        balance = self._get_balance_sheet()
        if income is None or balance is None:
            result["评级"] = "数据不足"
            return result

        try:
            latest = income.iloc[0]
            latest_bal = balance.iloc[0]

            revenue = self._get_value(latest, ["revenue", "营业收入"])
            cost = self._get_value(latest, ["operating_cost", "oper_cost", "营业成本"])
            net_profit = self._get_value(latest, ["net_profit", "净利润"])
            total_assets = self._get_value(latest_bal, ["total_assets", "资产总计"])
            total_equity = self._get_value(latest_bal, ["total_equity", "股东权益合计"])

            # 毛利率
            if revenue and revenue > 0 and cost is not None:
                result["指标"]["毛利率"] = round((revenue - cost) / revenue * 100, 2)

            # 净利率
            if revenue and revenue > 0 and net_profit is not None:
                result["指标"]["净利率"] = round(net_profit / revenue * 100, 2)

            # ROA
            if total_assets and total_assets > 0 and net_profit is not None:
                result["指标"]["ROA"] = round(net_profit / total_assets * 100, 2)

            # ROE
            if total_equity and total_equity > 0 and net_profit is not None:
                roe = net_profit / total_equity
                result["指标"]["ROE"] = round(roe * 100, 2)

                # 杜邦拆解
                if revenue and revenue > 0 and total_assets and total_assets > 0:
                    net_margin = net_profit / revenue
                    asset_turnover = revenue / total_assets
                    equity_multiplier = total_assets / total_equity if total_equity > 0 else 0
                    result["杜邦拆解"] = {
                        "销售净利率": round(net_margin * 100, 2),
                        "资产周转率": round(asset_turnover, 4),
                        "权益乘数": round(equity_multiplier, 2),
                        "ROE验证": round(net_margin * asset_turnover * equity_multiplier * 100, 2),
                    }

            result["评级"] = self._rate_profitability(result)

        except Exception as e:
            logger.error(f"盈利能力计算异常: {e}")
            result["评级"] = "计算异常"

        return result

    # ========================================================================
    # 发展能力比率
    # ========================================================================
    def growth_ratios(self) -> dict:
        """计算发展能力比率（需要多年数据）"""
        result = {"指标": {}, "评级": ""}

        income = self._get_income_statement()
        balance = self._get_balance_sheet()
        if income is None or len(income) < 2:
            result["评级"] = "数据不足（需要至少2年数据）"
            return result

        try:
            curr = income.iloc[0]
            prev = income.iloc[-2]

            revenue_c = self._get_value(curr, ["revenue", "营业收入"])
            revenue_p = self._get_value(prev, ["revenue", "营业收入"])
            np_c = self._get_value(curr, ["net_profit", "净利润"])
            np_p = self._get_value(prev, ["net_profit", "净利润"])

            # 营收增长率
            if revenue_p and revenue_p > 0 and revenue_c is not None:
                result["指标"]["营收增长率"] = round(
                    (revenue_c - revenue_p) / revenue_p * 100, 2)

            # 净利润增长率
            if np_p and np_p != 0 and np_c is not None:
                result["指标"]["净利润增长率"] = round(
                    (np_c - np_p) / abs(np_p) * 100, 2)

            # 总资产增长率
            if balance is not None and len(balance) >= 2:
                ta_c = self._get_value(balance.iloc[0], ["total_assets", "资产总计"])
                ta_p = self._get_value(balance.iloc[-2], ["total_assets", "资产总计"])
                if ta_p and ta_p > 0 and ta_c is not None:
                    result["指标"]["总资产增长率"] = round(
                        (ta_c - ta_p) / ta_p * 100, 2)

            # 三年CAGR（如果有足够数据）
            if len(income) >= 4:
                rev_old = self._get_value(income.iloc[-4], ["revenue", "营业收入"])
                if rev_old and rev_old > 0 and revenue_c and revenue_c > 0:
                    cagr = (revenue_c / rev_old) ** (1 / 3) - 1
                    result["指标"]["营收三年CAGR"] = round(cagr * 100, 2)

            result["评级"] = self._rate_growth(result)

        except Exception as e:
            logger.error(f"发展能力计算异常: {e}")
            result["评级"] = "计算异常"

        return result

    # ========================================================================
    # 市场价值比率
    # ========================================================================
    def market_value_ratios(self) -> dict:
        """计算市场价值比率"""
        result = {"指标": {}, "评级": ""}

        income = self._get_income_statement()
        balance = self._get_balance_sheet()
        if income is None or balance is None:
            result["评级"] = "数据不足"
            return result

        try:
            latest = income.iloc[0]
            latest_bal = balance.iloc[0]

            net_profit = self._get_value(latest, ["net_profit", "净利润"])
            total_equity = self._get_value(latest_bal, ["total_equity", "股东权益合计"])

            # 获取股价和股本信息
            basic = self.data.get("basic")
            if basic is not None and len(basic) > 0:
                latest_basic = basic.iloc[0]
                close = self._get_value(latest_basic, ["close", "收盘价"])
                total_share = self._get_value(latest_basic, [
                    "total_share", "总股本", "total_mv"
                ])

                if net_profit and total_share and total_share > 0:
                    # 注意：不同数据源的单位不同
                    # tushare: net_profit(元), total_share(万股) → EPS = net_profit / (total_share * 10000)
                    # 此处假设 net_profit 已归一化为元，total_share 已归一化为万股
                    eps = net_profit / (total_share * 10000)
                    result["指标"]["EPS"] = round(eps, 4)
                    if close and eps > 0:
                        result["指标"]["PE"] = round(close / eps, 2)

                if total_equity and total_share and total_share > 0:
                    # 注意：不同数据源的单位不同，此处假设同 EPS 的单位约定
                    bvps = total_equity / (total_share * 10000)
                    result["指标"]["每股净资产"] = round(bvps, 4)
                    if close and bvps > 0:
                        result["指标"]["PB"] = round(close / bvps, 2)

            result["评级"] = self._rate_market(result)

        except Exception as e:
            logger.error(f"市场价值计算异常: {e}")
            result["评级"] = "计算异常"

        return result

    # ========================================================================
    # 综合评分
    # ========================================================================
    def overall_score(self) -> dict:
        """综合评分（外部接口）"""
        return self._overall_score()

    def _overall_score(self) -> dict:
        """综合评分"""
        if not self._ratios_cache:
            return {"总分": 0, "评级": "未分析"}

        scores = {
            "偿债": self._score_from_rating(
                self._ratios_cache.get("偿债能力", {}).get("评级", "")),
            "营运": self._score_from_rating(
                self._ratios_cache.get("营运能力", {}).get("评级", "")),
            "盈利": self._score_from_rating(
                self._ratios_cache.get("盈利能力", {}).get("评级", "")),
            "成长": self._score_from_rating(
                self._ratios_cache.get("发展能力", {}).get("评级", "")),
            "市场": self._score_from_rating(
                self._ratios_cache.get("市场价值", {}).get("评级", "")),
        }

        total = sum(scores.values())
        max_score = len(scores) * 100
        pct = total / max_score * 100 if max_score > 0 else 0

        if pct >= 80:
            grade = "优秀"
        elif pct >= 60:
            grade = "良好"
        elif pct >= 40:
            grade = "一般"
        elif pct >= 20:
            grade = "较差"
        else:
            grade = "风险"

        return {
            "总分": round(total),
            "满分": max_score,
            "得分率": round(pct, 1),
            "各项": scores,
            "评级": grade,
        }

    # ========================================================================
    # 辅助方法
    # ========================================================================
    def _get_balance_sheet(self) -> pd.DataFrame | None:
        return self.data.get("balance")

    def _get_income_statement(self) -> pd.DataFrame | None:
        return self.data.get("income")

    def _get_value(self, row, keys: list):
        """从行数据中获取值，支持多个可能的列名"""
        if row is None:
            return None
        for key in keys:
            if key in row.index:
                val = row[key]
                if pd.notna(val):
                    return float(val)
        return None

    def _rate_solvency(self, data: dict) -> str:
        """偿债能力评级"""
        short = data.get("短期偿债", {})
        long_term = data.get("长期偿债", {})
        cr = short.get("流动比率", 0)
        dar = long_term.get("资产负债率", 50)
        if cr >= 2 and dar <= 60:
            return "优秀"
        elif cr >= 1.5 and dar <= 70:
            return "良好"
        elif cr >= 1 and dar <= 80:
            return "一般"
        else:
            return "风险"

    def _rate_efficiency(self, data: dict) -> str:
        """营运能力评级"""
        indicators = data.get("指标", {})
        tat = indicators.get("总资产周转率", 0)
        if tat >= 1:
            return "优秀"
        elif tat >= 0.5:
            return "良好"
        elif tat >= 0.3:
            return "一般"
        else:
            return "较差"

    def _rate_profitability(self, data: dict) -> str:
        """盈利能力评级"""
        indicators = data.get("指标", {})
        roe = indicators.get("ROE", 0)
        if roe >= 20:
            return "优秀"
        elif roe >= 15:
            return "良好"
        elif roe >= 10:
            return "一般"
        elif roe >= 0:
            return "较差"
        else:
            return "亏损"

    def _rate_growth(self, data: dict) -> str:
        """发展能力评级"""
        indicators = data.get("指标", {})
        rg = indicators.get("营收增长率", 0)
        if rg >= 30:
            return "高速增长"
        elif rg >= 15:
            return "快速增长"
        elif rg >= 5:
            return "稳定增长"
        elif rg >= 0:
            return "低增长"
        else:
            return "下滑"

    def _rate_market(self, data: dict) -> str:
        """市场价值评级"""
        indicators = data.get("指标", {})
        pe = indicators.get("PE", 0)
        if pe <= 0:
            return "亏损或数据不足"
        elif pe <= 15:
            return "低估"
        elif pe <= 25:
            return "合理"
        elif pe <= 40:
            return "偏高"
        else:
            return "高估"

    def _score_from_rating(self, rating: str) -> int:
        """评级转分数"""
        score_map = {
            "优秀": 90, "良好": 75, "一般": 55, "较差": 35, "风险": 20,
            "高速增长": 90, "快速增长": 75, "稳定增长": 55, "低增长": 35, "下滑": 20,
            "低估": 85, "合理": 65, "偏高": 40, "高估": 20,
            "亏损": 10, "亏损或数据不足": 10,
            "计算异常": 30, "数据不足": 30, "未分析": 0,
        }
        return score_map.get(rating, 50)
