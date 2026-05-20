"""
Ch6 财务趋势分析 — 逐年改善度评分
=================================
整合《Python大数据财务分析》第6章 "第6章 财务趋势分析.py" (lines 135-163)

原始教科书算法 (lines 140-163):
  对每个财务比率，逐年比较当前值与上年值，
  若改善则计1分，标准化为100分制。
  总趋势评分 = 所有比率趋势评分的平均值。

  核心代码:
    n = 0
    for j in range(len(df) - 1):
        if df.iloc[j, k] > df.iloc[j+1, k] and not np.isinf(df.iloc[j, k]):
            n += 1
    score = n / (years - 1) * 100

适配改造：
  - 输入从 DataFrame (列=年份) → 改为 list[dict] (每期一个 dict)
  - 输出从 Excel → 改为 dict[str, float]
"""
import numpy as np


def score_trend_single(values: list[float]) -> tuple[float, str]:
    """
    单个比率的趋势评分
    完全复现教科书 Ch6 lines 140-150 的逻辑

    Args:
        values: 按时间顺序排列的比率值列表（最新在前）

    Returns:
        (score_0_100, diagnosis_string)
    """
    if not values or len(values) < 2:
        return 50.0, "数据不足"

    clean = []
    for v in values:
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            clean.append(v)

    if len(clean) < 2:
        return 50.0, "有效数据不足"

    n = 0
    comparisons = 0
    for j in range(len(clean) - 1):
        if clean[j] is not None and clean[j + 1] is not None:
            if not (isinstance(clean[j], float) and np.isinf(clean[j])):
                comparisons += 1
                if clean[j] > clean[j + 1]:
                    n += 1

    if comparisons == 0:
        return 50.0, "无可比较数据"

    score = round(n / comparisons * 100, 1)

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

    return score, diag


def score_trend_all_ratios(
    ratios_history: list[dict[str, float]],
) -> dict[str, float]:
    """
    对所有13项比率计算趋势评分
    完全复现教科书 Ch6 lines 152-163 的逻辑

    Args:
        ratios_history: 每期一个dict，包含全部比率值（最新在前）

    Returns:
        {ratio_name: trend_score_0_100, ...}
    """
    if not ratios_history:
        return {}

    # 收集所有比率名称
    all_ratio_names = set()
    for period in ratios_history:
        all_ratio_names.update(period.keys())

    trend_scores = {}
    for ratio_name in sorted(all_ratio_names):
        values = [period.get(ratio_name) for period in ratios_history]
        score, _ = score_trend_single(values)
        trend_scores[ratio_name] = score

    return trend_scores


def composite_trend_score(trend_scores: dict[str, float]) -> float:
    """
    综合趋势评分 = 所有比率趋势评分的平均值
    教科书 Ch6 line 163 的逻辑
    """
    if not trend_scores:
        return 50.0
    return round(sum(trend_scores.values()) / len(trend_scores), 1)
