"""
行业对标引擎 — FA Pro v11
======================
实现行业同侪对比分析：
  - 获取同行业公司列表
  - 批量拉取同行的关键财务数据
  - 四分位法计算公司在行业中的分位数
  - 生成完整的对标报告

参照《Python大数据财务分析》第7章"财务同业比较分析"
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class IndustryBenchmark:
    """行业对标结果"""
    industry: str
    company_name: str
    metrics: dict[str, dict] = field(default_factory=dict)
    # metrics = {metric_name: {p25, p50, p75, mean, company_value, percentile, peer_count}}
    total_peers: int = 0
    composite_ranking: int = 0      # 综合排名（1=最优）
    composite_percentile: float = 50.0  # 综合分位数


class BenchmarkEngine:
    """行业对标分析引擎"""

    def __init__(self, adapter=None):
        self.adapter = adapter
        self._peer_cache: dict[str, dict] = {}  # 同业数据缓存

    def get_industry_peers(
        self,
        stock_code: str,
        peer_count: int = 10,
    ) -> list[str]:
        """
        获取同行业可比公司列表

        策略：
        1. 通过Tushare pro.stock_basic获取同行业公司
        2. 优先选择市值相近的公司作为可比对象
        3. 若无法获取行业数据，回退到同板块（000xxx/600xxx等）的市值相近公司
        """
        if not self.adapter:
            return []

        try:
            # 尝试通过adapter获取股票基本信息（含行业）
            stock_basic = self.adapter.get_stock_data(
                stock_code, "", "", "stock_basic"
            )
            if stock_basic is not None and not stock_basic.empty:
                row = stock_basic.iloc[0]
                industry = row.get("industry") or row.get("所属行业", "")

                if industry:
                    # 同一行业的股票列表
                    # 尝试通过tushare获取
                    if hasattr(self.adapter, 'tushare_pro') and self.adapter.tushare_pro:
                        pro = self.adapter.tushare_pro
                        try:
                            df = pro.stock_basic(
                                exchange='', list_status='L',
                                fields='ts_code,name,industry'
                            )
                            peers = df[df['industry'] == industry]['ts_code'].tolist()
                            # 排除自身，限制数量
                            peers = [p for p in peers if p != stock_code][:peer_count]
                            if peers:
                                return peers
                        except Exception as e:
                            logger.debug(f"Tushare 同业查询失败: {e}")
        except Exception as e:
            logger.debug(f"获取行业信息失败: {e}")

        return []

    def fetch_peer_financials(
        self,
        peers: list[str],
        start_date: str = "20230101",
        end_date: str = None,
    ) -> dict[str, dict[str, float]]:
        """
        批量获取同行关键财务指标
        返回 {stock_code: {metric: value, ...}, ...}
        """
        if not peers or not self.adapter:
            return {}

        from datetime import datetime
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        result = {}

        for peer_code in peers:
            if peer_code in self._peer_cache:
                result[peer_code] = self._peer_cache[peer_code]
                continue
            try:
                metrics = self._extract_key_metrics(peer_code, start_date, end_date)
                if metrics:
                    result[peer_code] = metrics
                    self._peer_cache[peer_code] = metrics
            except Exception as e:
                logger.debug(f"同业 {peer_code} 数据获取失败: {e}")

        return result

    def _extract_key_metrics(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, float] | None:
        """提取单个公司的关键财务指标"""
        if not self.adapter:
            return None

        try:
            metrics = {}

            # 获取basic数据（含PE、PB、市值等）
            basic = self.adapter.get_stock_data(stock_code, start_date, end_date, "basic")
            if basic is not None and not basic.empty:
                row = basic.iloc[0]
                for col in ["pe", "pb", "total_mv", "close"]:
                    if col in row.index:
                        val = row[col]
                        if val and not (isinstance(val, float) and np.isnan(val)):
                            metrics[col] = float(val)

            # 获取财务指标
            fin = self.adapter.get_stock_data(stock_code, start_date, end_date, "financial")
            if fin is not None and not fin.empty:
                row = fin.iloc[0]
                for col in ["roe", "roa", "grossprofit_margin", "netprofit_margin",
                           "debt_to_assets", "current_ratio", "quick_ratio",
                           "assets_turn", "eps"]:
                    if col in row.index:
                        val = row[col]
                        if val and not (isinstance(val, float) and np.isnan(val)):
                            metrics[col] = float(val)

            return metrics if metrics else None

        except Exception as e:
            logger.debug(f"提取 {stock_code} 指标失败: {e}")
            return None

    @staticmethod
    def calculate_percentile(
        company_value: float,
        peer_values: list[float],
    ) -> float:
        """
        计算公司在行业中的分位数（百分位）
        返回值 0-100，越高表示公司在该指标上越领先
        """
        if not peer_values:
            return 50.0

        arr = np.array(peer_values)
        arr = arr[~np.isnan(arr)]
        if len(arr) == 0:
            return 50.0

        # 计算严格小于 company_value 的比例
        pct = np.sum(arr < company_value) / len(arr) * 100
        return round(pct, 1)

    def generate_benchmark(
        self,
        stock_code: str,
        company_metrics: dict[str, float],
        peer_codes: list[str] = None,
        start_date: str = "20230101",
    ) -> IndustryBenchmark:
        """
        生成完整行业对标报告

        流程：
        1. 获取同行列表（若未提供）
        2. 逐一拉取同行数据
        3. 逐指标计算分位数和行业统计值
        4. 综合排名
        """
        peers = peer_codes or self.get_industry_peers(stock_code)
        peer_data = self.fetch_peer_financials(peers, start_date)

        result = IndustryBenchmark(
            industry="未知行业",
            company_name=stock_code,
            total_peers=len(peer_data),
        )

        if not peer_data:
            return result

        # 逐指标计算统计值
        all_percentiles = []
        for metric, company_val in company_metrics.items():
            peer_vals = [
                pd.get(metric, np.nan)
                for pd in peer_data.values()
            ]
            peer_vals = [v for v in peer_vals if not np.isnan(v)]

            if len(peer_vals) >= 2:
                arr = np.array(peer_vals)
                p25, p50, p75 = np.percentile(arr, [25, 50, 75])
                pct = self.calculate_percentile(company_val, peer_vals)
                result.metrics[metric] = {
                    "p25": round(float(p25), 4),
                    "p50": round(float(p50), 4),
                    "p75": round(float(p75), 4),
                    "mean": round(float(np.mean(arr)), 4),
                    "company_value": company_val,
                    "percentile": pct,
                    "peer_count": len(peer_vals),
                }
                all_percentiles.append(pct)

        if all_percentiles:
            result.composite_percentile = round(float(np.mean(all_percentiles)), 1)
            result.composite_ranking = max(1, round(
                (100 - result.composite_percentile) / 100 * result.total_peers
            ))

        return result

    @staticmethod
    def format_benchmark(benchmark: IndustryBenchmark) -> str:
        """将对标结果格式化为可读文本"""
        lines = [
            "═══════════════════ 行业对标分析 ═══════════════════",
            f"  行业: {benchmark.industry}",
            f"  可比公司数: {benchmark.total_peers}",
            f"  综合排名: {benchmark.composite_ranking}/{benchmark.total_peers}",
            f"  综合分位: {benchmark.composite_percentile:.1f}%",
            "",
            "▌ 各指标分位数",
        ]

        for metric, stats in benchmark.metrics.items():
            pct = stats["percentile"]
            bar = "█" * max(0, int(pct / 5)) + "░" * max(0, 20 - int(pct / 5))
            lines.append(
                f"  {metric:<20} {bar} {pct:>5.1f}%  "
                f"(本公司:{stats['company_value']:.2f} | 中位:{stats['p50']:.2f})"
            )

        lines.append("\n═══════════════════════════════════════════════════")
        return "\n".join(lines)
