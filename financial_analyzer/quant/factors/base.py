"""因子基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class FactorInput:
    """因子计算的输入数据"""
    stock_code: str
    daily: Optional[pd.DataFrame] = None        # 日线行情
    income: Optional[pd.DataFrame] = None       # 利润表
    balance: Optional[pd.DataFrame] = None       # 资产负债表
    cashflow: Optional[pd.DataFrame] = None      # 现金流量表
    basic: Optional[pd.DataFrame] = None         # 股票基本信息
    moneyflow: Optional[pd.DataFrame] = None     # 资金流向
    margin: Optional[pd.DataFrame] = None        # 融资融券
    hk_hold: Optional[pd.DataFrame] = None       # 北向资金
    top10_holders: Optional[pd.DataFrame] = None # 十大股东
    dividend: Optional[pd.DataFrame] = None      # 分红数据


class BaseFactor(ABC):
    """所有因子的抽象基类"""

    name: str = ""
    category: str = ""
    label: str = ""
    direction: str = "positive"  # positive: 值越大越好, negative: 值越小越好

    def __init__(self, weight: float = 1.0):
        self.weight = weight

    @abstractmethod
    def compute(self, input_data: FactorInput) -> Optional[float]:
        """计算单个股票的因子值。返回 None 表示数据不满足计算条件"""
        ...

    @staticmethod
    def _validate_result(value: Optional[float]) -> Optional[float]:
        """将NaN转换为None"""
        if value is None:
            return None
        if value != value:  # NaN check
            return None
        return value

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            return  # 允许中间抽象类
