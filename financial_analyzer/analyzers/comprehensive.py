"""
综合投资分析器 — FA Pro v11
=========================
7维金字塔分析调度层：
  1. 并行运行所有独立分析器
  2. 收集结构化的 ScoreCard
  3. 计算加权综合评分
  4. 运行DCF估值
  5. 生成 InvestmentThesis

继承自哈佛分析框架的四维结构，
融合《Python大数据财务分析》的双重评分体系。
"""
from __future__ import annotations
from dataclasses import dataclass
import logging
from typing import Any
import numpy as np

from .results import (
    MarketResult, AuditStructuredResult, FinancialHealthResult,
    ProfitabilityResult, GrowthQualityResult, ValuationResult,
    InvestmentThesis,
)
from ..calculator.scoring import UnifiedScorer, ScoreCard
from ..calculator.dcf_valuation import DCFValuator, DCFResult
from ..calculator.scenario import ScenarioAnalyzer

logger = logging.getLogger(__name__)

# 7维权重
DIMENSION_WEIGHTS = {
    "business": 0.05,            # L1: 商业模式基础分（权重最低，依赖定性判断）
    "accounting_quality": 0.15,  # L2: 会计质量（欺诈检测很重要）
    "financial_health": 0.20,    # L3: 财务健康（核心）
    "profitability": 0.20,       # L4: 盈利能力（核心）
    "growth_quality": 0.20,      # L5: 成长与质量（核心）
    "valuation": 0.20,           # L6: 估值（核心）
}


