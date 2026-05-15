"""
深度财务分析计算器 - 专业级分析模型
包含：杜邦分析、Altman Z-score、Piotroski F-score、Beneish M-score、
     自由现金流/DCF估值、现金流象限分析、经济护城河评估
"""
import pandas as pd
import numpy as np
from ..logging_config import get_logger

logger = get_logger(__name__)


class DeepAnalysisCalculator:
    """深度财务分析计算器"""

    # ========================================================================
    # 1. 杜邦分析 (DuPont Analysis)
    # ========================================================================

    @staticmethod
    def dupont_3factor(net_profit, revenue, total_assets, equity) -> dict:
        """
        三因素杜邦分解: ROE = 净利率 × 资产周转率 × 权益乘数

        Returns:
            {
                "roe": float,           # ROE (%)
                "net_margin": float,    # 净利率 (%)
                "asset_turnover": float, # 资产周转率 (次)
                "equity_multiplier": float, # 权益乘数
                "diagnosis": str,       # 诊断结论
            }
        """
        result = {
            "roe": None, "net_margin": None,
            "asset_turnover": None, "equity_multiplier": None,
            "diagnosis": "数据不足，无法分析",
        }

        if not all([revenue, total_assets, equity]) or revenue == 0 or equity == 0:
            return result

        net_margin = net_profit / revenue * 100 if net_profit is not None else None
        asset_turnover = revenue / total_assets
        equity_multiplier = total_assets / equity
        roe = net_profit / equity * 100 if net_profit is not None else None

        result["roe"] = roe
        result["net_margin"] = net_margin
        result["asset_turnover"] = asset_turnover
        result["equity_multiplier"] = equity_multiplier

        # 诊断 ROE 驱动因素
        if roe is not None:
            drivers = []
            if net_margin is not None and net_margin > 15:
                drivers.append("高利润率")
            if asset_turnover > 1.0:
                drivers.append("高资产周转")
            if equity_multiplier > 2.5:
                drivers.append("高财务杠杆")

            if not drivers:
                if net_margin is not None and net_margin < 5:
                    result["diagnosis"] = "低利润率型：盈利能力薄弱，需关注成本控制或产品定价"
                elif asset_turnover < 0.5:
                    result["diagnosis"] = "低周转型：资产利用效率低，需关注资产运营效率"
                else:
                    result["diagnosis"] = "均衡型：各因子表现一般，无突出驱动因素"
            elif len(drivers) == 1:
                result["diagnosis"] = f"{drivers[0]}驱动型：ROE 主要由{drivers[0]}贡献"
            else:
                result["diagnosis"] = f"复合驱动型：{' + '.join(drivers)}共同驱动 ROE"

        return result

    @staticmethod
    def dupont_5factor(net_profit, revenue, total_assets, equity,
                       ebit, interest_expense, tax_expense, pre_tax_profit) -> dict:
        """
        五因素杜邦分解:
        ROE = 税负效应 × 利息效应 × EBIT利润率 × 资产周转率 × 权益乘数

        Returns:
            扩展的杜邦分解结果
        """
        result = DeepAnalysisCalculator.dupont_3factor(
            net_profit, revenue, total_assets, equity
        )
        result["tax_burden"] = None
        result["interest_burden"] = None
        result["ebit_margin"] = None

        if pre_tax_profit and pre_tax_profit != 0 and net_profit is not None:
            result["tax_burden"] = net_profit / pre_tax_profit  # 税负效应

        if ebit and pre_tax_profit is not None and ebit != 0:
            result["interest_burden"] = pre_tax_profit / ebit  # 利息效应

        if ebit and revenue and revenue > 0:
            result["ebit_margin"] = ebit / revenue * 100  # EBIT利润率

        return result

    @staticmethod
    def dupont_trend(periods_data: list) -> dict:
        """
        杜邦分析趋势（多年对比）

        Args:
            periods_data: list of dict，每个 dict 包含:
                {"end_date", "net_profit", "revenue", "total_assets", "equity"}

        Returns:
            趋势分析结果
        """
        results = []
        for period in periods_data:
            r = DeepAnalysisCalculator.dupont_3factor(
                period.get("net_profit"), period.get("revenue"),
                period.get("total_assets"), period.get("equity"),
            )
            r["end_date"] = period.get("end_date", "N/A")
            results.append(r)

        # 趋势判断
        roes = [r["roe"] for r in results if r["roe"] is not None]
        trends = {}
        if len(roes) >= 2:
            if roes[0] > roes[-1] * 1.1:
                trends["roe_trend"] = "上升"
            elif roes[0] < roes[-1] * 0.9:
                trends["roe_trend"] = "下降"
            else:
                trends["roe_trend"] = "稳定"

        return {"periods": results, "trends": trends}

    # ========================================================================
    # 2. Altman Z-score 破产预测模型
    # ========================================================================

    @staticmethod
    def altman_zscore(total_assets, working_capital, retained_earnings,
                      ebit, market_cap, total_liab, revenue,
                      is_manufacturer=True) -> dict:
        """
        Altman Z-score 破产预测

        Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5

        Args:
            total_assets: 总资产
            working_capital: 营运资本 (流动资产 - 流动负债)
            retained_earnings: 留存收益
            ebit: 息税前利润
            market_cap: 权益市值 (总市值)
            total_liab: 总负债
            revenue: 营业收入
            is_manufacturer: 是否制造业（影响阈值）

        Returns:
            {"z_score", "zone", "zone_cn", "components", "details"}
        """
        result = {
            "z_score": None, "zone": "unknown", "zone_cn": "未知",
            "components": {}, "details": [],
        }

        if not total_assets or total_assets == 0:
            result["details"].append("总资产数据缺失")
            return result

        x1 = working_capital / total_assets if working_capital is not None else 0
        x2 = retained_earnings / total_assets if retained_earnings is not None else 0
        x3 = ebit / total_assets if ebit is not None else 0
        x4 = market_cap / total_liab if market_cap and total_liab and total_liab > 0 else 0
        x5 = revenue / total_assets if revenue is not None else 0

        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

        result["z_score"] = z
        result["components"] = {
            "X1_营运资本/总资产": x1,
            "X2_留存收益/总资产": x2,
            "X3_EBIT/总资产": x3,
            "X4_权益市值/总负债": x4,
            "X5_营收/总资产": x5,
        }

        # 判定区域 (制造业标准)
        if is_manufacturer:
            if z > 2.99:
                result["zone"] = "safe"
                result["zone_cn"] = "安全区"
                result["details"].append("Z-score > 2.99，财务状况良好，破产风险低")
            elif z > 1.81:
                result["zone"] = "grey"
                result["zone_cn"] = "灰色区"
                result["details"].append("Z-score 在 1.81-2.99 之间，财务状况不确定，需关注")
            else:
                result["zone"] = "distress"
                result["zone_cn"] = "危险区"
                result["details"].append("Z-score < 1.81，财务困境风险较高")
        else:
            # 非制造业/服务业阈值
            if z > 2.60:
                result["zone"] = "safe"
                result["zone_cn"] = "安全区"
            elif z > 1.10:
                result["zone"] = "grey"
                result["zone_cn"] = "灰色区"
            else:
                result["zone"] = "distress"
                result["zone_cn"] = "危险区"

        return result

    # ========================================================================
    # 3. Piotroski F-score 财务健康评分 (0-9)
    # ========================================================================

    @staticmethod
    def piotroski_fscore(current: dict, previous: dict, prev2: dict = None) -> dict:
        """
        Piotroski F-score (9分制)

        Args:
            current: 最新期数据 dict
                {net_profit, op_cashflow, total_assets, total_liab,
                 current_assets, current_liab, shares, gross_margin, revenue,
                 total_equity, retained_earnings}
            previous: 上一期数据
            prev2: 上两期数据（用于判断趋势）

        Returns:
            {"score": int(0-9), "details": list, "profit_score", "leverage_score", "efficiency_score"}
        """
        score = 0
        details = []
        profit_score = 0
        leverage_score = 0
        efficiency_score = 0

        # --- 盈利性 (4分) ---

        # 1. ROA > 0 (1分)
        roa = None
        if current.get("net_profit") is not None and current.get("total_assets"):
            roa = current["net_profit"] / current["total_assets"]
            if roa > 0:
                score += 1; profit_score += 1
                details.append("✓ ROA 为正 (+1)")
            else:
                details.append("✗ ROA 为负 (0)")

        # 2. 经营现金流 > 0 (1分)
        op_cf = current.get("op_cashflow")
        if op_cf is not None:
            if op_cf > 0:
                score += 1; profit_score += 1
                details.append("✓ 经营现金流为正 (+1)")
            else:
                details.append("✗ 经营现金流为负 (0)")

        # 3. ROA 上升 (1分)
        if previous and previous.get("total_assets"):
            prev_roa = previous.get("net_profit", 0) / previous["total_assets"] if previous.get("net_profit") is not None else None
            if roa is not None and prev_roa is not None and roa > prev_roa:
                score += 1; profit_score += 1
                details.append("✓ ROA 同比上升 (+1)")
            else:
                details.append("✗ ROA 同比未上升 (0)")

        # 4. 现金流 > 净利润 (应计质量) (1分)
        if op_cf is not None and current.get("net_profit") is not None:
            if op_cf > current["net_profit"]:
                score += 1; profit_score += 1
                details.append("✓ 经营现金流 > 净利润，盈利质量好 (+1)")
            else:
                details.append("✗ 经营现金流 ≤ 净利润 (0)")

        # --- 杠杆/流动性 (3分) ---

        # 5. 负债率下降 (1分)
        cur_debt_ratio = DeepAnalysisCalculator._safe_ratio(
            current.get("total_liab"), current.get("total_assets"))
        prev_debt_ratio = DeepAnalysisCalculator._safe_ratio(
            previous.get("total_liab"), previous.get("total_assets")) if previous else None
        if cur_debt_ratio is not None and prev_debt_ratio is not None:
            if cur_debt_ratio < prev_debt_ratio:
                score += 1; leverage_score += 1
                details.append("✓ 资产负债率同比下降 (+1)")
            else:
                details.append("✗ 资产负债率未下降 (0)")

        # 6. 流动比率上升 (1分)
        cur_cr = DeepAnalysisCalculator._safe_ratio(
            current.get("current_assets"), current.get("current_liab"))
        prev_cr = DeepAnalysisCalculator._safe_ratio(
            previous.get("current_assets"), previous.get("current_liab")) if previous else None
        if cur_cr is not None and prev_cr is not None:
            if cur_cr > prev_cr:
                score += 1; leverage_score += 1
                details.append("✓ 流动比率同比上升 (+1)")
            else:
                details.append("✗ 流动比率未上升 (0)")

        # 7. 未发新股 (1分) — A股暂用简化判断
        cur_shares = current.get("shares")
        prev_shares = previous.get("shares") if previous else None
        if cur_shares is not None and prev_shares is not None:
            if cur_shares <= prev_shares * 1.01:  # 1%容差
                score += 1; leverage_score += 1
                details.append("✓ 未大规模增发新股 (+1)")
            else:
                details.append("✗ 有增发新股 (0)")
        else:
            # 无法判断时默认给分（保守估计）
            score += 1; leverage_score += 1
            details.append("○ 增发信息不详，默认 (+1)")

        # --- 运营效率 (2分) ---

        # 8. 毛利率上升 (1分)
        cur_gm = DeepAnalysisCalculator._calc_margin(
            current.get("revenue"), current.get("gross_margin"), "gross")
        prev_gm = DeepAnalysisCalculator._calc_margin(
            previous.get("revenue"), previous.get("gross_margin"), "gross") if previous else None
        if cur_gm is not None and prev_gm is not None:
            if cur_gm > prev_gm:
                score += 1; efficiency_score += 1
                details.append("✓ 毛利率同比上升 (+1)")
            else:
                details.append("✗ 毛利率未上升 (0)")

        # 9. 资产周转率上升 (1分)
        cur_at = DeepAnalysisCalculator._safe_ratio(
            current.get("revenue"), current.get("total_assets"))
        prev_at = DeepAnalysisCalculator._safe_ratio(
            previous.get("revenue"), previous.get("total_assets")) if previous else None
        if cur_at is not None and prev_at is not None:
            if cur_at > prev_at:
                score += 1; efficiency_score += 1
                details.append("✓ 资产周转率同比上升 (+1)")
            else:
                details.append("✗ 资产周转率未上升 (0)")

        # 诊断
        if score >= 8:
            diagnosis = "财务状况优秀，各项指标全面改善"
        elif score >= 6:
            diagnosis = "财务状况良好，大部分指标改善"
        elif score >= 4:
            diagnosis = "财务状况一般，部分指标需关注"
        else:
            diagnosis = "财务状况较弱，多项指标恶化，需谨慎"

        return {
            "score": score,
            "profit_score": profit_score,
            "leverage_score": leverage_score,
            "efficiency_score": efficiency_score,
            "details": details,
            "diagnosis": diagnosis,
        }

    # ========================================================================
    # 4. Beneish M-score 盈余管理检测
    # ========================================================================

    @staticmethod
    def beneish_mscore(current: dict, previous: dict) -> dict:
        """
        Beneish M-score 盈余管理检测

        M = -4.84 + 0.920×DSRI + 0.528×GMI + 0.404×AQI + 0.892×SGI
            + 0.115×DEPI - 0.172×SGAI + 4.679×TATA - 0.327×LVGI

        需要至少2年数据

        Args:
            current: 最新期 {revenue, accounts_receivable, gross_profit, total_assets,
                     current_assets, net_ppe, depreciation, sga_expense, total_liab,
                     current_liab, cash, other_assets, net_profit, op_cashflow}
            previous: 上一期对应数据

        Returns:
            {"m_score", "manipulator", "components", "details"}
        """
        result = {
            "m_score": None, "manipulator": False,
            "components": {}, "details": [],
        }

        # 计算各指标
        try:
            # DSRI - 应收账款天数指数
            _cur_ar_ratio = DeepAnalysisCalculator._safe_divide(
                current.get("accounts_receivable"), current.get("revenue"))
            _prev_ar_ratio = DeepAnalysisCalculator._safe_divide(
                previous.get("accounts_receivable"), previous.get("revenue"))
            cur_ar_days = _cur_ar_ratio * 365 if _cur_ar_ratio is not None else None
            prev_ar_days = _prev_ar_ratio * 365 if _prev_ar_ratio is not None else None
            dsri = cur_ar_days / prev_ar_days if cur_ar_days and prev_ar_days and prev_ar_days != 0 else 1.0

            # GMI - 毛利率指数
            cur_gm = DeepAnalysisCalculator._calc_margin(
                current.get("revenue"), current.get("gross_profit"), "gross")
            prev_gm = DeepAnalysisCalculator._calc_margin(
                previous.get("revenue"), previous.get("gross_profit"), "gross")
            gmi = prev_gm / cur_gm if cur_gm and prev_gm and cur_gm != 0 else 1.0

            # AQI - 资产质量指数
            _cur_ratio = DeepAnalysisCalculator._safe_divide(
                (current.get("current_assets") or 0) + (current.get("net_ppe") or 0),
                current.get("total_assets"))
            _prev_ratio = DeepAnalysisCalculator._safe_divide(
                (previous.get("current_assets") or 0) + (previous.get("net_ppe") or 0),
                previous.get("total_assets"))
            cur_aqi = (1 - _cur_ratio) if _cur_ratio is not None else None
            prev_aqi = (1 - _prev_ratio) if _prev_ratio is not None else None
            aqi = cur_aqi / prev_aqi if cur_aqi and prev_aqi and prev_aqi != 0 else 1.0

            # SGI - 营收增长指数
            sgi = DeepAnalysisCalculator._safe_divide(
                current.get("revenue"), previous.get("revenue")) or 1.0

            # DEPI - 折旧率指数
            _cur_dep = current.get("depreciation") or 0
            _cur_ppe = current.get("net_ppe") or 0
            _prev_dep = previous.get("depreciation") or 0
            _prev_ppe = previous.get("net_ppe") or 0
            cur_depi = DeepAnalysisCalculator._safe_divide(_cur_dep, _cur_dep + _cur_ppe)
            prev_depi = DeepAnalysisCalculator._safe_divide(_prev_dep, _prev_dep + _prev_ppe)
            depi = prev_depi / cur_depi if cur_depi and prev_depi and cur_depi != 0 else 1.0

            # SGAI - 销管费用指数
            cur_sgai = DeepAnalysisCalculator._safe_divide(
                current.get("sga_expense"), current.get("revenue"))
            prev_sgai = DeepAnalysisCalculator._safe_divide(
                previous.get("sga_expense"), previous.get("revenue"))
            sgai = cur_sgai / prev_sgai if cur_sgai and prev_sgai and prev_sgai != 0 else 1.0

            # LVGI - 杠杆指数
            cur_lvgi = DeepAnalysisCalculator._safe_divide(
                current.get("total_liab"), current.get("total_assets"))
            prev_lvgi = DeepAnalysisCalculator._safe_divide(
                previous.get("total_liab"), previous.get("total_assets"))
            lvgi = cur_lvgi / prev_lvgi if cur_lvgi and prev_lvgi and prev_lvgi != 0 else 1.0

            # TATA - 应计项目比率
            _np = current.get("net_profit") or 0
            _ocf = current.get("op_cashflow") or 0
            tata = DeepAnalysisCalculator._safe_divide(_np - _ocf, current.get("total_assets"))

            # 保护 None 值，用 1.0 作为中性默认值
            dsri = dsri if dsri is not None else 1.0
            gmi = gmi if gmi is not None else 1.0
            aqi = aqi if aqi is not None else 1.0
            sgi = sgi if sgi is not None else 1.0
            depi = depi if depi is not None else 1.0
            sgai = sgai if sgai is not None else 1.0
            lvgi = lvgi if lvgi is not None else 1.0
            tata = tata if tata is not None else 0.0

            m = (-4.84
                 + 0.920 * dsri
                 + 0.528 * gmi
                 + 0.404 * aqi
                 + 0.892 * sgi
                 + 0.115 * depi
                 - 0.172 * sgai
                 + 4.679 * tata
                 - 0.327 * lvgi)

            result["m_score"] = m
            result["manipulator"] = m > -1.78
            result["components"] = {
                "DSRI_应收天数指数": round(dsri, 4),
                "GMI_毛利率指数": round(gmi, 4),
                "AQI_资产质量指数": round(aqi, 4),
                "SGI_营收增长指数": round(sgi, 4),
                "DEPI_折旧率指数": round(depi, 4),
                "SGAI_销管费用指数": round(sgai, 4),
                "LVGI_杠杆指数": round(lvgi, 4),
                "TATA_应计比率": round(tata, 4) if tata else 0,
            }

            if m > -1.78:
                result["details"].append(f"M-score = {m:.2f} > -1.78，存在盈余管理嫌疑")
                if dsri > 1.4:
                    result["details"].append("  → 应收账款天数异常增长，可能存在收入确认激进")
                if gmi > 1.2:
                    result["details"].append("  → 毛利率下降明显，成本压力增大")
                if sgi > 1.5:
                    result["details"].append("  → 营收增速异常高，需关注可持续性")
                if tata and tata > 0.05:
                    result["details"].append("  → 应计利润占比高，现金流质量需关注")
            else:
                result["details"].append(f"M-score = {m:.2f} ≤ -1.78，盈余管理风险较低")

        except Exception as e:
            logger.error(f"Beneish M-score 计算异常: {e}")
            result["details"].append(f"计算异常: {str(e)}")

        return result

    # ========================================================================
    # 5. 自由现金流 / DCF 估值
    # ========================================================================

    @staticmethod
    def free_cash_flow(op_cashflow, capex) -> dict:
        """
        自由现金流计算

        FCFF = 经营活动现金流 - 资本支出
        """
        fcf = None
        if op_cashflow is not None and capex is not None:
            fcf = op_cashflow - abs(capex)
        elif op_cashflow is not None:
            fcf = op_cashflow  # 无资本支出数据时用经营现金流近似

        result = {"fcf": fcf, "op_cashflow": op_cashflow, "capex": capex}
        if fcf is not None:
            result["fcf_positive"] = fcf > 0
            result["fcf_margin"] = None  # 需要外部计算
        return result

    @staticmethod
    def fcf_trend(periods_data: list) -> dict:
        """
        自由现金流趋势分析

        Args:
            periods_data: list of {"end_date", "op_cashflow", "capex", "revenue"}
        """
        fcfs = []
        for p in periods_data:
            op_cf = p.get("op_cashflow")
            capex = p.get("capex")
            revenue = p.get("revenue")
            fcf = DeepAnalysisCalculator.free_cash_flow(op_cf, capex)
            fcf["end_date"] = p.get("end_date", "N/A")
            fcf["fcf_margin"] = (fcf["fcf"] / revenue * 100) if fcf["fcf"] and revenue and revenue > 0 else None
            fcfs.append(fcf)

        # 趋势
        fcf_values = [f["fcf"] for f in fcfs if f["fcf"] is not None]
        trend = "数据不足"
        if len(fcf_values) >= 2:
            if all(f > 0 for f in fcf_values):
                if fcf_values[0] > fcf_values[-1]:
                    trend = "自由现金流持续为正且增长"
                else:
                    trend = "自由现金流持续为正但下降"
            elif all(f < 0 for f in fcf_values):
                trend = "自由现金流持续为负，处于投入期或经营困难"
            elif fcf_values[0] > 0 and fcf_values[-1] < 0:
                trend = "自由现金流由正转负，需关注"
            elif fcf_values[0] < 0 and fcf_values[-1] > 0:
                trend = "自由现金流由负转正，经营改善"
            else:
                trend = "自由现金流波动较大"

        return {"periods": fcfs, "trend": trend}

    @staticmethod
    def simple_dcf(fcf_latest, growth_rate_5y, growth_rate_terminal,
                   discount_rate, shares, years=5) -> dict:
        """
        简化 DCF 估值

        Args:
            fcf_latest: 最新自由现金流
            growth_rate_5y: 未来5年增长率 (%)
            growth_rate_terminal: 永续增长率 (%)
            discount_rate: 折现率/要求回报率 (%)
            shares: 总股本
            years: 预测年数

        Returns:
            {"intrinsic_value_per_share", "assumptions", "projected_fcfs"}
        """
        if not fcf_latest or fcf_latest <= 0 or not shares or shares <= 0:
            return {
                "intrinsic_value_per_share": None,
                "assumptions": {},
                "projected_fcfs": [],
                "error": "自由现金流为负或数据不足，无法进行 DCF 估值",
            }

        g1 = growth_rate_5y / 100
        g2 = growth_rate_terminal / 100
        r = discount_rate / 100

        # 预测期现金流
        projected = []
        fcf = fcf_latest
        for i in range(1, years + 1):
            fcf = fcf * (1 + g1)
            pv = fcf / ((1 + r) ** i)
            projected.append({"year": i, "fcf": fcf, "pv": pv})

        # 终值
        terminal_fcf = projected[-1]["fcf"] * (1 + g2)
        terminal_value = terminal_fcf / (r - g2) if r > g2 else 0
        terminal_pv = terminal_value / ((1 + r) ** years)

        # 企业价值
        pv_fcfs = sum(p["pv"] for p in projected)
        enterprise_value = pv_fcfs + terminal_pv

        # 每股价值（简化，未减去净债务）
        intrinsic_value = enterprise_value / shares

        return {
            "intrinsic_value_per_share": intrinsic_value,
            "enterprise_value": enterprise_value,
            "pv_projected_fcfs": pv_fcfs,
            "pv_terminal_value": terminal_pv,
            "projected_fcfs": projected,
            "assumptions": {
                "fcf_latest": fcf_latest,
                "growth_rate_5y": growth_rate_5y,
                "growth_rate_terminal": growth_rate_terminal,
                "discount_rate": discount_rate,
                "years": years,
            },
        }

    # ========================================================================
    # 6. 现金流象限分析
    # ========================================================================

    @staticmethod
    def cashflow_quadrant(op_cf, inv_cf, fin_cf) -> dict:
        """
        现金流象限分析 (8种组合)

        三大现金流正负组合 → 公司经营状态判断
        """
        op_sign = "+" if (op_cf or 0) >= 0 else "-"
        inv_sign = "+" if (inv_cf or 0) >= 0 else "-"
        fin_sign = "+" if (fin_cf or 0) >= 0 else "-"
        pattern = f"经营{op_sign}/投资{inv_sign}/筹资{fin_sign}"

        quadrant_map = {
            "经营+/投资+/筹资+": {"type": "成熟充裕型", "icon": "🟢",
                              "desc": "三大现金流均为正，公司经营成熟，投资收益好，同时还在融资。需关注融资目的。"},
            "经营+/投资+/筹资-": {"type": "成熟奶牛型", "icon": "🟢",
                              "desc": "经营和投资产生现金，同时偿还债务或分红。典型的成熟企业现金流特征。"},
            "经营+/投资-/筹资+": {"type": "扩张成长型", "icon": "🟡",
                              "desc": "经营产生现金，加大投资扩张，同时融资补充。成长期企业常见。"},
            "经营+/投资-/筹资-": {"type": "稳健发展型", "icon": "🟢",
                              "desc": "经营产生现金，投资扩张，同时偿债。现金流健康，自给自足。"},
            "经营-/投资+/筹资+": {"type": "融资维持型", "icon": "🟠",
                              "desc": "经营亏损，靠变卖资产和融资维持。处于困境或转型期，需关注持续性。"},
            "经营-/投资+/筹资-": {"type": "衰退收缩型", "icon": "🔴",
                              "desc": "经营亏损，变卖资产偿债。处于衰退期，风险较高。"},
            "经营-/投资-/筹资+": {"type": "烧钱扩张型", "icon": "🟠",
                              "desc": "经营和投资都在消耗现金，完全靠融资支撑。高风险高回报，需关注融资可持续性。"},
            "经营-/投资-/筹资-": {"type": "危机衰退型", "icon": "🔴",
                              "desc": "三大现金流均为负，公司处于严重困境。极高风险。"},
        }

        info = quadrant_map.get(pattern, {"type": "未知", "icon": "⚪", "desc": "数据不足"})

        return {
            "pattern": pattern,
            "type": info["type"],
            "icon": info["icon"],
            "description": info["desc"],
            "op_cf": op_cf, "inv_cf": inv_cf, "fin_cf": fin_cf,
        }

    @staticmethod
    def cashflow_quadrant_trend(periods_data: list) -> dict:
        """
        现金流象限趋势（多年）

        Args:
            periods_data: list of {"end_date", "op_cf", "inv_cf", "fin_cf"}
        """
        results = []
        for p in periods_data:
            q = DeepAnalysisCalculator.cashflow_quadrant(
                p.get("op_cf"), p.get("inv_cf"), p.get("fin_cf"))
            q["end_date"] = p.get("end_date", "N/A")
            results.append(q)

        types = [r["type"] for r in results]
        if len(types) >= 2 and types[0] != types[-1]:
            trend = f"从「{types[-1]}」转变为「{types[0]}」"
        else:
            trend = f"持续为「{types[0]}」" if types else "数据不足"

        return {"periods": results, "trend": trend}

    # ========================================================================
    # 7. 经济护城河评估
    # ========================================================================

    @staticmethod
    def economic_moat(periods_data: list) -> dict:
        """
        经济护城河评估

        Args:
            periods_data: list of {"end_date", "net_profit", "revenue", "op_cost",
                          "total_assets", "equity"} (近5年)

        Returns:
            {"moat_score", "moat_type", "factors", "details"}
        """
        factors = {}
        details = []
        total_score = 0

        if len(periods_data) < 2:
            return {"moat_score": 0, "moat_type": "数据不足", "factors": {}, "details": ["需要至少2年数据"]}

        # 1. 毛利率稳定性 (0-25分)
        gross_margins = []
        for p in periods_data:
            rev = p.get("revenue")
            cost = p.get("op_cost")
            if rev and cost and rev > 0:
                gross_margins.append((rev - cost) / rev * 100)

        if len(gross_margins) >= 2:
            avg_gm = np.mean(gross_margins)
            std_gm = np.std(gross_margins)
            cv = std_gm / avg_gm if avg_gm > 0 else 999  # 变异系数

            gm_score = 0
            if avg_gm > 40 and cv < 0.15:
                gm_score = 25
                details.append(f"✓ 毛利率均值 {avg_gm:.1f}%，变异系数 {cv:.2f}，高且稳定")
            elif avg_gm > 30 and cv < 0.20:
                gm_score = 20
                details.append(f"✓ 毛利率均值 {avg_gm:.1f}%，较高且相对稳定")
            elif avg_gm > 20:
                gm_score = 12
                details.append(f"○ 毛利率均值 {avg_gm:.1f}%，处于正常水平")
            else:
                gm_score = 5
                details.append(f"⚠ 毛利率均值 {avg_gm:.1f}%，偏低")
            factors["毛利率稳定性"] = gm_score
            total_score += gm_score

        # 2. ROE 持续性 (0-25分)
        roes = []
        for p in periods_data:
            np_val = p.get("net_profit")
            eq = p.get("equity")
            if np_val and eq and eq > 0:
                roes.append(np_val / eq * 100)

        if roes:
            high_roe_years = sum(1 for r in roes if r > 15)
            avg_roe = np.mean(roes)

            roe_score = 0
            if high_roe_years >= 4 and avg_roe > 20:
                roe_score = 25
                details.append(f"✓ 连续 {high_roe_years} 年 ROE > 15%，均值 {avg_roe:.1f}%，护城河宽")
            elif high_roe_years >= 3:
                roe_score = 18
                details.append(f"✓ {high_roe_years} 年 ROE > 15%，盈利能力较强")
            elif high_roe_years >= 1:
                roe_score = 10
                details.append(f"○ {high_roe_years} 年 ROE > 15%，盈利能力一般")
            else:
                roe_score = 3
                details.append(f"⚠ 无年份 ROE > 15%，盈利能力较弱")
            factors["ROE持续性"] = roe_score
            total_score += roe_score

        # 3. 营收增长稳定性 (0-25分)
        revenues = [p.get("revenue") for p in periods_data if p.get("revenue")]
        rev_score = 0
        if len(revenues) >= 2:
            growth_rates = []
            for i in range(len(revenues) - 1):
                if revenues[i + 1] and revenues[i + 1] > 0:
                    growth_rates.append((revenues[i] - revenues[i + 1]) / revenues[i + 1] * 100)

            if growth_rates:
                avg_growth = np.mean(growth_rates)
                positive_years = sum(1 for g in growth_rates if g > 0)

                if avg_growth > 15 and positive_years == len(growth_rates):
                    rev_score = 25
                    details.append(f"✓ 营收 CAGR {avg_growth:.1f}%，持续高增长")
                elif avg_growth > 8 and positive_years >= len(growth_rates) * 0.7:
                    rev_score = 18
                    details.append(f"✓ 营收均增 {avg_growth:.1f}%，增长稳健")
                elif avg_growth > 0:
                    rev_score = 10
                    details.append(f"○ 营收均增 {avg_growth:.1f}%，增长缓慢")
                else:
                    rev_score = 3
                    details.append(f"⚠ 营收均增 {avg_growth:.1f}%，呈下滑趋势")
            factors["营收增长稳定性"] = rev_score
            total_score += rev_score

        # 4. 净利率趋势 (0-25分)
        net_margins = []
        for p in periods_data:
            np_val = p.get("net_profit")
            rev = p.get("revenue")
            if np_val is not None and rev and rev > 0:
                net_margins.append(np_val / rev * 100)

        nm_score = 0
        if len(net_margins) >= 2:
            avg_nm = np.mean(net_margins)
            if net_margins[0] > net_margins[-1] * 1.05 and avg_nm > 10:
                nm_score = 25
                details.append(f"✓ 净利率均值 {avg_nm:.1f}%，趋势上升")
            elif avg_nm > 8:
                nm_score = 18
                details.append(f"✓ 净利率均值 {avg_nm:.1f}%，盈利能力较强")
            elif avg_nm > 3:
                nm_score = 10
                details.append(f"○ 净利率均值 {avg_nm:.1f}%，盈利能力一般")
            else:
                nm_score = 3
                details.append(f"⚠ 净利率均值 {avg_nm:.1f}%，盈利能力较弱")
            factors["净利率趋势"] = nm_score
            total_score += nm_score

        # 护城河判定
        if total_score >= 80:
            moat_type = "宽护城河"
        elif total_score >= 60:
            moat_type = "窄护城河"
        elif total_score >= 40:
            moat_type = "有限竞争优势"
        else:
            moat_type = "无明显护城河"

        return {
            "moat_score": total_score,
            "moat_type": moat_type,
            "factors": factors,
            "details": details,
        }

    # ========================================================================
    # 辅助方法
    # ========================================================================

    @staticmethod
    def _safe_divide(a, b):
        if a is None or b is None or b == 0:
            return None
        try:
            return a / b
        except (TypeError, ZeroDivisionError):
            return None

    @staticmethod
    def _safe_ratio(a, b):
        return DeepAnalysisCalculator._safe_divide(a, b)

    @staticmethod
    def _calc_margin(revenue, value, margin_type="gross"):
        if revenue is None or value is None:
            return None
        try:
            if not revenue or revenue == 0:
                return None
            return value / revenue * 100
        except (TypeError, ZeroDivisionError):
            return None
