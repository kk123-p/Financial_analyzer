"""
统一评分引擎 — FA Pro v11
========================
实现三种评分维度：
  - 趋势评分：逐年比较改善程度（参照《Python大数据财务分析》第6章）
  - 同业评分：四分位法行业对标（参照第7章）
  - 绝对评分：基于专业财务阈值的绝对评价

综合评分 = 趋势×0.3 + 同业×0.3 + 绝对×0.4
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class ScoreCard:
    """单个指标的完整评分卡"""
    dimension: str          # 维度名称，如 "ROE"
    category: str           # 类别，如 "盈利能力"
    raw_value: float        # 原始指标值
    trend_score: float      # 趋势评分 0-100
    peer_score: float       # 同业评分 0-100（无同行数据时=50）
    absolute_score: float   # 绝对评分 0-100
    weight: float = 1.0     # 权重
    diagnosis: str = ""     # 诊断结论
    history: list[float] = field(default_factory=list)  # 历史值序列

    @property
    def composite(self) -> float:
        """加权综合评分"""
        return (self.trend_score * 0.3 +
                self.peer_score * 0.3 +
                self.absolute_score * 0.4)


# ============================================================================
# 专业财务阈值 — 基于CFA/CPA教材和A股市场实证数据
# ============================================================================

# 盈利能力阈值（越高越好）
PROFITABILITY_THRESHOLDS = {
    "roe":          [(20, 90), (15, 75), (10, 55), (5, 35), (0, 20)],
    "roa":          [(10, 90), (7, 75), (4, 55), (2, 35), (0, 20)],
    "gross_margin": [(50, 90), (35, 75), (20, 55), (10, 35), (0, 20)],
    "net_margin":   [(20, 90), (12, 75), (6, 55), (3, 35), (0, 20)],
    "op_margin":    [(25, 90), (15, 75), (8, 55), (3, 35), (0, 20)],
}

# 偿债能力阈值（流动比率等 — 中间值最优）
SOLVENCY_THRESHOLDS = {
    "current_ratio":      [(2.5, 80), (2.0, 90), (1.5, 85), (1.0, 60), (0.5, 30)],
    "quick_ratio":        [(1.5, 80), (1.0, 90), (0.7, 75), (0.4, 50), (0.2, 25)],
    "debt_ratio":         [(30, 90), (45, 75), (60, 55), (75, 35), (90, 20)],  # 越低越好（已反向）
    "interest_coverage":  [(20, 90), (10, 75), (5, 55), (2, 35), (0, 20)],
}

# 营运能力阈值
EFFICIENCY_THRESHOLDS = {
    "asset_turnover":    [(1.5, 90), (1.0, 75), (0.6, 55), (0.3, 35), (0, 20)],
    "inventory_turnover":[(10, 90), (6, 75), (3, 55), (1.5, 35), (0, 20)],
    "receivable_turnover":[(15, 90), (8, 75), (4, 55), (2, 35), (0, 20)],
}

# 成长能力阈值
GROWTH_THRESHOLDS = {
    "revenue_growth":    [(30, 90), (20, 75), (10, 55), (5, 35), (0, 20)],
    "profit_growth":     [(30, 90), (20, 75), (10, 55), (5, 35), (0, 20)],
    "asset_growth":      [(20, 90), (12, 75), (6, 55), (2, 35), (0, 20)],
}

# 估值阈值（越低越好，已反向）
VALUATION_THRESHOLDS = {
    "pe":           [(10, 90), (15, 80), (20, 60), (30, 40), (50, 20)],  # 低PE=高分
    "pb":           [(1.0, 90), (1.5, 80), (2.5, 55), (4.0, 35), (7.0, 20)],
    "ev_ebitda":    [(6, 90), (10, 75), (14, 55), (18, 35), (25, 20)],
    "fcf_yield":    [(10, 90), (6, 75), (3, 55), (1, 35), (0, 20)],    # FCF收益率越高越好
}

ALL_THRESHOLDS = {
    **PROFITABILITY_THRESHOLDS,
    **SOLVENCY_THRESHOLDS,
    **EFFICIENCY_THRESHOLDS,
    **GROWTH_THRESHOLDS,
    **VALUATION_THRESHOLDS,
}


class UnifiedScorer:
    """统一评分引擎 — 趋势+同业+绝对 三维评分"""

    @staticmethod
    def score_trend(history: list[float]) -> tuple[float, str]:
        """
        趋势评分：逐年比较改善年份占比 × 100
        参照教材第6章"财务趋势分析"
        """
        if not history or len(history) < 2:
            return 50.0, "数据不足，无法计算趋势"

        # 去除None和NaN
        clean = [v for v in history if v is not None and not (isinstance(v, float) and np.isnan(v))]
        if len(clean) < 2:
            return 50.0, "有效数据不足"

        improvements = sum(
            1 for i in range(1, len(clean))
            if clean[i] > clean[i - 1]
        )
        score = (improvements / (len(clean) - 1)) * 100

        if score >= 80:
            diag = "持续改善"
        elif score >= 60:
            diag = "总体向好"
        elif score >= 40:
            diag = "波动持平"
        elif score >= 20:
            diag = "趋势走弱"
        else:
            diag = "持续恶化"

        return round(score, 1), diag

    @staticmethod
    def score_peer(value: float, peer_values: list[float]) -> tuple[float, str]:
        """
        同业评分：四分位法映射
        参照教材第7章"财务同业比较分析"
        """
        if not peer_values or len(peer_values) < 2:
            return 50.0, "无同行数据"

        arr = np.array(peer_values)
        p25, p50, p75 = np.percentile(arr, [25, 50, 75])

        if value >= p75:
            return 100.0, f"领先 (>P75={p75:.2f})"
        elif value >= p50:
            return 75.0, f"优秀 (P50-P75, 中位={p50:.2f})"
        elif value >= p25:
            return 50.0, f"中等 (P25-P50)"
        else:
            return 25.0, f"落后 (<P25={p25:.2f})"

    @staticmethod
    def score_absolute(value: float, metric_name: str, thresholds: dict = None) -> tuple[float, str]:
        """
        绝对评分：基于专业阈值的插值评分
        阈值格式：[(boundary, score), ...]  从高到低排列
        """
        if thresholds is None:
            thresholds = ALL_THRESHOLDS

        if metric_name not in thresholds:
            return 50.0, "无阈值定义"

        bounds = thresholds[metric_name]
        if not bounds:
            return 50.0, "无阈值定义"

        # 判断方向：如果第一个边界的分数最高 → 越高越好
        # 如果最后一个边界的分数最高 → 越低越好（如负债率）

        # 找到value所在区间并线性插值
        for i, (boundary, score) in enumerate(bounds):
            if value >= boundary:
                if i == 0:
                    # 在最高边界之上，给最高分（但不超过100）
                    return min(float(score) + 5, 100.0), f"优秀 ({metric_name}={value:.2f})"
                # 在边界i和i-1之间插值
                prev_boundary, prev_score = bounds[i - 1]
                if prev_boundary == boundary:
                    return float(score), f"{metric_name}={value:.2f}"
                ratio = (value - boundary) / (prev_boundary - boundary)
                interp_score = score + ratio * (prev_score - score)
                return round(max(0, min(100, interp_score)), 1), f"{metric_name}={value:.2f}"

        # 低于所有边界，给最低分
        lowest_boundary, lowest_score = bounds[-1]
        return max(float(lowest_score) - 5, 0.0), f"偏低 ({metric_name}={value:.2f})"

    @staticmethod
    def score_lower_is_better(value: float, metric_name: str) -> tuple[float, str]:
        """
        对于越低越好的指标（如PE、负债率），反转阈值表
        """
        # 使用预定义的反向阈值
        reversed_map = {
            "debt_ratio":       [(30, 90), (45, 75), (60, 55), (75, 35), (90, 20)],
            "pe":               [(10, 90), (15, 80), (20, 60), (30, 40), (50, 20)],
            "pb":               [(1.0, 90), (1.5, 80), (2.5, 55), (4.0, 35), (7.0, 20)],
            "ev_ebitda":        [(6, 90), (10, 75), (14, 55), (18, 35), (25, 20)],
        }
        if metric_name in reversed_map:
            return UnifiedScorer.score_absolute(value, metric_name, reversed_map)
        return 50.0, "无反向阈值定义"

    @staticmethod
    def composite(cards: list[ScoreCard], weights: dict[str, float] = None) -> float:
        """加权综合评分 0-100"""
        if not cards:
            return 50.0

        total_weight = 0.0
        weighted_sum = 0.0

        for card in cards:
            w = weights.get(card.dimension, card.weight) if weights else card.weight
            weighted_sum += card.composite * w
            total_weight += w

        return round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0

    @staticmethod
    def build_card(
        dimension: str,
        category: str,
        raw_value: float,
        history: list[float] = None,
        peer_values: list[float] = None,
        metric_name: str = None,
        weight: float = 1.0,
    ) -> ScoreCard:
        """一站式构建ScoreCard"""
        metric = metric_name or dimension.lower().replace(" ", "_")

        trend_score, trend_diag = UnifiedScorer.score_trend(
            (history or []) + [raw_value]
        )

        peer_score, peer_diag = UnifiedScorer.score_peer(
            raw_value, peer_values or []
        )

        try:
            abs_score, abs_diag = UnifiedScorer.score_absolute(raw_value, metric)
        except Exception:
            abs_score, abs_diag = 50.0, f"{metric}={raw_value:.2f}"

        diag = f"[趋势] {trend_diag} | [同业] {peer_diag} | [绝对] {abs_diag}"

        return ScoreCard(
            dimension=dimension,
            category=category,
            raw_value=raw_value,
            trend_score=trend_score,
            peer_score=peer_score,
            absolute_score=abs_score,
            weight=weight,
            diagnosis=diag,
            history=(history or []) + [raw_value],
        )

    @staticmethod
    def rating(score: float) -> str:
        """评分 → 中文评级"""
        if score >= 80:
            return "优秀"
        elif score >= 65:
            return "良好"
        elif score >= 50:
            return "一般"
        elif score >= 35:
            return "较差"
        else:
            return "风险"

    @staticmethod
    def investment_rating(score: float) -> str:
        """评分 → 投资评级"""
        if score >= 80:
            return "强烈推荐"
        elif score >= 65:
            return "推荐"
        elif score >= 50:
            return "中性"
        elif score >= 35:
            return "回避"
        else:
            return "强烈回避"

    @staticmethod
    def star_rating(score: float) -> str:
        """评分 → 星级"""
        stars = min(5, max(1, round(score / 20)))
        return "★" * stars + "☆" * (5 - stars)
