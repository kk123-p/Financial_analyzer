"""
资金面分析器 — 主力资金流向、融资融券、北向资金、大宗交易
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..logging_config import get_logger

logger = get_logger(__name__)


class CapitalFlowAnalyzer(BaseAnalyzer):
    """资金面分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter=None, cache_manager=None):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def _get_basic_info(self) -> dict:
        info = {}
        stock_basic = self.data.get("stock_basic")
        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            info["name"] = sb.get("name", "N/A")
        return info

    def analyze(self) -> str:
        """资金面综合分析"""
        result = RF.header("资金面分析")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        result += self._analyze_moneyflow()
        result += self._analyze_margin()
        result += self._analyze_hk_hold()
        result += self._analyze_block_trade()
        result += self._capital_flow_score()

        result += RF.footer()
        return result

    def _analyze_moneyflow(self) -> str:
        result = RF.section("主力资金流向")
        df = self.data.get("moneyflow")
        if df is None or df.empty:
            return result + "  未获取到资金流向数据\n\n"

        df = df.sort_values("trade_date").reset_index(drop=True)
        recent = df.tail(20)

        net_amounts = []
        for _, row in recent.iterrows():
            buy_elg = float(row.get("buy_elg_amount", 0) or 0)
            sell_elg = float(row.get("sell_elg_amount", 0) or 0)
            buy_lg = float(row.get("buy_lg_amount", 0) or 0)
            sell_lg = float(row.get("sell_lg_amount", 0) or 0)
            net_amounts.append((buy_elg + buy_lg) - (sell_elg + sell_lg))

        cum_net = sum(net_amounts)
        recent_5 = net_amounts[-5:] if len(net_amounts) >= 5 else net_amounts
        avg_daily_net = sum(recent_5) / len(recent_5) if recent_5 else 0

        result += f"  近20日累计主力净流入: {self._fmt_amount(cum_net)}\n"
        result += f"  近5日日均主力净流入: {self._fmt_amount(avg_daily_net)}\n\n"

        first_10 = net_amounts[:10] if len(net_amounts) >= 10 else net_amounts
        last_10 = net_amounts[-10:] if len(net_amounts) >= 10 else net_amounts
        first_sum = sum(first_10)
        last_sum = sum(last_10)

        if first_sum < 0 and last_sum > 0:
            result += "  ✅ 资金流向改善：前10日净流出 → 近10日净流入，主力态度转多\n"
        elif first_sum > 0 and last_sum > 0:
            result += "  ✅ 主力持续流入，资金面偏多\n"
        elif first_sum < 0 and last_sum < 0:
            result += "  ⚠️ 主力持续流出，资金面偏空\n"
        else:
            result += "  → 主力态度转向偏空\n"

        result += f"\n  {'日期':<12s} {'超大单净流入':>14s} {'大单净流入':>14s} {'中单净流入':>14s} {'小单净流入':>14s}\n"
        result += f"  {'─' * 72}\n"
        for _, row in recent.tail(5).iterrows():
            date = str(row.get("trade_date", ""))[:8]
            elg = (float(row.get("buy_elg_amount", 0) or 0) - float(row.get("sell_elg_amount", 0) or 0))
            lg = (float(row.get("buy_lg_amount", 0) or 0) - float(row.get("sell_lg_amount", 0) or 0))
            md = (float(row.get("buy_md_amount", 0) or 0) - float(row.get("sell_md_amount", 0) or 0))
            sm = (float(row.get("buy_sm_amount", 0) or 0) - float(row.get("sell_sm_amount", 0) or 0))
            result += f"  {date:<12s} {self._fmt_amount(elg):>14s} {self._fmt_amount(lg):>14s} {self._fmt_amount(md):>14s} {self._fmt_amount(sm):>14s}\n"

        result += "\n"
        return result

    def _analyze_margin(self) -> str:
        result = RF.section("融资融券")
        margin_df = self.data.get("margin")
        margin_detail = self.data.get("margin_detail")

        if margin_df is not None and not margin_df.empty:
            margin_df = margin_df.sort_values("trade_date").reset_index(drop=True)
            latest = margin_df.iloc[-1]
            rzye = float(latest.get("rzye", 0) or 0)
            rqye = float(latest.get("rqye", 0) or 0)

            result += f"  最新融资余额: {rzye / 1e8:.2f}亿\n"
            result += f"  最新融券余额: {rqye / 1e8:.2f}亿\n"
            if rzye > 0:
                result += f"  融资融券比: {rzye / max(rqye, 1):.0f}:1\n"

            if len(margin_df) >= 10:
                prev_10 = float(margin_df.iloc[-10].get("rzye", 0) or 0)
                change = (rzye - prev_10) / prev_10 * 100 if prev_10 > 0 else 0
                if change > 10:
                    result += f"  ✅ 融资余额快速上升（+{change:.1f}%），杠杆资金看多\n"
                elif change > 0:
                    result += f"  → 融资余额小幅增加（+{change:.1f}%）\n"
                elif change < -10:
                    result += f"  ⚠️ 融资余额快速下降（{change:.1f}%），杠杆资金撤退\n"
                else:
                    result += f"  → 融资余额小幅下降（{change:.1f}%）\n"

        if margin_detail is not None and not margin_detail.empty:
            latest = margin_detail.sort_values("trade_date").iloc[-1]
            rzmre = float(latest.get("rzmre", 0) or 0)
            rqyl = float(latest.get("rqyl", 0) or 0)
            result += f"  当日融资买入额: {rzmre / 1e8:.2f}亿\n"
            if rqyl:
                result += f"  当日融券卖出量: {rqyl / 1e4:.2f}万股\n"

        result += "\n"
        return result

    def _analyze_hk_hold(self) -> str:
        result = RF.section("北向资金（沪深股通）")
        df = self.data.get("hk_hold")
        if df is None or df.empty:
            return result + "  未获取到北向资金数据\n\n"

        df = df.sort_values("trade_date").reset_index(drop=True)
        latest = df.iloc[-1]
        latest_ratio = float(latest.get("ratio", 0) or 0)

        result += f"  最新北向持股占比: {latest_ratio:.2f}%\n"
        result += f"  最新北向持股数: {self._fmt_num(latest.get('vol'))}\n"

        if len(df) >= 20:
            prev_20 = float(df.iloc[-20].get("ratio", 0) or 0)
            change = latest_ratio - prev_20
            if change > 1:
                result += f"  ✅ 北向资金近20日增持 {change:+.2f}个百分点\n"
            elif change < -1:
                result += f"  ⚠️ 北向资金近20日减持 {change:+.2f}个百分点\n"
            else:
                result += "  → 北向资金近20日基本持平\n"

        result += "\n"
        return result

    def _analyze_block_trade(self) -> str:
        result = RF.section("大宗交易")
        df = self.data.get("block_trade")
        if df is None or df.empty:
            return result + "  未获取到大宗交易数据\n\n"

        recent = df.head(10) if "trade_date" in df.columns else df.iloc[:10]
        result += "  近10笔大宗交易:\n"
        result += f"  {'日期':<12s} {'价格':>10s} {'成交量':>12s} {'成交额':>12s}\n"
        result += f"  {'─' * 50}\n"

        for _, row in recent.iterrows():
            date = str(row.get("trade_date", "N/A"))[:8]
            price = f"{float(row.get('price', 0)):.2f}" if row.get("price") else "N/A"
            vol = self._fmt_num(row.get("vol"))
            amount = self._fmt_amount(row.get("amount"))
            result += f"  {date:<12s} {price:>10s} {vol:>12s} {amount:>12s}\n"

        result += "\n"
        return result

    def _capital_flow_score(self) -> str:
        """资金面综合评分"""
        result = RF.section("资金面综合评分")

        score = 50
        reasons = []

        moneyflow = self.data.get("moneyflow")
        if moneyflow is not None and not moneyflow.empty:
            mf = moneyflow.sort_values("trade_date")
            recent = mf.tail(20)
            net_sum = 0
            for _, row in recent.iterrows():
                buy = float(row.get("buy_elg_amount", 0) or 0) + float(row.get("buy_lg_amount", 0) or 0)
                sell = float(row.get("sell_elg_amount", 0) or 0) + float(row.get("sell_lg_amount", 0) or 0)
                net_sum += (buy - sell)
            if net_sum > 1e8:
                score += 20
                reasons.append("主力近20日大幅净流入 (+20)")
            elif net_sum > 0:
                score += 10
                reasons.append("主力近20日小幅净流入 (+10)")
            else:
                score -= 10
                reasons.append("主力近20日净流出 (-10)")

        hk = self.data.get("hk_hold")
        if hk is not None and not hk.empty:
            hk = hk.sort_values("trade_date")
            if len(hk) >= 20:
                recent_ratio = float(hk.iloc[-1].get("ratio", 0) or 0)
                prev_ratio = float(hk.iloc[-20].get("ratio", 0) or 0)
                if recent_ratio - prev_ratio > 0.5:
                    score += 10
                    reasons.append("北向资金增持 (+10)")

        margin = self.data.get("margin")
        if margin is not None and not margin.empty:
            m = margin.sort_values("trade_date")
            if len(m) >= 10:
                latest = float(m.iloc[-1].get("rzye", 0) or 0)
                prev = float(m.iloc[-10].get("rzye", 0) or 0)
                change = (latest - prev) / prev * 100 if prev > 0 else 0
                if change > 5:
                    score += 5
                    reasons.append("融资余额增长 (+5)")

        score = max(0, min(100, score))
        rating = "偏多" if score >= 60 else ("中性" if score >= 40 else "偏空")

        result += f"  资金面评分: {score}/100 ({rating})\n"
        for r in reasons:
            result += f"    {r}\n"

        result += "\n"
        return result

    @staticmethod
    def _fmt_amount(val) -> str:
        if val is None:
            return "N/A"
        try:
            v = float(val)
            if abs(v) >= 1e8:
                return f"{v / 1e8:+.2f}亿"
            elif abs(v) >= 1e4:
                return f"{v / 1e4:+.2f}万"
            else:
                return f"{v:+,.0f}"
        except (ValueError, TypeError):
            return "N/A"

    @staticmethod
    def _fmt_num(val) -> str:
        if val is None:
            return "N/A"
        try:
            v = float(val)
            if abs(v) >= 1e8:
                return f"{v / 1e8:.2f}亿"
            elif abs(v) >= 1e4:
                return f"{v / 1e4:.2f}万"
            else:
                return f"{v:,.0f}"
        except (ValueError, TypeError):
            return "N/A"
