"""
分析器基类 - 提取公共的数据获取逻辑
缓存统一由 DataSourceAdapter 管理，本类不再重复缓存逻辑
"""
import pandas as pd
from datetime import datetime, timedelta

from ..logging_config import get_logger

logger = get_logger(__name__)


class BaseAnalyzer:
    """分析器基类 - 统一数据获取、初始化"""

    # 默认回溯年数
    DEFAULT_YEARS = 5

    def __init__(self, data: dict, stock_code: str, data_adapter=None, cache_manager=None):
        self.data = data
        self.stock_code = stock_code
        self.data_adapter = data_adapter
        self.cache_manager = cache_manager

    def _fetch_data(self, data_type: str, years: int = None) -> tuple[pd.DataFrame | None, str | None]:
        """
        获取财务数据（带缓存），返回 (df, error_msg) 元组
        优先从 self.data 中取已加载的数据，没有再调用数据适配器。
        自动去重（同一 end_date 只保留第一条）。

        Args:
            data_type: 数据类型 (financial/income/balance/cashflow/daily/basic)
            years: 回溯年数，默认 5 年

        Returns:
            (DataFrame, None) 成功
            (None, error_string) 失败
        """
        if years is None:
            years = self.DEFAULT_YEARS

        df = None

        # 优先从已加载的数据中取
        if self.data and data_type in self.data:
            df = self.data[data_type]
            if df is not None and not df.empty:
                df = self._deduplicate(df)
                return df, None

        if not self.stock_code:
            return None, "未设置股票代码"

        if not self.data_adapter:
            return None, "未配置数据适配器"

        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y%m%d")
            df = self.data_adapter.get_stock_data(
                self.stock_code, start_date, end_date, data_type
            )

            if df is not None and not df.empty:
                df = self._deduplicate(df)
                return df, None
            else:
                return None, f"未获取到{data_type}数据"
        except Exception as e:
            logger.error(f"获取{data_type}数据失败: {e}")
            return None, f"获取{data_type}数据失败: {str(e)}"

    @staticmethod
    def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
        """去重：同一 end_date 只保留一条记录。
        tushare 会返回多个报告类型（合并/母公司），优先保留合并报表(report_type=1)。"""
        if df is None or df.empty or "end_date" not in df.columns:
            return df
        df = df.copy()
        # 优先保留合并报表 (report_type=1)，再保留第一条
        if "report_type" in df.columns:
            # 合并报表优先
            df["_sort_key"] = (df["report_type"] == 1).astype(int)
            df = df.sort_values("_sort_key", ascending=False).drop(columns=["_sort_key"])
        df = df.drop_duplicates(subset=["end_date"], keep="first").reset_index(drop=True)
        return df
