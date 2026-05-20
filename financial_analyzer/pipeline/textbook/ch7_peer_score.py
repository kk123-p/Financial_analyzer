"""
Ch7 财务同业比较分析 — 四分位数评分
===================================
整合《Python大数据财务分析》第7章 "第7章 财务同业比较分析（第5节-综合案例）.py" (lines 131-154)

原始教科书算法 (lines 131-154):
  对每个财务比率：
    - 获取全行业该比率的描述性统计（P25, P50, P75）
    - 四分位数映射：
      > P75    → 100分 (领先)
      P50 ~ P75 → 75分 (优秀)
      P25 ~ P50 → 50分 (中等)
      < P25    → 25分 (落后)
    - 无限值给100分
  总同业评分 = 所有比率评分的平均值

适配改造：
  - 输入从 Excel + Tushare直调 → 改为项目 adapter + 标准化数据
  - 输出从 Excel → 改为 dict
"""
import numpy as np


def score_peer_single(
    company_value: float,
    peer_values: list[float],
) -> tuple[float, str]:
    """
    单个比率的同业评分 — 完全复现教科书 Ch7 5.5 lines 131-148

    Args:
        company_value: 本公司的比率值
        peer_values: 全行业该比率的值列表

    Returns:
        (score_100_75_50_25, diagnosis)
    """
    if not peer_values or len(peer_values) < 2:
        return 50.0, "同行数据不足"

    # 处理无限值
    if isinstance(company_value, float) and np.isinf(company_value):
        return 100.0, "无限值→满分"

    arr = np.array([v for v in peer_values if not (isinstance(v, float) and np.isinf(v))])
    if len(arr) < 2:
        return 50.0, "有效同行数据不足"

    p25 = float(np.percentile(arr, 25))
    p50 = float(np.percentile(arr, 50))
    p75 = float(np.percentile(arr, 75))

    if company_value > p75:
        return 100.0, f"领先 (>{p75:.2f})"
    elif company_value > p50:
        return 75.0, f"优秀 ({p50:.2f}~{p75:.2f})"
    elif company_value > p25:
        return 50.0, f"中等 ({p25:.2f}~{p50:.2f})"
    else:
        return 25.0, f"落后 (<{p25:.2f})"


def compute_peer_percentiles(
    peer_values: list[float],
) -> dict[str, float]:
    """
    计算行业分位数统计
    """
    arr = np.array([v for v in peer_values if not (isinstance(v, float) and np.isinf(v))])
    if len(arr) < 2:
        return {}
    return {
        "p25": round(float(np.percentile(arr, 25)), 4),
        "p50": round(float(np.percentile(arr, 50)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "mean": round(float(np.mean(arr)), 4),
        "count": len(arr),
    }


def score_peer_all_ratios(
    company_ratios: dict[str, float],
    peer_ratios_map: dict[str, list[float]],
) -> dict[str, dict]:
    """
    对所有比率进行同业评分

    Args:
        company_ratios: {ratio_name: company_value}
        peer_ratios_map: {ratio_name: [peer_value1, peer_value2, ...]}

    Returns:
        {ratio_name: {"score": float, "diagnosis": str, "percentiles": dict}, ...}
    """
    results = {}
    for ratio_name, company_val in company_ratios.items():
        peer_vals = peer_ratios_map.get(ratio_name, [])
        score, diag = score_peer_single(company_val, peer_vals)
        percentiles = compute_peer_percentiles(peer_vals)
        results[ratio_name] = {
            "score": score,
            "diagnosis": diag,
            "percentiles": percentiles,
        }
    return results


def composite_peer_score(peer_results: dict[str, dict]) -> float:
    """
    综合同业评分 = 所有比率评分的平均值
    教科书 Ch7 5.5 line 154 的逻辑
    """
    if not peer_results:
        return 50.0
    scores = [r["score"] for r in peer_results.values()]
    return round(sum(scores) / len(scores), 1)
