"""
第二阶段计算器 - 行业对比、相对估值、股东回报、财报质量
"""
import pandas as pd
import numpy as np
from ..logging_config import get_logger

logger = get_logger(__name__)


class Phase2Calculator:
    """第二阶段分析计算器"""

    # ========================================================================
    # 1. 行业对比分析
    # ========================================================================

    @staticmethod
    def compare_with_peers(company_data: dict, peers_data: list) -> dict:
        """
        公司与同行业对比

        Args:
            company_data: {"roe", "gross_margin", "net_margin", "pe", "pb", "revenue_growth", ...}
            peers_data: list of dict，同行业公司数据

        Returns:
            {"rankings": {}, "peer_avg": {}, "details": []}
        """
        metrics = ["roe", "gross_margin", "net_margin", "pe", "pb",
                    "revenue_growth", "debt_ratio", "current_ratio"]
        rankings = {}
        peer_avg = {}
        details = []

        for metric in metrics:
            company_val = company_data.get(metric)
            peer_vals = [p.get(metric) for p in peers_data if p.get(metric) is not None]
            if company_val is None or not peer_vals:
                continue

            # 排名（PE/PB 越低越好，其他越高越好）
            lower_is_better = metric in ["pe", "pb", "debt_ratio"]
            all_vals = sorted(peer_vals + [company_val],
                              reverse=not lower_is_better)
            rank = all_vals.index(company_val) + 1
            total = len(all_vals)
            percentile = (total - rank) / total * 100

            avg = np.mean(peer_vals)
            median = np.median(peer_vals)

            rankings[metric] = {
                "rank": rank, "total": total,
                "percentile": percentile,
                "value": company_val,
            }
            peer_avg[metric] = {"avg": avg, "median": median}

            if percentile > 75:
                details.append(f"  {metric}: {company_val:.2f} (行业前25%，排名 {rank}/{total})")
            elif percentile > 50:
                details.append(f"  {metric}: {company_val:.2f} (行业中上，排名 {rank}/{total})")
            elif percentile > 25:
                details.append(f"  {metric}: {company_val:.2f} (行业中下，排名 {rank}/{total})")
            else:
                details.append(f"  {metric}: {company_val:.2f} (行业后25%，排名 {rank}/{total})")

        return {
            "rankings": rankings,
            "peer_avg": peer_avg,
            "details": details,
        }

    # ========================================================================
    # 2. 相对估值
    # ========================================================================

    @staticmethod
    def pe_percentile(pe_history: list, current_pe: float) -> dict:
        """
        PE 历史分位数

        Args:
            pe_history: 历史 PE 值列表
            current_pe: 当前 PE

        Returns:
            {"percentile", "avg", "median", "min", "max", "current", "signal"}
        """
        if not pe_history or current_pe is None:
            return {"percentile": None, "signal": "数据不足"}

        valid = [p for p in pe_history if p is not None and p > 0 and p < 1000]
        if not valid:
            return {"percentile": None, "signal": "数据不足"}

        below = sum(1 for p in valid if p <= current_pe)
        percentile = below / len(valid) * 100

        result = {
            "percentile": percentile,
            "avg": np.mean(valid),
            "median": np.median(valid),
            "min": min(valid),
            "max": max(valid),
            "current": current_pe,
            "sample_count": len(valid),
        }

        if percentile < 20:
            result["signal"] = "PE 处于历史低位，可能被低估"
        elif percentile < 40:
            result["signal"] = "PE 偏低于历史均值"
        elif percentile < 60:
            result["signal"] = "PE 处于历史中位"
        elif percentile < 80:
            result["signal"] = "PE 偏高于历史均值"
        else:
            result["signal"] = "PE 处于历史高位，可能被高估"

        return result

    @staticmethod
    def pb_roe_model(roe: float, required_return: float = 10.0) -> dict:
        """
        PB-ROE 估值模型

        合理 PB = ROE / 要求回报率

        Args:
            roe: ROE (%)
            required_return: 要求回报率 (%)

        Returns:
            {"fair_pb", "current_pb", "premium_discount", "signal"}
        """
        if roe is None or roe <= 0:
            return {"fair_pb": None, "signal": "ROE 数据不足"}

        fair_pb = roe / required_return

        return {
            "fair_pb": fair_pb,
            "roe": roe,
            "required_return": required_return,
        }

    @staticmethod
    def ev_ebitda(ebitda: float, market_cap: float, total_liab: float,
                  cash: float, minority: float = 0) -> dict:
        """
        EV/EBITDA 估值

        EV = 市值 + 总负债 - 现金 - 少数股东权益
        """
        if not ebitda or ebitda <= 0:
            return {"ev": None, "ev_ebitda": None, "signal": "EBITDA 数据不足"}

        ev = (market_cap or 0) + (total_liab or 0) - (cash or 0) - minority
        ev_ebitda = ev / ebitda

        signal = "N/A"
        if ev_ebitda < 6:
            signal = "EV/EBITDA 偏低，可能被低估"
        elif ev_ebitda < 10:
            signal = "EV/EBITDA 合理"
        elif ev_ebitda < 15:
            signal = "EV/EBITDA 偏高"
        else:
            signal = "EV/EBITDA 过高，估值偏贵"

        return {"ev": ev, "ev_ebitda": ev_ebitda, "signal": signal}

    # ========================================================================
    # 3. 股东回报分析
    # ========================================================================

    @staticmethod
    def shareholder_returns(dividends: list, net_profits: list,
                            current_price: float, shares: float) -> dict:
        """
        股东回报分析

        Args:
            dividends: 近5年总派息额列表 (元)
            net_profits: 近5年净利润列表 (元)
            current_price: 当前股价
            shares: 总股本

        Returns:
            {"avg_payout_ratio", "dividend_yield", "total_return", "details"}
        """
        if not dividends or not net_profits:
            return {"avg_payout_ratio": None, "details": ["数据不足"]}

        # 股息支付率
        payout_ratios = []
        for d, np_val in zip(dividends, net_profits):
            if d and np_val and np_val > 0:
                payout_ratios.append(d / np_val * 100)

        avg_payout = np.mean(payout_ratios) if payout_ratios else None

        # 当前股息率 (用最近一年)
        div_per_share = (dividends[0] / shares) if dividends[0] and shares and shares > 0 else None
        dividend_yield = (div_per_share / current_price * 100) if div_per_share and current_price else None

        details = []
        if avg_payout:
            if avg_payout > 50:
                details.append(f"  平均股息支付率 {avg_payout:.1f}%，分红慷慨")
            elif avg_payout > 30:
                details.append(f"  平均股息支付率 {avg_payout:.1f}%，分红适中")
            else:
                details.append(f"  平均股息支付率 {avg_payout:.1f}%，留存较多用于发展")

        if dividend_yield:
            if dividend_yield > 3:
                details.append(f"  当前股息率 {dividend_yield:.2f}%，具有吸引力")
            elif dividend_yield > 1:
                details.append(f"  当前股息率 {dividend_yield:.2f}%，一般水平")
            else:
                details.append(f"  当前股息率 {dividend_yield:.2f}%，偏低")

        return {
            "avg_payout_ratio": avg_payout,
            "dividend_yield": dividend_yield,
            "payout_ratios": payout_ratios,
            "details": details,
        }

    # ========================================================================
    # 4. 财报质量分析
    # ========================================================================

    @staticmethod
    def financial_quality(periods_data: list) -> dict:
        """
        财报质量评估

        Args:
            periods_data: list of dict (近3-5年)
                {revenue, accounts_receivable, inventories, op_cashflow,
                 net_profit, total_assets, goodwill, non_recurring_income}

        Returns:
            {"quality_score", "quality_level", "factors", "details"}
        """
        if len(periods_data) < 2:
            return {"quality_score": 0, "quality_level": "数据不足",
                    "factors": {}, "details": ["需要至少2年数据"]}

        factors = {}
        details = []
        total_score = 0

        # 1. 应收账款/营收比趋势 (0-25分)
        ar_ratios = []
        for p in periods_data:
            rev = p.get("revenue")
            ar = p.get("accounts_receivable")
            if rev and rev > 0 and ar is not None:
                ar_ratios.append(ar / rev * 100)

        ar_score = 12  # 默认
        if len(ar_ratios) >= 2:
            if ar_ratios[0] < ar_ratios[-1] * 0.9:
                ar_score = 25
                details.append("  应收/营收比下降，收入确认质量改善")
            elif ar_ratios[0] > ar_ratios[-1] * 1.2:
                ar_score = 5
                details.append("  应收/营收比上升，可能存在放宽信用政策或收入确认激进")
            else:
                ar_score = 15
                details.append("  应收/营收比稳定")
        factors["应收质量"] = ar_score
        total_score += ar_score

        # 2. 经营现金流/净利润偏离度 (0-25分)
        cf_np_ratios = []
        for p in periods_data:
            ocf = p.get("op_cashflow")
            np_val = p.get("net_profit")
            if ocf and np_val and np_val > 0:
                cf_np_ratios.append(ocf / np_val)

        cf_score = 12
        if cf_np_ratios:
            avg_ratio = np.mean(cf_np_ratios)
            if avg_ratio >= 1.2:
                cf_score = 25
                details.append(f"  经营现金流/净利润 = {avg_ratio:.2f}，盈利质量优秀")
            elif avg_ratio >= 0.8:
                cf_score = 18
                details.append(f"  经营现金流/净利润 = {avg_ratio:.2f}，盈利质量正常")
            elif avg_ratio >= 0.5:
                cf_score = 10
                details.append(f"  经营现金流/净利润 = {avg_ratio:.2f}，现金流质量偏低")
            else:
                cf_score = 3
                details.append(f"  经营现金流/净利润 = {avg_ratio:.2f}，现金流质量差")
        factors["现金流质量"] = cf_score
        total_score += cf_score

        # 3. 存货/营业成本比趋势 (0-25分)
        inv_ratios = []
        for p in periods_data:
            inv = p.get("inventories")
            cost = p.get("op_cost") or p.get("oper_cost")
            if inv is not None and cost and cost > 0:
                inv_ratios.append(inv / cost * 100)

        inv_score = 12
        if len(inv_ratios) >= 2:
            if inv_ratios[0] < inv_ratios[-1] * 0.9:
                inv_score = 22
                details.append("  存货/成本比下降，存货管理改善")
            elif inv_ratios[0] > inv_ratios[-1] * 1.3:
                inv_score = 5
                details.append("  存货/成本比上升，可能存在滞销风险")
            else:
                inv_score = 15
                details.append("  存货/成本比稳定")
        factors["存货质量"] = inv_score
        total_score += inv_score

        # 4. 商誉/总资产比 (0-25分)
        gw_score = 20  # 默认
        for p in periods_data:
            gw = p.get("goodwill")
            ta = p.get("total_assets")
            if gw and ta and ta > 0:
                gw_ratio = gw / ta * 100
                if gw_ratio > 30:
                    gw_score = 5
                    details.append(f"  商誉/总资产 = {gw_ratio:.1f}%，商誉减值风险高")
                elif gw_ratio > 15:
                    gw_score = 10
                    details.append(f"  商誉/总资产 = {gw_ratio:.1f}%，需关注减值风险")
                elif gw_ratio > 5:
                    gw_score = 18
                    details.append(f"  商誉/总资产 = {gw_ratio:.1f}%，风险可控")
                else:
                    gw_score = 25
                    details.append(f"  商誉/总资产 = {gw_ratio:.1f}%，商誉风险低")
                break
        factors["商誉风险"] = gw_score
        total_score += gw_score

        # 质量等级
        if total_score >= 80:
            quality_level = "优秀"
        elif total_score >= 60:
            quality_level = "良好"
        elif total_score >= 40:
            quality_level = "一般"
        else:
            quality_level = "较差"

        return {
            "quality_score": total_score,
            "quality_level": quality_level,
            "factors": factors,
            "details": details,
        }
