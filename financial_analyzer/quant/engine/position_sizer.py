"""仓位分配策略模块"""
from abc import ABC, abstractmethod
import numpy as np
from typing import Optional


class PositionSizer(ABC):
    """仓位分配策略基类"""
    name: str = "base"

    @abstractmethod
    def compute_weights(
        self,
        scores: dict[str, float],
        cov_matrix: Optional[np.ndarray] = None,
        stock_codes: Optional[list[str]] = None,
    ) -> dict[str, float]:
        """计算各资产权重

        Args:
            scores: {stock_code: composite_score}
            cov_matrix: 协方差矩阵（可选，部分策略需要）
            stock_codes: 股票代码列表（与 cov_matrix 行列对应）

        Returns:
            {stock_code: weight}  权重之和应为 1
        """
        ...


class EqualWeightSizer(PositionSizer):
    """均等分配"""
    name = "equal"

    def compute_weights(self, scores, cov_matrix=None, stock_codes=None):
        n = len(scores)
        if n == 0:
            return {}
        w = 1.0 / n
        return {code: w for code in scores}


class RiskParitySizer(PositionSizer):
    """风险平价：各资产对组合风险贡献相等"""
    name = "risk_parity"

    def compute_weights(self, scores, cov_matrix=None, stock_codes=None):
        if cov_matrix is None or stock_codes is None:
            return EqualWeightSizer().compute_weights(scores)

        n = len(stock_codes)
        if n == 0:
            return {}

        # 初始等权
        w = np.ones(n) / n

        # 迭代求解风险平价
        for _ in range(100):
            port_var = w @ cov_matrix @ w
            if port_var < 1e-10:
                break
            marginal_risk = cov_matrix @ w
            risk_contrib = w * marginal_risk
            target = port_var / n  # 目标：每资产风险贡献相等
            w_new = w * np.sqrt(target / (risk_contrib + 1e-10))
            w_new = w_new / w_new.sum()
            if np.max(np.abs(w_new - w)) < 1e-8:
                w = w_new
                break
            w = w_new

        return {stock_codes[i]: float(w[i]) for i in range(n)}


class MinVarianceSizer(PositionSizer):
    """最小方差组合"""
    name = "min_variance"

    def compute_weights(self, scores, cov_matrix=None, stock_codes=None):
        if cov_matrix is None or stock_codes is None:
            return EqualWeightSizer().compute_weights(scores)

        n = len(stock_codes)
        if n == 0:
            return {}

        try:
            inv_cov = np.linalg.inv(cov_matrix)
            ones = np.ones(n)
            w = inv_cov @ ones / (ones @ inv_cov @ ones)
            # 确保非负（截断负权重）
            w = np.maximum(w, 0)
            if w.sum() > 0:
                w = w / w.sum()
            else:
                w = np.ones(n) / n
        except np.linalg.LinAlgError:
            w = np.ones(n) / n

        return {stock_codes[i]: float(w[i]) for i in range(n)}


class KellySizer(PositionSizer):
    """Kelly 公式：基于胜率和赔率"""
    name = "kelly"

    def compute_weights(self, scores, cov_matrix=None, stock_codes=None):
        n = len(scores)
        if n == 0:
            return {}

        # 用分数作为胜率代理，归一化到 [0.1, 0.9]
        values = list(scores.values())
        min_v, max_v = min(values), max(values)
        if max_v - min_v < 1e-10:
            return {code: 1.0/n for code in scores}

        raw_weights = {}
        for code, score in scores.items():
            win_prob = 0.1 + 0.8 * (score - min_v) / (max_v - min_v)
            # Kelly: f* = p - q/b，简化为 f* = 2p - 1
            kelly_frac = max(0, 2 * win_prob - 1)
            raw_weights[code] = kelly_frac

        total = sum(raw_weights.values())
        if total < 1e-10:
            return {code: 1.0/n for code in scores}

        return {code: w/total for code, w in raw_weights.items()}


class MarketCapSizer(PositionSizer):
    """市值加权"""
    name = "market_cap"

    def compute_weights(self, scores, cov_matrix=None, stock_codes=None):
        # scores 在此策略中被解释为市值代理（对数市值）
        n = len(scores)
        if n == 0:
            return {}

        # 将分数转为市值（指数化）
        values = np.array(list(scores.values()))
        min_v = values.min()
        market_caps = np.exp(values - min_v)  # 防止下溢
        total = market_caps.sum()

        if total < 1e-10:
            return {code: 1.0/n for code in scores}

        codes = list(scores.keys())
        return {codes[i]: float(market_caps[i]/total) for i in range(n)}


SIZERS = {
    "equal": EqualWeightSizer,
    "risk_parity": RiskParitySizer,
    "min_variance": MinVarianceSizer,
    "kelly": KellySizer,
    "market_cap": MarketCapSizer,
}
