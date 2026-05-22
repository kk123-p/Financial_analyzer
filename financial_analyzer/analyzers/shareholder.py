"""
股东结构分析器 — 股东人数趋势、机构持股、股权集中度
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..logging_config import get_logger

logger = get_logger(__name__)


class ShareholderAnalyzer(BaseAnalyzer):
    """股东结构分析器"""

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
        """股东结构综合分析"""
        result = RF.header("股东结构分析")

        basic_info = self._get_basic_info()
        if basic_info.get("name"):
            result += f"【股票信息】{basic_info['name']} ({self.stock_code})\n\n"

        result += self._analyze_holder_count()
        result += self._analyze_top10_holders()
        result += self._analyze_top10_floatholders()
        result += self._ownership_score()

        result += RF.footer()
        return result

    def _analyze_holder_count(self) -> str:
        result = RF.section("股东人数变化趋势")
        df = self.data.get("stk_holdernumber")
        if df is None or df.empty:
            return result + "  未获取到股东人数数据\n\n"

        df = df.sort_values("ann_date").reset_index(drop=True)
        if len(df) < 2:
            result += f"  最新股东人数: {self._fmt_num(df.iloc[-1].get('holder_num'))}\n\n"
            return result

        first = df.iloc[0].get("holder_num") or 0
        last = df.iloc[-1].get("holder_num") or 0
        change_pct = (last - first) / first * 100 if first else 0

        result += f"  {'─' * 55}\n"
        result += f"  {'报告期':<14s} {'股东人数':>14s} {'变化':>14s}\n"
        result += f"  {'─' * 55}\n"

        prev = None
        for _, row in df.iterrows():
            date = str(row.get("ann_date", "N/A"))[:8]
            num = row.get("holder_num")
            num_str = self._fmt_num(num)
            if prev is not None and prev > 0:
                delta = (num - prev) / prev * 100 if num else 0
                delta_str = f"{delta:+.1f}%"
            else:
                delta_str = "--"
            result += f"  {date:<14s} {num_str:>14s} {delta_str:>14s}\n"
            prev = num

        direction = "增加" if change_pct > 0 else "减少"
        signal = "⚠️ 散户化" if change_pct > 20 else ("✅ 筹码集中" if change_pct < -20 else "→ 基本稳定")
        result += f"\n  总变化: {change_pct:+.1f}% (股东人数{direction})  {signal}\n"
        result += "\n"
        return result

    def _analyze_top10_holders(self) -> str:
        result = RF.section("前十大股东")
        df = self.data.get("top10_holders")
        if df is None or df.empty:
            return result + "  未获取到前十大股东数据\n\n"

        latest_period = df["end_date"].max() if "end_date" in df.columns else None
        if latest_period:
            latest = df[df["end_date"] == latest_period]
            result += f"  报告期: {str(latest_period)[:8]}\n\n"

            total_ratio = 0
            result += f"  {'股东名称':<24s} {'持股数':>12s} {'占比':>10s}\n"
            result += f"  {'─' * 48}\n"
            for _, row in latest.head(10).iterrows():
                name = str(row.get("holder_name", "N/A"))
                if len(name) > 22:
                    name = name[:22] + ".."
                amount = row.get("hold_amount")
                ratio = row.get("hold_ratio")
                amt_str = self._fmt_num(amount) if amount else "N/A"
                ratio_str = f"{float(ratio):.2f}%" if ratio else "N/A"
                result += f"  {name:<24s} {amt_str:>12s} {ratio_str:>10s}\n"
                if ratio:
                    total_ratio += float(ratio)

            result += f"\n  前十大合计持股: {total_ratio:.2f}%\n"
            if total_ratio > 60:
                result += "  ✅ 股权高度集中（>60%），控制权稳定\n"
            elif total_ratio > 40:
                result += "  → 股权相对集中（40-60%）\n"
            else:
                result += "  ⚠️ 股权较分散（<40%），存在潜在控制权风险\n"

        result += "\n"
        return result

    def _analyze_top10_floatholders(self) -> str:
        result = RF.section("前十大流通股东（机构持仓）")
        df = self.data.get("top10_floatholders")
        if df is None or df.empty:
            return result + "  未获取到流通股东数据\n\n"

        latest_period = df["end_date"].max() if "end_date" in df.columns else None
        if latest_period:
            latest = df[df["end_date"] == latest_period]
            inst_ratio = 0
            fund_names = ["基金", "QFII", "社保", "保险", "券商", "信托", "银行", "私募"]

            for _, row in latest.iterrows():
                name = str(row.get("holder_name", ""))
                ratio = row.get("hold_ratio")
                if ratio:
                    is_inst = any(kw in name for kw in fund_names)
                    if is_inst:
                        inst_ratio += float(ratio)

            result += f"  报告期: {str(latest_period)[:8]}\n"
            result += f"  机构持股占比: {inst_ratio:.2f}%\n\n"

            for _, row in latest.head(10).iterrows():
                name = str(row.get("holder_name", ""))
                is_inst = any(kw in name for kw in fund_names)
                if is_inst:
                    ratio = row.get("hold_ratio")
                    ratio_str = f"{float(ratio):.2f}%" if ratio else "N/A"
                    result += f"  · {name:<30s} {ratio_str:>8s}\n"

            if inst_ratio > 30:
                result += "\n  ✅ 机构持仓比例较高（>30%），认可度高\n"
            elif inst_ratio > 10:
                result += "\n  → 有一定机构参与（10-30%）\n"
            else:
                result += "\n  → 机构参与度较低（<10%）\n"

        result += "\n"
        return result

    def _ownership_score(self) -> str:
        """股权结构综合评分"""
        result = RF.section("股权结构综合评分")

        score = 50
        reasons = []

        holder_df = self.data.get("stk_holdernumber")
        if holder_df is not None and not holder_df.empty:
            holder_df = holder_df.sort_values("ann_date")
            if len(holder_df) >= 2:
                first = holder_df.iloc[0].get("holder_num") or 0
                last = holder_df.iloc[-1].get("holder_num") or 0
                change = (last - first) / first * 100 if first else 0
                if change < -20:
                    score += 20
                    reasons.append("股东人数大幅减少 → 筹码集中 (+20)")
                elif change < -5:
                    score += 10
                    reasons.append("股东人数小幅减少 (+10)")
                elif change > 20:
                    score -= 15
                    reasons.append("股东人数大幅增加 → 筹码分散 (-15)")

        top10 = self.data.get("top10_holders")
        if top10 is not None and not top10.empty:
            latest_period = top10["end_date"].max() if "end_date" in top10.columns else None
            if latest_period:
                latest = top10[top10["end_date"] == latest_period]
                total_ratio = sum(float(r) for r in latest["hold_ratio"] if r)
                if total_ratio > 60:
                    score += 15
                    reasons.append(f"前十大持股{total_ratio:.1f}% → 高度集中 (+15)")
                elif total_ratio > 40:
                    score += 5
                    reasons.append(f"前十大持股{total_ratio:.1f}% (+5)")

        score = max(0, min(100, score))
        rating = "优秀" if score >= 80 else ("良好" if score >= 60 else ("一般" if score >= 40 else "关注"))

        result += f"  股权结构评分: {score}/100 ({rating})\n"
        for r in reasons:
            result += f"    {r}\n"

        result += "\n"
        return result

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
