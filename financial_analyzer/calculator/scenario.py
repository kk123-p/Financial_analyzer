"""
情景分析 — FA Pro v11
===================
敏感性分析和蒙特卡洛模拟

参照哈佛分析框架第4维"前景分析"和CFA估值方法
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class ScenarioResult:
    """情景分析结果"""
    scenario_name: str
    probability: float                  # 发生概率
    description: str                    # 情景描述
    key_drivers: dict[str, float]       # 关键驱动因子值
    projected_revenue_growth: float     # 预测营收增长率
    projected_margin: float             # 预测利润率
    estimated_fair_price: float         # 估测公允价值
    estimated_return: float             # 预期回报率%


@dataclass
class SensitivityResult:
    """单因子敏感性分析"""
    parameter: str
    base_value: float
    range_pct: list[float]              # 参数变动范围（百分比）
    fair_prices: list[float]            # 对应的公允价值
    price_impacts: list[float]          # 价格影响%


class ScenarioAnalyzer:
    """情景分析器"""

    @staticmethod
    def build_scenarios(
        base_fair_price: float,
        current_price: float,
        growth_rate: float,
        net_margin: float,
    ) -> list[ScenarioResult]:
        """
        构建三情景分析框架

        参照CFA估值方法论中"Base/Upside/Downside"三情景框架
        以及A股分析师常用的情景设定
        """
        scenarios = []

        # 乐观情景（概率25%）
        opt_growth = growth_rate * 1.5
        opt_margin = min(net_margin * 1.15, 60.0)
        opt_price = base_fair_price * (1 + (opt_growth - growth_rate) * 2 +
                                        (opt_margin - net_margin) / net_margin * 0.5)
        scenarios.append(ScenarioResult(
            scenario_name="乐观",
            probability=0.25,
            description="行业景气上行，公司市场份额扩大，利润率改善",
            key_drivers={"营收增长率": opt_growth, "净利润率": opt_margin},
            projected_revenue_growth=round(opt_growth * 100, 1),
            projected_margin=round(opt_margin, 1),
            estimated_fair_price=round(opt_price, 2),
            estimated_return=round((opt_price - current_price) / current_price * 100, 1),
        ))

        # 基准情景（概率55%）
        scenarios.append(ScenarioResult(
            scenario_name="基准",
            probability=0.55,
            description="行业平稳运行，公司维持现有竞争力，利润稳定增长",
            key_drivers={"营收增长率": growth_rate, "净利润率": net_margin},
            projected_revenue_growth=round(growth_rate * 100, 1),
            projected_margin=round(net_margin, 1),
            estimated_fair_price=round(base_fair_price, 2),
            estimated_return=round((base_fair_price - current_price) / current_price * 100, 1),
        ))

        # 悲观情景（概率20%）
        pes_growth = max(growth_rate * 0.5, 0.01)
        pes_margin = net_margin * 0.85
        pes_price = base_fair_price * (1 - (growth_rate - pes_growth) * 2 -
                                        (net_margin - pes_margin) / net_margin * 0.5)
        scenarios.append(ScenarioResult(
            scenario_name="悲观",
            probability=0.20,
            description="行业景气下行，竞争加剧，利润率承压",
            key_drivers={"营收增长率": pes_growth, "净利润率": pes_margin},
            projected_revenue_growth=round(pes_growth * 100, 1),
            projected_margin=round(pes_margin, 1),
            estimated_fair_price=round(max(pes_price, current_price * 0.5), 2),
            estimated_return=round((max(pes_price, current_price * 0.5) - current_price) / current_price * 100, 1),
        ))

        return scenarios

    @staticmethod
    def expected_value(scenarios: list[ScenarioResult]) -> float:
        """概率加权预期价值"""
        total = sum(s.probability for s in scenarios)
        if total == 0:
            return 0
        return round(sum(
            s.estimated_fair_price * s.probability / total
            for s in scenarios
        ), 2)

    @staticmethod
    def sensitivity_single_factor(
        base_fair_price: float,
        parameter_name: str,
        base_value: float,
        impact_range: list[float] = None,
    ) -> SensitivityResult:
        """
        单因子敏感性分析
        参数变动范围默认 ±20%
        """
        if impact_range is None:
            impact_range = [-0.20, -0.10, -0.05, 0, 0.05, 0.10, 0.20]

        fair_prices = []
        price_impacts = []

        for delta in impact_range:
            # 简化模型：公允价值与关键参数近似线性关系
            adjusted = base_fair_price * (1 + delta * 1.5)
            fair_prices.append(round(adjusted, 2))
            price_impacts.append(round(delta * 100, 1))

        return SensitivityResult(
            parameter=parameter_name,
            base_value=base_value,
            range_pct=[round(r * 100, 1) for r in impact_range],
            fair_prices=fair_prices,
            price_impacts=price_impacts,
        )

    @staticmethod
    def monte_carlo_dcf(
        base_fcff: float,
        wacc: float,
        years: int = 5,
        simulations: int = 1000,
        vol_growth: float = 0.05,    # 增长率年化波动率
        vol_margin: float = 0.03,    # 利润率年化波动率
    ) -> dict:
        """
        蒙特卡洛模拟DCF估值

        对关键假设（增长率和WACC）引入随机性，
        运行N次模拟得到公允价值概率分布。
        """
        np.random.seed(42)  # 可复现

        fair_prices = []
        growth_samples = []
        wacc_samples = []

        for _ in range(simulations):
            # 增长率：对数正态分布
            g = np.random.lognormal(
                mean=np.log(max(0.01, base_fcff / 1e4)),
                sigma=vol_growth,
            )
            g = max(0.01, min(0.30, g))
            growth_samples.append(g)

            # WACC：正态分布
            w = np.random.normal(loc=wacc, scale=0.015)
            w = max(0.04, min(0.20, w))
            wacc_samples.append(w)

            # 简化DCF计算
            fcf_pv = 0
            for t in range(1, years + 1):
                fcf_t = base_fcff * (1 + g) ** t
                fcf_pv += fcf_t / (1 + w) ** t

            # 终值
            tv = fcf_pv / years * 15  # 简化终值估算
            tv_pv = tv / (1 + w) ** years

            price = (fcf_pv + tv_pv) / 1e4
            fair_prices.append(round(price, 2))

        arr = np.array(fair_prices)
        return {
            "simulations": simulations,
            "mean": round(float(np.mean(arr)), 2),
            "median": round(float(np.median(arr)), 2),
            "std": round(float(np.std(arr)), 2),
            "p10": round(float(np.percentile(arr, 10)), 2),
            "p25": round(float(np.percentile(arr, 25)), 2),
            "p75": round(float(np.percentile(arr, 75)), 2),
            "p90": round(float(np.percentile(arr, 90)), 2),
            "min": round(float(arr.min()), 2),
            "max": round(float(arr.max()), 2),
        }
