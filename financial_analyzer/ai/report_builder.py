"""
体检报告 JSON 构建器
将第一阶段的原始财务数据 + 分析结果，打包成结构化的"公司体检报告"
作为第二阶段（AI深度投研）的唯一输入源
"""
import pandas as pd
import numpy as np
from ..logging_config import get_logger

logger = get_logger(__name__)


class ReportBuilder:
    """体检报告构建器"""

    @staticmethod
    def build(data: dict, stock_code: str, data_adapter=None, cache_manager=None) -> dict:
        """
        构建完整的公司体检报告

        Args:
            data: 原始财务数据 dict (income/balance/cashflow/basic)
            stock_code: 股票代码
            data_adapter: 数据适配器（可选）
            cache_manager: 缓存管理器（可选）

        Returns:
            结构化体检报告 dict
        """
        report = {
            "stock_code": stock_code,
            "company_snapshot": {},
            "financial_health": {},
            "dupont_analysis": {},
            "risk_models": {},
            "valuation": {},
            "cashflow_analysis": {},
            "anomaly_signals": [],
        }

        try:
            # 1. 公司快照
            report["company_snapshot"] = ReportBuilder._build_snapshot(data, stock_code)

            # 2. 财务健康仪表盘
            report["financial_health"] = ReportBuilder._build_health(data)

            # 3. 杜邦分析
            report["dupont_analysis"] = ReportBuilder._build_dupont(data)

            # 4. 风险模型 (Z-score, F-score, M-score)
            report["risk_models"] = ReportBuilder._build_risk_models(data)

            # 5. 估值
            report["valuation"] = ReportBuilder._build_valuation(data)

            # 6. 现金流分析
            report["cashflow_analysis"] = ReportBuilder._build_cashflow(data)

            # 7. 异常信号（基础版，详细版由 SignalDetector 做）
            report["anomaly_signals"] = ReportBuilder._build_anomaly_signals(data)

        except Exception as e:
            logger.error(f"构建体检报告异常: {e}")
            report["error"] = str(e)

        return report

    # ========================================================================
    # 公司快照
    # ========================================================================
    @staticmethod
    def _build_snapshot(data: dict, stock_code: str) -> dict:
        """公司快照"""
        snap = {"stock_code": stock_code}

        basic = data.get("basic")
        income = data.get("income")

        if basic is not None and len(basic) > 0:
            latest = basic.iloc[0]
            snap["price"] = ReportBuilder._val(latest, ["close", "收盘价"])
            snap["total_share"] = ReportBuilder._val(latest, ["total_share", "总股本"])
            if snap["price"] and snap["total_share"]:
                snap["market_cap"] = round(snap["price"] * snap["total_share"], 2)
                snap["market_cap_yi"] = round(snap["market_cap"] / 10000, 2)  # 万元→亿元

        if income is not None and len(income) > 0:
            latest_inc = income.iloc[0]
            snap["revenue"] = ReportBuilder._val(latest_inc, ["revenue", "营业收入"])
            snap["net_profit"] = ReportBuilder._val(latest_inc, ["net_profit", "净利润"])

        # PE, PB
        balance = data.get("balance")
        if balance is not None and len(balance) > 0:
            latest_bal = balance.iloc[0]
            equity = ReportBuilder._val(latest_bal, ["total_equity", "股东权益合计"])
            if snap.get("price") and snap.get("total_share") and equity:
                pb = snap["price"] * snap["total_share"] / (equity * 10000) if equity != 0 else None
                snap["pb"] = round(pb, 2) if pb else None
            if snap.get("price") and snap.get("total_share") and snap.get("net_profit") and snap["net_profit"] > 0:
                pe = snap["price"] * snap["total_share"] / (snap["net_profit"] * 10000)
                snap["pe"] = round(pe, 2)

        return snap

    # ========================================================================
    # 财务健康仪表盘
    # ========================================================================
    @staticmethod
    def _build_health(data: dict) -> dict:
        """财务健康仪表盘 - 包含五大类比率和原始数据"""
        health = {}

        income = data.get("income")
        balance = data.get("balance")
        cashflow = data.get("cashflow")

        if income is None or balance is None:
            return health

        try:
            latest_inc = income.iloc[0]
            latest_bal = balance.iloc[0]

            # 原始数据（给 SignalDetector 用）
            raw = {}
            raw["revenue"] = ReportBuilder._val(latest_inc, ["revenue", "营业收入"])
            raw["net_profit"] = ReportBuilder._val(latest_inc, ["net_profit", "净利润"])
            raw["operating_cost"] = ReportBuilder._val(latest_inc, ["operating_cost", "营业成本"])
            raw["total_assets"] = ReportBuilder._val(latest_bal, ["total_assets", "资产总计"])
            raw["total_liab"] = ReportBuilder._val(latest_bal, ["total_liab", "负债合计"])
            raw["equity"] = ReportBuilder._val(latest_bal, ["total_equity", "股东权益合计"])
            raw["accounts_receivable"] = ReportBuilder._val(latest_bal, ["accounts_receivable", "应收账款"])
            raw["inventory"] = ReportBuilder._val(latest_bal, ["inventories", "存货"])
            raw["cash"] = ReportBuilder._val(latest_bal, ["money_cap", "货币资金"])
            raw["goodwill"] = ReportBuilder._val(latest_bal, ["goodwill", "商誉"])

            if cashflow is not None and len(cashflow) > 0:
                latest_cf = cashflow.iloc[0]
                raw["op_cashflow"] = ReportBuilder._val(latest_cf, [
                    "n_cashflow_act", "经营活动产生的现金流量净额"
                ])

            health["_raw"] = raw

            # 上一期原始数据（给 SignalDetector 用）
            if len(income) >= 2:
                raw_prev = {}
                prev_inc = income.iloc[-2]
                prev_bal = balance.iloc[-2]
                raw_prev["revenue"] = ReportBuilder._val(prev_inc, ["revenue", "营业收入"])
                raw_prev["net_profit"] = ReportBuilder._val(prev_inc, ["net_profit", "净利润"])
                raw_prev["accounts_receivable"] = ReportBuilder._val(prev_bal, ["accounts_receivable", "应收账款"])
                health["_raw_prev"] = raw_prev

            # 盈利能力
            profitability = {}
            rev = raw["revenue"]
            np_val = raw["net_profit"]
            cost = raw["operating_cost"]
            ta = raw["total_assets"]
            eq = raw["equity"]

            if rev and rev > 0 and cost is not None:
                profitability["毛利率"] = round((rev - cost) / rev * 100, 2)
            if rev and rev > 0 and np_val is not None:
                profitability["净利率"] = round(np_val / rev * 100, 2)
            if ta and ta > 0 and np_val is not None:
                profitability["ROA"] = round(np_val / ta * 100, 2)
            if eq and eq > 0 and np_val is not None:
                profitability["ROE"] = round(np_val / eq * 100, 2)
            health["盈利能力"] = profitability

            # 偿债能力
            solvency = {}
            current_assets = ReportBuilder._val(latest_bal, ["total_current_assets", "流动资产合计"])
            current_liab = ReportBuilder._val(latest_bal, ["total_current_liab", "流动负债合计"])
            if current_assets and current_liab and current_liab > 0:
                solvency["流动比率"] = round(current_assets / current_liab, 2)
                inv = raw["inventory"]
                if inv is not None:
                    solvency["速动比率"] = round((current_assets - inv) / current_liab, 2)
            if ta and ta > 0 and raw["total_liab"]:
                solvency["资产负债率"] = round(raw["total_liab"] / ta * 100, 2)
            health["偿债能力"] = solvency

            # 营运能力
            efficiency = {}
            ar = raw["accounts_receivable"]
            if rev and ar and ar > 0:
                efficiency["应收账款周转率"] = round(rev / ar, 2)
            if cost and raw["inventory"] and raw["inventory"] > 0:
                efficiency["存货周转率"] = round(cost / raw["inventory"], 2)
            if rev and ta and ta > 0:
                efficiency["总资产周转率"] = round(rev / ta, 4)
            health["营运能力"] = efficiency

            # 发展能力（需要多年数据）
            growth = {}
            if len(income) >= 2:
                prev_rev = ReportBuilder._val(income.iloc[-2], ["revenue", "营业收入"])
                prev_np = ReportBuilder._val(income.iloc[-2], ["net_profit", "净利润"])
                if prev_rev and prev_rev > 0 and rev:
                    growth["营收增长率"] = round((rev - prev_rev) / prev_rev * 100, 2)
                if prev_np and prev_np != 0 and np_val is not None:
                    growth["净利润增长率"] = round((np_val - prev_np) / abs(prev_np) * 100, 2)
            health["发展能力"] = growth

        except Exception as e:
            logger.error(f"构建财务健康仪表盘异常: {e}")

        return health

    # ========================================================================
    # 杜邦分析
    # ========================================================================
    @staticmethod
    def _build_dupont(data: dict) -> dict:
        """杜邦分析（三因子 + 改良版）"""
        dupont = {"three_factor": [], "improved": []}

        income = data.get("income")
        balance = data.get("balance")
        if income is None or balance is None:
            return dupont

        try:
            # 三因子杜邦（最近3年）
            for i in range(max(0, len(income) - 3), len(income)):
                if i >= len(balance):
                    break
                inc = income.iloc[i]
                bal = balance.iloc[i]

                rev = ReportBuilder._val(inc, ["revenue", "营业收入"])
                np_val = ReportBuilder._val(inc, ["net_profit", "净利润"])
                ta = ReportBuilder._val(bal, ["total_assets", "资产总计"])
                eq = ReportBuilder._val(bal, ["total_equity", "股东权益合计"])

                if rev and rev > 0 and ta and ta > 0 and eq and eq > 0 and np_val is not None:
                    nm = np_val / rev  # 净利率
                    at = rev / ta  # 资产周转率
                    em = ta / eq  # 权益乘数
                    roe = nm * at * em

                    end_date = str(inc.get("end_date", "")) if "end_date" in inc.index else f"period_{i}"
                    dupont["three_factor"].append({
                        "end_date": end_date,
                        "roe": round(roe * 100, 2),
                        "net_margin": round(nm * 100, 2),
                        "asset_turnover": round(at, 4),
                        "equity_multiplier": round(em, 2),
                    })

            # 改良杜邦（RNOA + 杠杆贡献）
            for i in range(max(0, len(income) - 3), len(income)):
                if i >= len(balance):
                    break
                inc = income.iloc[i]
                bal = balance.iloc[i]

                np_val = ReportBuilder._val(inc, ["net_profit", "净利润"])
                ta = ReportBuilder._val(bal, ["total_assets", "资产总计"])
                eq = ReportBuilder._val(bal, ["total_equity", "股东权益合计"])
                tl = ReportBuilder._val(bal, ["total_liab", "负债合计"])

                if np_val is not None and ta and ta > 0 and eq and eq > 0:
                    # 简化版 RNOA ≈ ROA（未分离经营/金融活动）
                    rnoa = np_val / ta
                    # 杠杆贡献 ≈ (RNOA - 利息成本) × 负债/权益
                    # 简化：杠杆贡献 = ROE - RNOA
                    roe = np_val / eq
                    leverage_contrib = roe - rnoa

                    end_date = str(inc.get("end_date", "")) if "end_date" in inc.index else f"period_{i}"
                    dupont["improved"].append({
                        "end_date": end_date,
                        "roe": round(roe * 100, 2),
                        "rnoa": round(rnoa * 100, 2),
                        "leverage_contribution": round(leverage_contrib * 100, 2),
                        "spread": round((rnoa - 0.04) * 100, 2),  # 经营差异率（假设融资成本4%）
                    })

        except Exception as e:
            logger.error(f"杜邦分析异常: {e}")

        return dupont

    # ========================================================================
    # 风险模型
    # ========================================================================
    @staticmethod
    def _build_risk_models(data: dict) -> dict:
        """Z-score, F-score, M-score"""
        risk = {}

        balance = data.get("balance")
        income = data.get("income")
        cashflow = data.get("cashflow")

        if balance is None or income is None:
            return risk

        try:
            latest_bal = balance.iloc[0]
            latest_inc = income.iloc[0]

            ta = ReportBuilder._val(latest_bal, ["total_assets", "资产总计"])
            tl = ReportBuilder._val(latest_bal, ["total_liab", "负债合计"])
            ca = ReportBuilder._val(latest_bal, ["total_current_assets", "流动资产合计"])
            cl = ReportBuilder._val(latest_bal, ["total_current_liab", "流动负债合计"])
            eq = ReportBuilder._val(latest_bal, ["total_equity", "股东权益合计"])
            re = ReportBuilder._val(latest_bal, ["surplus_reserve", "盈余公积"])  # 留存收益近似
            rev = ReportBuilder._val(latest_inc, ["revenue", "营业收入"])
            np_val = ReportBuilder._val(latest_inc, ["net_profit", "净利润"])
            ebit = ReportBuilder._val(latest_inc, ["operate_profit", "营业利润"])

            basic = data.get("basic")
            mve = None
            if basic is not None and len(basic) > 0:
                close = ReportBuilder._val(basic.iloc[0], ["close", "收盘价"])
                share = ReportBuilder._val(basic.iloc[0], ["total_share", "总股本"])
                if close and share:
                    mve = close * share

            # Z-score (Altman修正模型)
            if ta and ta > 0:
                x1 = ((ca or 0) - (cl or 0)) / ta if ca and cl else 0
                x2 = (re or 0) / ta if re else 0
                x3 = (ebit or 0) / ta if ebit else 0
                x4 = (mve or 0) / (tl * 10000) if mve and tl and tl > 0 else 0
                x5 = (rev or 0) / ta if rev else 0

                z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

                zone = "safe" if z > 2.99 else ("gray" if z > 1.81 else "distress")
                zone_cn = {"safe": "安全区", "gray": "灰色区", "distress": "危机区"}[zone]

                risk["zscore"] = {
                    "z_score": round(z, 2),
                    "zone": zone,
                    "zone_cn": zone_cn,
                    "components": {
                        "X1_营运资本/总资产": round(x1, 4),
                        "X2_留存收益/总资产": round(x2, 4),
                        "X3_EBIT/总资产": round(x3, 4),
                        "X4_市值/总负债": round(x4, 4),
                        "X5_营收/总资产": round(x5, 4),
                    }
                }

            # F-score (Piotroski) - 简化版
            fscore = 0
            fscore_details = []
            if np_val and np_val > 0:
                fscore += 1; fscore_details.append("净利润为正 ✓")
            if cashflow is not None and len(cashflow) > 0:
                ocf = ReportBuilder._val(cashflow.iloc[0], ["n_cashflow_act", "经营活动产生的现金流量净额"])
                if ocf and ocf > 0:
                    fscore += 1; fscore_details.append("经营现金流为正 ✓")
                if np_val and ocf and ocf > np_val * 10000:
                    fscore += 1; fscore_details.append("现金流>净利润 ✓")
            if ta and ta > 0:
                roa = (np_val or 0) / ta
                if len(income) >= 2:
                    prev_np = ReportBuilder._val(income.iloc[-2], ["net_profit", "净利润"])
                    prev_ta = ReportBuilder._val(balance.iloc[-2], ["total_assets", "资产总计"])
                    if prev_ta and prev_ta > 0 and prev_np is not None:
                        prev_roa = prev_np / prev_ta
                        if roa > prev_roa:
                            fscore += 1; fscore_details.append("ROA改善 ✓")
            if eq and eq > 0:
                if tl:
                    dar = tl / (ta or 1)
                    if len(balance) >= 2:
                        prev_tl = ReportBuilder._val(balance.iloc[-2], ["total_liab", "负债合计"])
                        prev_ta2 = ReportBuilder._val(balance.iloc[-2], ["total_assets", "资产总计"])
                        if prev_tl and prev_ta2 and prev_ta2 > 0:
                            prev_dar = prev_tl / prev_ta2
                            if dar < prev_dar:
                                fscore += 1; fscore_details.append("杠杆下降 ✓")
            # 简化：毛利率、周转率改善
            if rev and rev > 0 and ReportBuilder._val(latest_inc, ["operating_cost", "营业成本"]):
                gm = (rev - ReportBuilder._val(latest_inc, ["operating_cost", "营业成本"])) / rev
                if len(income) >= 2:
                    prev_rev = ReportBuilder._val(income.iloc[-2], ["revenue", "营业收入"])
                    prev_cost = ReportBuilder._val(income.iloc[-2], ["operating_cost", "营业成本"])
                    if prev_rev and prev_rev > 0 and prev_cost:
                        prev_gm = (prev_rev - prev_cost) / prev_rev
                        if gm > prev_gm:
                            fscore += 1; fscore_details.append("毛利率改善 ✓")

            risk["fscore"] = {
                "score": fscore,
                "max": 9,
                "diagnosis": "强健" if fscore >= 7 else ("一般" if fscore >= 4 else "脆弱"),
                "details": fscore_details,
            }

            # M-score (Beneish) - 简化版
            # 完整模型需要8个变量，这里用关键指标近似
            mscore = -2.22  # 默认安全值
            if np_val and ta and ta > 0 and rev and rev > 0:
                ar = ReportBuilder._val(latest_bal, ["accounts_receivable", "应收账款"])
                inv = ReportBuilder._val(latest_bal, ["inventories", "存货"])
                # 简化：应收增速远超营收 → 可能操纵
                if len(income) >= 2 and ar:
                    prev_ar = ReportBuilder._val(balance.iloc[-2], ["accounts_receivable", "应收账款"])
                    prev_rev = ReportBuilder._val(income.iloc[-2], ["revenue", "营业收入"])
                    if prev_ar and prev_ar > 0 and prev_rev and prev_rev > 0:
                        ar_gi = ar / prev_ar
                        rev_gi = rev / prev_rev
                        # DSRI简化
                        dsri = ar_gi / rev_gi if rev_gi > 0 else 1
                        # 如果DSRI > 1.46 且利润为正，M-score可能异常
                        if dsri > 1.46:
                            mscore = -1.5  # 接近阈值
                        if dsri > 2.0:
                            mscore = -1.0  # 超过阈值

            risk["mscore"] = {
                "m_score": round(mscore, 2),
                "threshold": -1.78,
                "manipulator": mscore > -1.78,
                "diagnosis": "可能存在盈余操纵" if mscore > -1.78 else "正常",
            }

        except Exception as e:
            logger.error(f"风险模型计算异常: {e}")

        return risk

    # ========================================================================
    # 估值
    # ========================================================================
    @staticmethod
    def _build_valuation(data: dict) -> dict:
        """估值分析"""
        val = {}

        basic = data.get("basic")
        income = data.get("income")
        balance = data.get("balance")

        if basic is None or len(basic) < 5:
            return val

        try:
            # PE历史分位
            if income is not None and len(income) > 0:
                np_val = ReportBuilder._val(income.iloc[0], ["net_profit", "净利润"])
                if np_val and np_val > 0:
                    pe_list = []
                    for i in range(len(basic)):
                        close = ReportBuilder._val(basic.iloc[i], ["close", "收盘价"])
                        share = ReportBuilder._val(basic.iloc[i], ["total_share", "总股本"])
                        if close and share and share > 0:
                            pe = close * share / (np_val * 10000)
                            if 0 < pe < 300:
                                pe_list.append(pe)
                    if pe_list:
                        current_pe = pe_list[-1]
                        pct = sum(1 for p in pe_list if p <= current_pe) / len(pe_list) * 100
                        val["pe_percentile"] = {
                            "current": round(current_pe, 2),
                            "percentile": round(pct, 1),
                            "avg": round(np.mean(pe_list), 2),
                            "min": round(min(pe_list), 2),
                            "max": round(max(pe_list), 2),
                        }

            # PB历史分位
            if balance is not None and len(balance) > 0:
                eq = ReportBuilder._val(balance.iloc[0], ["total_equity", "股东权益合计"])
                if eq and eq > 0:
                    pb_list = []
                    for i in range(len(basic)):
                        close = ReportBuilder._val(basic.iloc[i], ["close", "收盘价"])
                        share = ReportBuilder._val(basic.iloc[i], ["total_share", "总股本"])
                        if close and share and share > 0:
                            pb = close * share / (eq * 10000)
                            if 0 < pb < 50:
                                pb_list.append(pb)
                    if pb_list:
                        current_pb = pb_list[-1]
                        pct = sum(1 for p in pb_list if p <= current_pb) / len(pb_list) * 100
                        val["pb_percentile"] = {
                            "current": round(current_pb, 2),
                            "percentile": round(pct, 1),
                            "avg": round(np.mean(pb_list), 2),
                        }

        except Exception as e:
            logger.error(f"估值分析异常: {e}")

        return val

    # ========================================================================
    # 现金流分析
    # ========================================================================
    @staticmethod
    def _build_cashflow(data: dict) -> dict:
        """现金流分析"""
        cf_analysis = {}

        cashflow = data.get("cashflow")
        if cashflow is None or len(cashflow) < 2:
            return cf_analysis

        try:
            quadrant = []
            for i in range(max(0, len(cashflow) - 3), len(cashflow)):
                row = cashflow.iloc[i]
                ocf = ReportBuilder._val(row, ["n_cashflow_act", "经营活动产生的现金流量净额"])
                icf = ReportBuilder._val(row, ["n_cashflow_inv_act", "投资活动产生的现金流量净额"])
                fcf = ReportBuilder._val(row, ["n_cash_flows_fnc_act", "筹资活动产生的现金流量净额"])

                if ocf is not None and icf is not None and fcf is not None:
                    # 判断象限
                    if ocf > 0 and icf < 0 and fcf < 0:
                        qtype = "奶牛型（经营造血+投资+偿债）"
                    elif ocf > 0 and icf < 0 and fcf > 0:
                        qtype = "成长型（经营造血+融资扩张）"
                    elif ocf > 0 and icf > 0 and fcf < 0:
                        qtype = "偿债型（经营+投资回收+偿债）"
                    elif ocf < 0 and icf < 0 and fcf > 0:
                        qtype = "烧钱型（依赖融资维持）"
                    elif ocf < 0 and icf > 0 and fcf > 0:
                        qtype = "衰退型（变卖资产+融资）"
                    else:
                        qtype = "混合型"

                    end_date = str(row.get("end_date", "")) if "end_date" in row.index else f"period_{i}"
                    quadrant.append({
                        "end_date": end_date,
                        "ocf": round(ocf, 2),
                        "icf": round(icf, 2),
                        "fcf": round(fcf, 2),
                        "quadrant_type": qtype,
                    })

            cf_analysis["quadrant"] = quadrant

        except Exception as e:
            logger.error(f"现金流分析异常: {e}")

        return cf_analysis

    # ========================================================================
    # 基础异常信号
    # ========================================================================
    @staticmethod
    def _build_anomaly_signals(data: dict) -> list:
        """基础异常信号（快速扫描，详细检测由 SignalDetector 做）"""
        signals = []

        balance = data.get("balance")
        income = data.get("income")
        if balance is None or income is None:
            return signals

        try:
            latest_bal = balance.iloc[0]
            ta = ReportBuilder._val(latest_bal, ["total_assets", "资产总计"])

            # 商誉占比
            gw = ReportBuilder._val(latest_bal, ["goodwill", "商誉"])
            eq = ReportBuilder._val(latest_bal, ["total_equity", "股东权益合计"])
            if gw and eq and eq > 0 and gw / eq > 0.3:
                signals.append({
                    "name": "商誉占比过高",
                    "level": "high" if gw / eq > 0.5 else "medium",
                    "data": f"商誉/净资产 = {gw/eq:.1%}",
                })

            # 应收增速异常
            if len(balance) >= 2 and len(income) >= 2:
                ar = ReportBuilder._val(latest_bal, ["accounts_receivable", "应收账款"])
                ar_prev = ReportBuilder._val(balance.iloc[-2], ["accounts_receivable", "应收账款"])
                rev = ReportBuilder._val(income.iloc[0], ["revenue", "营业收入"])
                rev_prev = ReportBuilder._val(income.iloc[-2], ["revenue", "营业收入"])
                if ar and ar_prev and ar_prev > 0 and rev and rev_prev and rev_prev > 0:
                    ar_g = (ar - ar_prev) / ar_prev
                    rev_g = (rev - rev_prev) / rev_prev
                    if ar_g > rev_g + 0.2:
                        signals.append({
                            "name": "应收账款异常增长",
                            "level": "medium",
                            "data": f"应收增速{ar_g:.1%} vs 营收增速{rev_g:.1%}",
                        })

        except Exception as e:
            logger.error(f"异常信号扫描异常: {e}")

        return signals

    # ========================================================================
    # 辅助
    # ========================================================================
    @staticmethod
    def _val(row, keys: list):
        """从行数据中获取值"""
        if row is None:
            return None
        for key in keys:
            if key in row.index:
                v = row[key]
                if pd.notna(v):
                    return float(v)
        return None
