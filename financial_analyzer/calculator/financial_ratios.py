"""
财务比率计算器 - 五类核心财务比率
偿债能力、营运能力、盈利能力、发展能力、市场价值
"""
from ..logging_config import get_logger

logger = get_logger(__name__)


class FinancialRatiosCalculator:
    """财务比率计算器"""

    @staticmethod
    def _safe_div(a, b, pct=False):
        """安全除法"""
        if a is None or b is None or b == 0:
            return None
        try:
            v = a / b
            return v * 100 if pct else v
        except (TypeError, ZeroDivisionError):
            return None

    @staticmethod
    def _avg(cur, prev):
        """平均值（期初+期末）/2"""
        if cur is not None and prev is not None:
            return (cur + prev) / 2
        return cur

    # ========================================================================
    # 一、偿债能力比率
    # ========================================================================

    @staticmethod
    def solvency_ratios(current: dict, previous: dict = None) -> dict:
        """
        偿债能力比率

        Args:
            current: 最新期数据 dict（来自 _build_periods_data）
            previous: 上一期数据（用于计算平均值）

        Returns:
            dict with all solvency ratios
        """
        r = {}

        ca = current.get("current_assets")        # 流动资产
        cl = current.get("current_liab")           # 流动负债
        inv = current.get("inventory") or 0        # 存货
        cash = current.get("cash") or current.get("money_cap") or 0  # 货币资金
        trad = current.get("trad_asset") or 0      # 交易性金融资产
        ta = current.get("total_assets")            # 总资产
        tl = current.get("total_liab")              # 总负债
        eq = current.get("equity")                  # 所有者权益
        ebit = current.get("ebit") or current.get("operate_profit")  # 息税前利润
        fin_exp = current.get("interest_expense") or current.get("fin_exp")  # 利息费用

        # 短期偿债能力
        r["流动比率"] = FinancialRatiosCalculator._safe_div(ca, cl)
        r["速动比率"] = FinancialRatiosCalculator._safe_div(
            (ca or 0) - inv, cl) if ca is not None and cl is not None else None
        r["现金比率"] = FinancialRatiosCalculator._safe_div(
            cash + trad, cl) if cl is not None and cl != 0 else None

        # 长期偿债能力
        r["资产负债率"] = FinancialRatiosCalculator._safe_div(tl, ta, pct=True)
        r["产权比率"] = FinancialRatiosCalculator._safe_div(tl, eq)
        r["利息保障倍数"] = FinancialRatiosCalculator._safe_div(ebit, fin_exp)

        return r

    # ========================================================================
    # 二、营运能力比率
    # ========================================================================

    @staticmethod
    def operational_ratios(current: dict, previous: dict = None) -> dict:
        """
        营运能力比率（需要平均值）

        Args:
            current: 最新期数据
            previous: 上一期数据
        """
        r = {}
        F = FinancialRatiosCalculator

        rev = current.get("revenue")           # 营业收入
        cost = current.get("op_cost") or current.get("oper_cost")  # 营业成本

        # 应收账款
        ar_cur = current.get("accounts_receivable")
        ar_prev = previous.get("accounts_receivable") if previous else None
        ar_avg = F._avg(ar_cur, ar_prev)

        ar_turnover = F._safe_div(rev, ar_avg)
        r["应收账款周转率"] = ar_turnover
        r["应收账款周转天数"] = F._safe_div(360, ar_turnover)

        # 存货
        inv_cur = current.get("inventory")
        inv_prev = previous.get("inventory") if previous else None
        inv_avg = F._avg(inv_cur, inv_prev)

        inv_turnover = F._safe_div(cost, inv_avg)
        r["存货周转率"] = inv_turnover
        r["存货周转天数"] = F._safe_div(360, inv_turnover)

        # 总资产
        ta_cur = current.get("total_assets")
        ta_prev = previous.get("total_assets") if previous else None
        ta_avg = F._avg(ta_cur, ta_prev)

        r["总资产周转率"] = F._safe_div(rev, ta_avg)

        return r

    # ========================================================================
    # 三、盈利能力比率
    # ========================================================================

    @staticmethod
    def profitability_ratios(current: dict, previous: dict = None) -> dict:
        """
        盈利能力比率
        """
        r = {}
        F = FinancialRatiosCalculator

        rev = current.get("revenue")
        cost = current.get("op_cost") or current.get("oper_cost")
        np = current.get("net_profit")
        ta = current.get("total_assets")
        eq = current.get("equity")
        total_profit = current.get("pre_tax_profit") or current.get("total_profit")
        total_exp = (current.get("op_cost") or 0) + (current.get("sell_exp") or 0) + \
                    (current.get("admin_exp") or 0) + (current.get("fin_exp") or 0) + \
                    (current.get("rd_expense") or 0)

        # 销售毛利率
        if rev and cost and rev > 0:
            r["销售毛利率"] = (rev - cost) / rev * 100
        else:
            r["销售毛利率"] = None

        # 销售净利率
        r["销售净利率"] = F._safe_div(np, rev, pct=True)

        # ROA（用平均总资产）
        ta_prev = previous.get("total_assets") if previous else None
        ta_avg = F._avg(ta, ta_prev)
        r["总资产报酬率(ROA)"] = F._safe_div(np, ta_avg, pct=True)

        # ROE（用平均净资产）
        eq_prev = previous.get("equity") if previous else None
        eq_avg = F._avg(eq, eq_prev)
        r["净资产收益率(ROE)"] = F._safe_div(np, eq_avg, pct=True)

        # 成本费用利润率
        r["成本费用利润率"] = F._safe_div(total_profit, total_exp, pct=True) \
            if total_exp and total_exp != 0 else None

        return r

    # ========================================================================
    # 四、发展能力比率
    # ========================================================================

    @staticmethod
    def growth_ratios(current: dict, previous: dict = None) -> dict:
        """
        发展能力比率（需要上期数据）
        """
        r = {}
        F = FinancialRatiosCalculator

        if previous is None:
            return {
                "营业收入增长率": None,
                "净利润增长率": None,
                "总资产增长率": None,
            }

        # 营收增长率
        rev_cur = current.get("revenue")
        rev_prev = previous.get("revenue")
        r["营业收入增长率"] = F._safe_div(
            (rev_cur or 0) - (rev_prev or 0), abs(rev_prev or 1), pct=True) \
            if rev_prev and rev_prev != 0 else None

        # 净利润增长率
        np_cur = current.get("net_profit")
        np_prev = previous.get("net_profit")
        if np_prev and np_prev != 0:
            r["净利润增长率"] = ((np_cur or 0) - np_prev) / abs(np_prev) * 100
        else:
            r["净利润增长率"] = None

        # 总资产增长率
        ta_cur = current.get("total_assets")
        ta_prev = previous.get("total_assets")
        r["总资产增长率"] = F._safe_div(
            (ta_cur or 0) - (ta_prev or 0), abs(ta_prev or 1), pct=True) \
            if ta_prev and ta_prev != 0 else None

        return r

    # ========================================================================
    # 五、市场价值比率
    # ========================================================================

    @staticmethod
    def market_ratios(current: dict, basic_info: dict) -> dict:
        """
        市场价值比率

        Args:
            current: 最新期财务数据
            basic_info: 来自 _get_basic_info() 的行情数据（pe, pb, shares, current_price 等）
        """
        r = {}
        F = FinancialRatiosCalculator

        np = current.get("net_profit")
        shares = basic_info.get("shares") or current.get("shares")
        price = basic_info.get("current_price")
        pe = basic_info.get("pe")
        pb = basic_info.get("pb")
        eq = current.get("equity")

        # 每股收益 EPS
        r["每股收益(EPS)"] = F._safe_div(np, shares)

        # 市盈率 P/E
        r["市盈率(P/E)"] = pe

        # 市净率 P/B
        r["市净率(P/B)"] = pb

        # 每股净资产
        r["每股净资产"] = F._safe_div(eq, shares)

        # 股利支付率（需要分红数据，从现金流取）
        div_paid = current.get("div_paid")  # 分配股利支付的现金
        r["股利支付率"] = F._safe_div(div_paid, np, pct=True)

        return r

    # ========================================================================
    # 综合计算
    # ========================================================================

    @staticmethod
    def calculate_all(current: dict, previous: dict = None,
                      basic_info: dict = None) -> dict:
        """
        计算全部五类财务比率

        Args:
            current: 最新期数据
            previous: 上一期数据（用于增长率和平均值）
            basic_info: 行情基本信息

        Returns:
            {"偿债能力": {...}, "营运能力": {...}, "盈利能力": {...},
             "发展能力": {...}, "市场价值": {...}}
        """
        if basic_info is None:
            basic_info = {}

        return {
            "偿债能力": FinancialRatiosCalculator.solvency_ratios(current, previous),
            "营运能力": FinancialRatiosCalculator.operational_ratios(current, previous),
            "盈利能力": FinancialRatiosCalculator.profitability_ratios(current, previous),
            "发展能力": FinancialRatiosCalculator.growth_ratios(current, previous),
            "市场价值": FinancialRatiosCalculator.market_ratios(current, basic_info),
        }