class ComprehensiveAnalyzer:
    """
    综合投资分析器

    用法:
        analyzer = ComprehensiveAnalyzer(data, stock_code, adapter, cache)
        thesis = analyzer.analyze()
        print(thesis.overall_rating)  # "推荐 ★★★★"
    """

    def __init__(self, data: dict, stock_code: str,
                 data_adapter=None, cache_manager=None):
        self.data = data
        self.stock_code = stock_code
        self.adapter = data_adapter
        self.cache = cache_manager
        self.scorer = UnifiedScorer()
        self.dcf = DCFValuator()
        self.scenario = ScenarioAnalyzer()

    def analyze(self) -> InvestmentThesis:
        """
        执行完整的7维投资分析

        返回 InvestmentThesis 包含：
        - 综合评级和评分
        - 7个维度的独立评分
        - DCF公允价值区间
        - 投资亮点和风险提示
        - 核心指标摘要
        - 雷达图数据
        """
        thesis = InvestmentThesis(
            stock_code=self.stock_code,
            company_name=self._get_company_name(),
            industry=self._get_industry(),
        )

        # ==== L1: 商业基础画像 ====
        market = self._analyze_l1_market()

        # ==== L2: 会计质量 ====
        audit = self._analyze_l2_accounting()

        # ==== L3: 财务健康 ====
        health = self._analyze_l3_financial_health()

        # ==== L4: 盈利能力 ====
        profit = self._analyze_l4_profitability()

        # ==== L5: 成长与质量 ====
        growth = self._analyze_l5_growth_quality()

        # ==== L6: 估值 ====
        valuation = self._analyze_l6_valuation(market, profit, growth)

        # ==== L7: 综合评分 ====
        thesis = self._synthesize(thesis, market, audit, health,
                                  profit, growth, valuation)

        return thesis

    # ========================================================================
    # L1: 商业基础画像
    # ========================================================================

    def _analyze_l1_market(self) -> MarketResult:
        """商业基础画像：从 data 中提取市场和公司基本信息"""
        result = MarketResult(stock_code=self.stock_code)

        # 公司名称
        basic = self.data.get("basic")
        stock_basic = self.data.get("stock_basic")

        if stock_basic is not None and not stock_basic.empty:
            sb = stock_basic.iloc[0]
            result.company_name = str(sb.get("name", sb.get("NAME", "")))
            result.industry = str(sb.get("industry", sb.get("所属行业", "")))

        if basic is not None and not basic.empty:
            b = basic.iloc[0]
            if not result.company_name:
                result.company_name = str(b.get("name", ""))
            result.pe_ttm = self._safe_float(b.get("pe")) or self._safe_float(b.get("pe_ttm")) or 0
            result.pb = self._safe_float(b.get("pb")) or 0
            result.market_cap_yi = round(
                (self._safe_float(b.get("total_mv")) or 0) / 1e8, 2
            )

        # 价格
        daily = self.data.get("daily")
        if daily is not None and not daily.empty and "close" in daily.columns:
            result.current_price = float(daily["close"].iloc[0])
            if len(daily) > 1:
                prev = float(daily["close"].iloc[1])
                if prev > 0:
                    result.price_change_pct = round(
                        (result.current_price - prev) / prev * 100, 2
                    )
            # 年化波动率
            if len(daily) >= 20 and "close" in daily.columns:
                returns = daily["close"].pct_change().dropna()
                if len(returns) > 0:
                    result.volatility_annual = round(
                        float(returns.std()) * np.sqrt(252) * 100, 1
                    )

        if daily is not None and not daily.empty and "vol" in daily.columns:
            result.volume = float(daily["vol"].iloc[0])

        return result

    # ========================================================================
    # L2: 会计质量审查
    # ========================================================================

    def _analyze_l2_accounting(self) -> AuditStructuredResult:
        """会计质量：运行32信号欺诈检测"""
        try:
            from .audit import AuditAnalyzer
            analyzer = AuditAnalyzer(
                self.data, self.stock_code, self.adapter, self.cache
            )
            audit_result = analyzer.get_audit_result()

            return AuditStructuredResult(
                total_score=round(float(audit_result.total_score), 1),
                risk_level=str(audit_result.risk_level),
                risk_icon=str(audit_result.risk_icon),
                total_signals=len(audit_result.all_signals),
                high_signals=audit_result.high_count,
                medium_signals=audit_result.medium_count,
                low_signals=audit_result.low_count,
                dimensions={
                    k: {"score": v.score, "signals": len(v.signals)}
                    for k, v in audit_result.dimensions.items()
                },
                signals_detail=[
                    {
                        "name": s.name,
                        "level": s.level.value,
                        "category": str(s.category),
                        "value": s.value,
                        "conclusion": s.conclusion,
                    }
                    for s in audit_result.all_signals
                ],
                radar_data=audit_result.radar_data or {},
                heatmap_data=audit_result.heatmap_data or [],
                recommendations=audit_result.recommendations or [],
            )
        except Exception as e:
            logger.warning(f"L2 会计质量分析失败: {e}")
            return AuditStructuredResult(total_score=60, risk_level="未知")

    # ========================================================================
    # L3: 财务健康
    # ========================================================================

    def _analyze_l3_financial_health(self) -> FinancialHealthResult:
        """财务健康：运行比率分析 + 统一评分"""
        try:
            from .financial_ratios import FinancialRatioAnalyzer
            fra = FinancialRatioAnalyzer(self.data, self.stock_code)
            ratios = fra.analyze()  # 返回结构化 dict

            # 提取各维度的评级并转换为分数
            def rating_to_score(rating: str) -> float:
                mapping = {
                    "优秀": 90, "良好": 75, "一般": 55,
                    "较差": 35, "风险": 20, "高速增长": 90,
                    "快速增长": 75, "稳定增长": 55, "低增长": 35,
                    "下滑": 20, "低估": 85, "合理": 65, "偏高": 40,
                    "高估": 20, "亏损": 10, "数据不足": 30,
                }
                return mapping.get(rating, 50)

            prof_score = rating_to_score(
                ratios.get("盈利能力", {}).get("评级", "一般")
            )
            solv_score = rating_to_score(
                ratios.get("偿债能力", {}).get("评级", "一般")
            )
            eff_score = rating_to_score(
                ratios.get("营运能力", {}).get("评级", "一般")
            )
            grow_score = rating_to_score(
                ratios.get("发展能力", {}).get("评级", "一般")
            )

            composite = round(
                prof_score * 0.30 + solv_score * 0.25 +
                eff_score * 0.20 + grow_score * 0.25
            )

            return FinancialHealthResult(
                profitability_score=prof_score,
                solvency_score=solv_score,
                efficiency_score=eff_score,
                growth_score=grow_score,
                composite_score=composite,
                rating=self._rating_label(composite),
                ratios=ratios,
            )
        except Exception as e:
            logger.warning(f"L3 财务健康分析失败: {e}")
            return FinancialHealthResult(composite_score=50, rating="数据不足")

    # ========================================================================
    # L4: 盈利能力
    # ========================================================================

    def _analyze_l4_profitability(self) -> ProfitabilityResult:
        """盈利能力：杜邦分解 + ROIC"""
        try:
            from .deep_analysis import DeepAnalyzer
            da = DeepAnalyzer(self.data, self.stock_code, self.adapter, self.cache)
            periods = da._build_periods_data(5)

            if not periods:
                return ProfitabilityResult(rating="数据不足")

            latest = periods[0]

            # ROE
            roe = self._safe_float(latest.get("roe")) or 0
            roe_trend = [
                self._safe_float(p.get("roe")) or 0
                for p in periods if self._safe_float(p.get("roe"))
            ]

            # 利润率
            gross_margin = self._safe_float(latest.get("gross_margin")) or 0
            net_margin = self._safe_float(latest.get("net_margin")) or 0
            op_margin = self._safe_float(latest.get("operating_margin")) or 0
            roa = self._safe_float(latest.get("roa")) or 0

            # 杜邦分解
            dupont = {
                "净利率": net_margin,
                "总资产周转率": self._safe_float(latest.get("asset_turnover")) or 0,
                "权益乘数": self._safe_float(latest.get("equity_multiplier")) or 0,
            }

            # 驱动类型判断
            if net_margin > 15:
                driver = "高利润率驱动"
            elif dupont["总资产周转率"] > 1.0:
                driver = "高周转驱动"
            elif dupont["权益乘数"] > 3:
                driver = "高杠杆驱动"
            else:
                driver = "均衡驱动"

            # 评分
            score = UnifiedScorer().composite([
                ScoreCard(dimension="ROE", category="盈利能力",
                          raw_value=roe, trend_score=0, peer_score=50,
                          absolute_score=min(roe / 20 * 100, 100)),
                ScoreCard(dimension="净利率", category="盈利能力",
                          raw_value=net_margin, trend_score=0, peer_score=50,
                          absolute_score=min(net_margin / 20 * 100, 100)),
            ])

            # 优劣势
            strengths = []
            weaknesses = []
            if roe > 15:
                strengths.append(f"ROE优秀({roe:.1f}%)")
            elif roe < 5:
                weaknesses.append(f"ROE偏低({roe:.1f}%)")
            if net_margin > 10:
                strengths.append(f"净利率良好({net_margin:.1f}%)")
            if gross_margin > 40:
                strengths.append(f"高毛利率({gross_margin:.1f}%)，品牌/技术壁垒")

            return ProfitabilityResult(
                roe=roe, roe_trend=roe_trend, roa=roa,
                gross_margin=gross_margin, net_margin=net_margin,
                operating_margin=op_margin,
                dupont_3factor=dupont, dupont_driver=driver,
                roic=self._estimate_roic(latest), roic_spread=0,
                score=score, rating=self._rating_label(score),
                strengths=strengths, weaknesses=weaknesses,
            )
        except Exception as e:
            logger.warning(f"L4 盈利能力分析失败: {e}")
            return ProfitabilityResult(rating="数据不足")

    # ========================================================================
    # L5: 成长与质量
    # ========================================================================

    def _analyze_l5_growth_quality(self) -> GrowthQualityResult:
        """成长与质量：现金流画像 + 盈利质量"""
        try:
            from .deep_analysis import DeepAnalyzer
            da = DeepAnalyzer(self.data, self.stock_code, self.adapter, self.cache)
            periods = da._build_periods_data(5)

            if not periods:
                return GrowthQualityResult(rating="数据不足")

            latest = periods[0]

            # 成长率 — 用 periods 的首尾估算 CAGR
            rev_growth = self._estimate_cagr(periods, "revenue")
            profit_growth = self._estimate_cagr(periods, "net_profit")
            asset_growth = self._estimate_cagr(periods, "total_assets")

            # 盈利质量
            cf_to_profit = self._safe_float(latest.get("ocf_to_profit")) or 0
            rev_cash_ratio = self._safe_float(latest.get("revenue_cash_ratio")) or 0

            # 现金流画像
            ocf = self._safe_float(latest.get("ocf")) or 0
            icf = self._safe_float(latest.get("icf")) or 0
            fcf = self._safe_float(latest.get("fcf")) or 0
            portrait = self._cashflow_portrait(ocf, icf, fcf)

            # FCF趋势
            fcf_trend = [
                self._safe_float(p.get("fcf")) or 0
                for p in periods
            ]

            # 评分
            score = UnifiedScorer().composite([
                ScoreCard(dimension="营收增长", category="成长",
                          raw_value=rev_growth, trend_score=0, peer_score=50,
                          absolute_score=min(max(rev_growth / 30 * 100, 0), 100)),
                ScoreCard(dimension="现金流/利润", category="质量",
                          raw_value=cf_to_profit, trend_score=0, peer_score=50,
                          absolute_score=min(max(cf_to_profit * 100, 0), 100)),
            ])

            return GrowthQualityResult(
                revenue_growth=round(rev_growth * 100, 1),
                profit_growth=round(profit_growth * 100, 1),
                asset_growth=round(asset_growth * 100, 1),
                growth_score=min(max(rev_growth / 30 * 100, 0), 100),
                cf_to_profit=round(cf_to_profit, 2),
                revenue_cash_ratio=round(rev_cash_ratio, 2),
                cashflow_portrait=portrait,
                fcf=round(fcf / 1e8, 2) if fcf else 0,
                fcf_trend=fcf_trend,
                quality_score=min(max(cf_to_profit * 100, 0), 100),
                overall_score=score,
                rating=self._rating_label(score),
            )
        except Exception as e:
            logger.warning(f"L5 成长质量分析失败: {e}")
            return GrowthQualityResult(rating="数据不足")

    # ========================================================================
    # L6: 估值
    # ========================================================================

    def _analyze_l6_valuation(
        self,
        market: MarketResult,
        profit: ProfitabilityResult,
        growth: GrowthQualityResult,
    ) -> ValuationResult:
        """估值三角：DCF + 相对估值 + PE分位"""
        result = ValuationResult(
            current_pe=market.pe_ttm,
            current_pb=market.pb,
        )

        # DCF估值
        try:
            # 准备DCF所需数据
            dcf_data = {
                "close": market.current_price,
                "total_share": self._extract_share_count(),
                "net_profit": profit.roe * self._extract_equity() / 100 \
                    if profit.roe else None,
                "operate_profit": self._extract_from_data(["operate_profit", "营业利润"]),
                "total_equity": self._extract_from_data(["total_equity", "股东权益合计"]),
                "total_liab": self._extract_from_data(["total_liab", "负债合计"]),
                "money_cap": self._extract_from_data(["money_cap", "货币资金"]),
            }

            dcf_result = self.dcf.calculate(dcf_data)
            result.dcf_fair_price = dcf_result.fair_price
            result.dcf_wacc = dcf_result.wacc
            result.dcf_upside = dcf_result.upside_pct
            result.sensitivity = dcf_result.sensitivity_matrix
            result.scenarios = dcf_result.scenarios
        except Exception as e:
            logger.warning(f"DCF估值失败: {e}")

        # PE分位（简化）
        try:
            from .phase2_analysis import Phase2Analyzer
            pa = Phase2Analyzer(self.data, self.stock_code, self.adapter)
            pe_pct_text = pa.pe_percentile_analysis()
            # 提取分位数（从文本中解析）
            import re
            match = re.search(r'当前分位:\s*([\d.]+)%', pe_pct_text)
            if match:
                result.pe_percentile = float(match.group(1))
        except Exception:
            result.pe_percentile = 50.0

        # 估值评分
        dcf_upside = result.dcf_upside
        pe_pct = result.pe_percentile

        # 估值吸引力：DCF上涨空间和PE分位各占50%
        dcf_score = min(max(50 + dcf_upside * 1.5, 0), 100)
        pe_score = max(0, 100 - pe_pct)  # 分位越低，估值越有吸引力

        result.valuation_score = round(dcf_score * 0.6 + pe_score * 0.4, 1)
        result.valuation_rating = self._valuation_label(result.valuation_score)

        # 公允价值区间
        if result.dcf_fair_price > 0:
            result.fair_value_range = (
                round(result.dcf_fair_price * 0.8, 2),
                round(result.dcf_fair_price * 1.2, 2),
            )

        return result

    # ========================================================================
    # L7: 综合评分合成
    # ========================================================================

    def _synthesize(
        self,
        thesis: InvestmentThesis,
        market: MarketResult,
        audit: AuditStructuredResult,
        health: FinancialHealthResult,
        profit: ProfitabilityResult,
        growth: GrowthQualityResult,
        valuation: ValuationResult,
    ) -> InvestmentThesis:
        """综合各维度评分，生成最终投资建议"""

        # 1. 基础分（行业和规模调整）
        thesis.business_score = 50.0  # 默认，可通过行业对标优化

        # 2. 会计质量（审计评分反向：低风险=高分）
        thesis.accounting_quality_score = audit.total_score

        # 3-5. 核心财务维度
        thesis.financial_health_score = health.composite_score
        thesis.profitability_score = profit.score
        thesis.growth_quality_score = growth.overall_score

        # 6. 估值
        thesis.valuation_score = valuation.valuation_score

        # 7. 综合评分（加权）
        scores = {
            "business": thesis.business_score,
            "accounting_quality": thesis.accounting_quality_score,
            "financial_health": thesis.financial_health_score,
            "profitability": thesis.profitability_score,
            "growth_quality": thesis.growth_quality_score,
            "valuation": thesis.valuation_score,
        }

        overall = sum(
            scores[dim] * DIMENSION_WEIGHTS.get(dim, 0.15)
            for dim in scores
        )
        overall = round(overall, 1)
        thesis.overall_score = overall
        thesis.overall_rating = UnifiedScorer.investment_rating(overall)
        thesis.star_rating = UnifiedScorer.star_rating(overall)

        # 定价
        thesis.current_price = market.current_price
        thesis.fair_value_range = valuation.fair_value_range
        thesis.upside_potential = valuation.dcf_upside

        # 投资亮点
        thesis.strengths = self._collect_strengths(profit, growth, valuation)
        thesis.risks = self._collect_risks(audit, profit, growth)
        thesis.catalysts = self._collect_catalysts(growth, valuation)

        # 核心指标
        thesis.key_metrics = {
            "股价": market.current_price,
            "市值(亿)": market.market_cap_yi,
            "PE(TTM)": market.pe_ttm,
            "PB": market.pb,
            "ROE(%)": profit.roe,
            "净利率(%)": profit.net_margin,
            "营收CAGR(%)": growth.revenue_growth,
            "净利润CAGR(%)": growth.profit_growth,
            "现金流/利润": growth.cf_to_profit,
            "DCF公允价值": valuation.dcf_fair_price,
            "估测空间%": valuation.dcf_upside,
            "审计评分": audit.total_score,
        }

        # 雷达图数据（7维标准化到0-100）
        thesis.radar_data = {
            "商业模式": thesis.business_score,
            "会计质量": thesis.accounting_quality_score,
            "财务健康": thesis.financial_health_score,
            "盈利能力": thesis.profitability_score,
            "成长质量": thesis.growth_quality_score,
            "估值吸引": thesis.valuation_score,
        }

        return thesis

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _get_company_name(self) -> str:
        sb = self.data.get("stock_basic")
        if sb is not None and not sb.empty:
            return str(sb.iloc[0].get("name", sb.iloc[0].get("NAME", "")))
        basic = self.data.get("basic")
        if basic is not None and not basic.empty:
            return str(basic.iloc[0].get("name", ""))
        return self.stock_code

    def _get_industry(self) -> str:
        sb = self.data.get("stock_basic")
        if sb is not None and not sb.empty:
            return str(sb.iloc[0].get("industry", sb.iloc[0].get("所属行业", "")))
        return ""

    def _extract_from_data(self, keys: list[str]) -> Any:
        """从原始data字典中按优先级提取值"""
        for df_name in ["balance", "income", "cashflow", "basic", "daily"]:
            df = self.data.get(df_name)
            if df is not None and not df.empty:
                row = df.iloc[0]
                for key in keys:
                    if key in row.index:
                        return row[key]
        return None

    def _extract_share_count(self) -> float:
        val = self._extract_from_data(["total_share", "total_share_y"])
        return self._safe_float(val) or 0

    def _extract_equity(self) -> float:
        val = self._extract_from_data(["total_equity", "total_hldr_eqy_exc_min_int",
                                        "股东权益合计"])
        return self._safe_float(val) or 1

    def _estimate_roic(self, period: dict) -> float:
        """估算ROIC"""
        ebit = self._safe_float(period.get("operating_profit")) or 0
        tax_rate = 0.25
        equity = self._safe_float(period.get("total_equity")) or 1
        # 有息负债估计
        ib_debt = self._safe_float(period.get("total_liab")) or 0
        ib_debt = ib_debt * 0.5  # 假设50%为有息
        invested_capital = equity + ib_debt
        if invested_capital > 0:
            return round(ebit * (1 - tax_rate) / invested_capital * 100, 2)
        return 0

    def _estimate_cagr(self, periods: list[dict], key: str) -> float:
        """估算多年CAGR"""
        vals = [self._safe_float(p.get(key)) for p in periods if self._safe_float(p.get(key))]
        if len(vals) >= 2 and vals[-1] > 0:
            return (vals[0] / vals[-1]) ** (1 / (len(vals) - 1)) - 1
        return 0

    def _cashflow_portrait(self, ocf: float, icf: float, fcf: float) -> str:
        """现金流画像分类（参照教材第8章）"""
        if ocf > 0 and icf > 0:
            return "妖精型（经营+, 投资+）"
        elif ocf > 0 and icf < 0:
            return "奶牛型（经营+, 投资-）"  # 成熟稳健
        elif ocf < 0 and icf > 0:
            return "蛮牛型（经营-, 投资+）"  # 烧钱扩张
        else:
            return "危险型（经营-, 投资-）"  # 双重失血

    def _collect_strengths(self, profit, growth, valuation) -> list[str]:
        s = []
        if profit.roe > 15:
            s.append(f"ROE优秀 ({profit.roe:.1f}%)")
        if profit.net_margin > 10:
            s.append(f"净利率良好 ({profit.net_margin:.1f}%)")
        if growth.revenue_growth > 15:
            s.append(f"高成长性 (营收CAGR {growth.revenue_growth:.1f}%)")
        if growth.cf_to_profit > 1.0:
            s.append("利润现金含量高，盈利质量好")
        if valuation.dcf_upside > 20:
            s.append(f"DCF估值偏低 (上涨空间{valuation.dcf_upside:.0f}%)")
        if valuation.pe_percentile < 30:
            s.append(f"PE处于历史低位 (分位{valuation.pe_percentile:.0f}%)")
        return s

    def _collect_risks(self, audit, profit, growth) -> list[str]:
        r = []
        if audit.high_signals > 0:
            r.append(f"财务审计发现{audit.high_signals}个高风险信号")
        if audit.medium_signals > 3:
            r.append(f"财务审计发现{audit.medium_signals}个中风险信号")
        if profit.roe < 5:
            r.append(f"ROE偏低 ({profit.roe:.1f}%)")
        if growth.revenue_growth < 5:
            r.append("营收增长乏力")
        if growth.cf_to_profit < 0.5:
            r.append("利润现金含量偏低")
        return r

    def _collect_catalysts(self, growth, valuation) -> list[str]:
        c = []
        if growth.revenue_growth > 20:
            c.append("业绩高增长有望推动估值修复")
        if valuation.pe_percentile < 20:
            c.append("极低PE分位，估值修复空间大")
        if 10 < valuation.dcf_upside < 50:
            c.append("DCF估值显示有安全边际")
        return c

    def _valuation_label(self, score: float) -> str:
        if score >= 70:
            return "显著低估"
        elif score >= 55:
            return "偏低"
        elif score >= 45:
            return "合理"
        elif score >= 30:
            return "偏高"
        return "显著高估"

    @staticmethod
    def _rating_label(score: float) -> str:
        return UnifiedScorer.rating(score)

    @staticmethod
    def _safe_float(val: Any) -> float | None:
        if val is None:
            return None
        try:
            v = float(val)
            if np.isnan(v) or np.isinf(v):
                return None
            return v
        except (ValueError, TypeError):
            return None
