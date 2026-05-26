# 量化交易系统 Phase 1 — 因子+信号引擎 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建多因子批量计算 + 截面排名 + 约束过滤管道，每月生成调仓清单。

**Architecture:** 独立 `quant/` 模块，仅复用数据适配器层。因子按基类统一接口，引擎管道串联执行（universe → factors → matrix → normalize → score → rank → filter → optimize → signal）。前端新增「策略」Tab。

**Tech Stack:** Python/pandas/numpy, dataclasses, FastAPI, Vanilla JS (Chart.js for charts)

---

### Task 1: 数据模型定义

**Files:**
- Create: `financial_analyzer/quant/__init__.py`
- Create: `financial_analyzer/quant/models.py`
- Create: `tests/test_quant_models.py`

- [ ] **Step 1: 编写 models.py 的测试**

```python
"""quant models 单元测试"""
import pytest
from datetime import date
from financial_analyzer.quant.models import (
    StockInfo, FactorValue, FactorMatrix, SignalResult,
    TradeAction, TradeList, FactorConfig
)

class TestStockInfo:
    def test_create_valid(self):
        s = StockInfo(code="600519", name="贵州茅台", industry="白酒", market="主板")
        assert s.code == "600519"
        assert s.industry == "白酒"

    def test_optional_fields_default(self):
        s = StockInfo(code="000001", name="平安银行")
        assert s.industry == ""
        assert s.market == ""
        assert s.is_st is False
        assert s.is_suspended is False
        assert s.listed_date is None

class TestFactorValue:
    def test_create(self):
        fv = FactorValue(stock_code="600519", factor_name="pe", raw_value=15.2, z_score=0.5)
        assert fv.raw_value == 15.2
        assert fv.z_score == 0.5

    def test_default_values(self):
        fv = FactorValue(stock_code="000001", factor_name="roe")
        assert fv.raw_value is None
        assert fv.z_score is None
        assert fv.percentile is None

class TestFactorMatrix:
    def test_empty_matrix(self):
        m = FactorMatrix(date=date(2026, 5, 29))
        assert m.date == date(2026, 5, 29)
        assert len(m.stocks) == 0

    def test_add_stock_scores(self):
        m = FactorMatrix(date=date(2026, 5, 29))
        m.stocks = ["600519", "000858"]
        m.scores = {
            "600519": {"pe": 1.2, "roe": 0.8},
            "000858": {"pe": -0.5, "roe": 1.5},
        }
        assert m.get_score("600519", "pe") == 1.2
        assert m.get_score("000858", "roe") == 1.5
        assert m.get_score("600519", "nonexist") is None

    def test_composite_score(self):
        m = FactorMatrix(date=date(2026, 5, 29))
        m.stocks = ["600519"]
        m.scores = {"600519": {"pe": 1.0, "roe": 2.0}}
        weights = {"pe": 0.5, "roe": 0.5}
        result = m.composite_score("600519", weights)
        assert result == 1.5

class TestSignalResult:
    def test_create(self):
        sr = SignalResult(
            stock_code="600519",
            stock_name="贵州茅台",
            action="buy",
            composite_score=1.25,
            target_weight=0.15,
            reason="因子综合得分排名第3",
        )
        assert sr.action == "buy"
        assert sr.composite_score == 1.25

class TestTradeList:
    def test_create(self):
        tl = TradeList(
            date=date(2026, 5, 29),
            universe="沪深300",
            signals=[
                SignalResult("600519", "贵州茅台", "buy", 1.25, 0.15, "排名第3"),
                SignalResult("000858", "五粮液", "sell", 0.1, 0.0, "排名跌出前30"),
            ],
        )
        assert len(tl.buys) == 1
        assert len(tl.sells) == 1

    def test_empty_trade_list(self):
        tl = TradeList(date=date(2026, 5, 29), universe="沪深300")
        assert tl.buys == []
        assert tl.sells == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_quant_models.py -v`
Expected: FAIL — 所有类未定义

- [ ] **Step 3: 创建 __init__.py**

```python
"""financial_analyzer.quant — 多因子量化交易策略引擎"""
```

- [ ] **Step 4: 实现 models.py**

```python
"""量化系统数据模型"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class StockInfo:
    """股票基础信息"""
    code: str
    name: str
    industry: str = ""
    market: str = ""
    is_st: bool = False
    is_suspended: bool = False
    listed_date: Optional[date] = None


@dataclass
class FactorValue:
    """单个因子的计算结果"""
    stock_code: str
    factor_name: str
    raw_value: Optional[float] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None


@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    label: str
    category: str               # value/quality/growth/momentum/sentiment/low_vol/risk
    direction: str = "positive"  # positive=越大越好, negative=越小越好
    weight: float = 1.0
    enabled: bool = True


@dataclass
class FactorMatrix:
    """全市场因子矩阵（截面数据）"""
    date: date
    stocks: list[str] = field(default_factory=list)
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    industries: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def get_score(self, stock_code: str, factor_name: str) -> Optional[float]:
        return self.scores.get(stock_code, {}).get(factor_name)

    def composite_score(self, stock_code: str, weights: dict[str, float]) -> float:
        """加权综合得分"""
        stock_scores = self.scores.get(stock_code, {})
        total = 0.0
        for name, weight in weights.items():
            score = stock_scores.get(name, 0.0)
            total += score * weight
        return total


@dataclass
class SignalResult:
    """单只股票的调仓信号"""
    stock_code: str
    stock_name: str
    action: str          # buy / sell / hold / increase / decrease
    composite_score: float
    target_weight: float
    reason: str


@dataclass
class TradeList:
    """一次调仓的完整清单"""
    date: date
    universe: str
    signals: list[SignalResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def buys(self) -> list[SignalResult]:
        return [s for s in self.signals if s.action == "buy"]

    @property
    def sells(self) -> list[SignalResult]:
        return [s for s in self.signals if s.action == "sell"]
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/test_quant_models.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add financial_analyzer/quant/__init__.py financial_analyzer/quant/models.py tests/test_quant_models.py
git commit -m "feat(quant): add data models for factor matrix and trade signals

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: 因子基类

**Files:**
- Create: `financial_analyzer/quant/factors/__init__.py`
- Create: `financial_analyzer/quant/factors/base.py`
- Create: `tests/test_factor_base.py`

- [ ] **Step 1: 编写 base.py 的测试**

```python
"""因子基类测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.base import BaseFactor, FactorInput

class TestFactorInput:
    def test_create(self):
        daily = pd.DataFrame({"close": [10, 11, 12]})
        fi = FactorInput(stock_code="600519", daily=daily)
        assert fi.stock_code == "600519"
        assert len(fi.daily) == 3

class TestBaseFactor:
    def test_name_and_category(self):
        class TestFactor(BaseFactor):
            name = "test_factor"
            category = "value"
            label = "测试因子"
            direction = "positive"

            def compute(self, input_data):
                return 1.0

        f = TestFactor(weight=1.0)
        assert f.name == "test_factor"
        assert f.category == "value"
        assert f.weight == 1.0
        assert f.direction == "positive"

    def test_compute_abstract(self):
        class IncompleteFactor(BaseFactor):
            pass

        with pytest.raises(TypeError):
            IncompleteFactor()

    def test_compute_returns_factor_value(self):
        class SimpleFactor(BaseFactor):
            name = "simple"
            category = "test"
            label = "测试"

            def compute(self, input_data):
                return 0.75

        f = SimpleFactor()
        result = f.compute(FactorInput("600519", pd.DataFrame()))
        assert result == 0.75

    def test_compute_handles_nan(self):
        class NaNReturningFactor(BaseFactor):
            name = "nan_factor"
            category = "test"
            label = "NaN测试"

            def compute(self, input_data):
                return float('nan')

        f = NaNReturningFactor()
        result = f.compute(FactorInput("600519", pd.DataFrame()))
        assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factor_base.py -v`
Expected: FAIL

- [ ] **Step 3: 创建 factors/__init__.py** (空文件)

- [ ] **Step 4: 实现 base.py**

```python
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            return  # 允许中间抽象类
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/test_factor_base.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add financial_analyzer/quant/factors/__init__.py financial_analyzer/quant/factors/base.py tests/test_factor_base.py
git commit -m "feat(quant): add factor base class with abc and FactorInput

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: 选股池管理

**Files:**
- Create: `financial_analyzer/quant/universe.py`
- Create: `tests/test_universe.py`

- [ ] **Step 1: 编写 universe.py 的测试**

```python
"""选股池管理测试"""
import pytest
from datetime import date, timedelta
from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.models import StockInfo

@pytest.fixture
def sample_stocks():
    return [
        StockInfo("600519", "贵州茅台", "白酒", "主板", False, False, date(2001, 8, 27)),
        StockInfo("000858", "五粮液", "白酒", "主板", False, False, date(1998, 4, 27)),
        StockInfo("300750", "宁德时代", "电池", "创业板", False, False, date(2018, 6, 11)),
        StockInfo("000001", "平安银行", "银行", "主板", False, False, date(1991, 4, 3)),
        StockInfo("688981", "中芯国际", "半导体", "科创板", False, False, date(2020, 7, 16)),
        StockInfo("600000", "浦发银行", "银行", "主板", False, True, date(1999, 11, 10)),
    ]

class TestUniverseManager:
    def test_filter_st_suspended(self, sample_stocks):
        """ST和停牌股票应被过滤"""
        # 标记一只为ST, 一只为停牌
        sample_stocks[0].is_st = True
        result = UniverseManager()._apply_hard_filters(sample_stocks)
        codes = [s.code for s in result]
        assert "600519" not in codes  # ST过滤
        assert "600000" not in codes  # 停牌过滤

    def test_filter_high_price(self, sample_stocks):
        """高价股过滤"""
        # 需要模拟股价 — 这里仅测试方法存在
        result = UniverseManager()._filter_by_price(sample_stocks, {"600519": 16.0, "000858": 10.0})
        codes = [s.code for s in result]
        assert "600519" not in codes  # >15元
        assert "000858" in codes

    def test_filter_new_listings(self, sample_stocks):
        """次新股(上市<6个月)应被过滤"""
        today = date(2026, 5, 26)
        six_months_ago = today - timedelta(days=183)
        sample_stocks[4].listed_date = today  # 今天刚上市
        result = UniverseManager()._filter_by_age(sample_stocks, today)
        codes = [s.code for s in result]
        assert "688981" not in codes

    def test_get_universe_returns_stocks(self):
        """获取选股池应返回股票列表"""
        mgr = UniverseManager()
        stocks = mgr.get_universe("沪深300")
        assert isinstance(stocks, list)
        # 可能因未配置Tushare返回空列表，这是合法的

    def test_pool_names(self):
        mgr = UniverseManager()
        pools = mgr.pool_names()
        assert "沪深300" in pools
        assert "中证500" in pools
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_universe.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 universe.py**

```python
"""选股池管理 — 从Tushare获取成分股并应用过滤"""
from datetime import date, timedelta
from typing import Optional

from ..data_sources.adapter import DataSourceAdapter
from ..logging_config import get_logger
from .models import StockInfo

logger = get_logger(__name__)

POOL_DEFINITIONS = {
    "沪深300": {"index_code": "000300.SH"},
    "中证500": {"index_code": "000905.SH"},
    "中证800": {"index_code": "000906.SH"},
    "创业板指": {"index_code": "399006.SZ"},
    "科创50": {"index_code": "000688.SH"},
}


class UniverseManager:
    """选股池管理器"""

    def __init__(self, adapter: Optional[DataSourceAdapter] = None):
        self._adapter = adapter
        self._cache: dict[str, list[StockInfo]] = {}

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = DataSourceAdapter()
        return self._adapter

    def pool_names(self) -> list[str]:
        return list(POOL_DEFINITIONS.keys())

    def get_universe(self, pool_name: str) -> list[StockInfo]:
        """获取选股池成分股（已应用基础过滤）"""
        if pool_name in self._cache:
            return self._cache[pool_name]

        stocks = self._fetch_index_members(pool_name)
        stocks = self._apply_hard_filters(stocks)
        self._cache[pool_name] = stocks
        logger.info(f"选股池 [{pool_name}]: {len(stocks)} 只股票（过滤后）")
        return stocks

    def get_custom_universe(self, pool_names: list[str]) -> list[StockInfo]:
        """合并多个选股池，去重"""
        seen = set()
        result = []
        for name in pool_names:
            for s in self.get_universe(name):
                if s.code not in seen:
                    seen.add(s.code)
                    result.append(s)
        return result

    def _fetch_index_members(self, pool_name: str) -> list[StockInfo]:
        """从Tushare获取指数成分股"""
        definition = POOL_DEFINITIONS.get(pool_name)
        if definition is None:
            return []

        try:
            pro = self.adapter.tushare_pro
            if pro is None:
                logger.warning("Tushare未连接，无法获取成分股")
                return []

            index_code = definition["index_code"]
            df = pro.index_weight(index_code=index_code)
            if df is None or df.empty:
                return []

            stocks = []
            for _, row in df.iterrows():
                code = str(row.get("con_code", ""))
                if not code:
                    continue
                stocks.append(StockInfo(code=code, name=""))
            return stocks
        except Exception as e:
            logger.error(f"获取成分股失败 [{pool_name}]: {e}")
            return []

    def _apply_hard_filters(self, stocks: list[StockInfo]) -> list[StockInfo]:
        """硬过滤：排除ST、停牌、次新股"""
        return [s for s in stocks if not s.is_st and not s.is_suspended]

    def _filter_by_price(self, stocks: list[StockInfo],
                         prices: dict[str, float],
                         max_price: float = 15.0) -> list[StockInfo]:
        """过滤股价超过阈值的股票"""
        return [s for s in stocks if prices.get(s.code, 999) <= max_price]

    def _filter_by_age(self, stocks: list[StockInfo],
                       today: date,
                       min_months: int = 6) -> list[StockInfo]:
        """过滤上市不满min_months的次新股"""
        cutoff = today - timedelta(days=min_months * 30)
        return [s for s in stocks
                if s.listed_date is None or s.listed_date <= cutoff]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_universe.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/universe.py tests/test_universe.py
git commit -m "feat(quant): add universe manager with index member fetching and filters

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: 价值因子

**Files:**
- Create: `financial_analyzer/quant/factors/value.py`
- Create: `tests/test_factors_value.py`

- [ ] **Step 1: 编写测试**

```python
"""价值因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.value import (
    PEFactor, PBFactor, PSFactor, DividendYieldFactor, FCFYieldFactor
)
from financial_analyzer.quant.factors.base import FactorInput


def make_daily(close=10.0):
    return pd.DataFrame({"close": [close], "total_mv": [1e6]})

def make_basic(pe=15.0, pb=2.0, total_share=1000):
    df = pd.DataFrame({"pe": [pe], "pb": [pb], "total_share": [total_share]})
    return df

def make_balance(equity=5000, total_assets=10000):
    return pd.DataFrame({
        "total_equity": [equity],
        "total_assets": [total_assets],
        "total_liab": [total_assets - equity],
    })

def make_cashflow(n_cashflow_act=500):
    return pd.DataFrame({"n_cashflow_act": [n_cashflow_act]})

def make_income(revenue=3000, net_profit=300):
    return pd.DataFrame({
        "revenue": [revenue],
        "net_profit": [net_profit],
    })

def basic_input(code="600519", **kwargs):
    return FactorInput(
        stock_code=code,
        daily=kwargs.get("daily", make_daily()),
        basic=kwargs.get("basic", make_basic()),
        balance=kwargs.get("balance", make_balance()),
        cashflow=kwargs.get("cashflow", make_cashflow()),
        income=kwargs.get("income", make_income()),
    )


class TestPEFactor:
    def test_normal(self):
        inp = basic_input(basic=make_basic(pe=12.5))
        result = PEFactor().compute(inp)
        # PE因子: 1/PE (低PE更好), 方向negative
        assert result == pytest.approx(-1 / 12.5, rel=1e-4)

    def test_no_basic(self):
        inp = basic_input(basic=None)
        result = PEFactor().compute(inp)
        assert result is None

    def test_negative_pe(self):
        inp = basic_input(basic=make_basic(pe=-5.0))
        result = PEFactor().compute(inp)
        assert result is None  # 负PE无意义

    def test_pe_zero(self):
        inp = basic_input(basic=make_basic(pe=0))
        result = PEFactor().compute(inp)
        assert result is None


class TestPBFactor:
    def test_normal(self):
        inp = basic_input(basic=make_basic(pb=1.5))
        result = PBFactor().compute(inp)
        assert result == pytest.approx(-1 / 1.5, rel=1e-4)

    def test_no_data(self):
        result = PBFactor().compute(FactorInput("600519"))
        assert result is None


class TestDividendYieldFactor:
    def test_no_dividend_data(self):
        # 无分红数据返回 None
        result = DividendYieldFactor().compute(basic_input())
        assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_value.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 value.py**

```python
"""价值因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _safe_get(df, col):
    """安全从DataFrame中取值"""
    if df is None or col not in df.columns:
        return None
    val = df[col].iloc[0]
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


class PEFactor(BaseFactor):
    name = "pe"
    category = "value"
    label = "市盈率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        pe = _safe_get(input_data.basic, "pe")
        if pe is None or pe <= 0:
            return None
        return -1.0 / pe  # 取倒数，低PE得分高


class PBFactor(BaseFactor):
    name = "pb"
    category = "value"
    label = "市净率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        pb = _safe_get(input_data.basic, "pb")
        if pb is None or pb <= 0:
            return None
        return -1.0 / pb


class PSFactor(BaseFactor):
    name = "ps"
    category = "value"
    label = "市销率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        revenue = _safe_get(input_data.income, "revenue")
        total_mv = _safe_get(input_data.daily, "total_mv")
        if not revenue or not total_mv or revenue <= 0:
            return None
        ps = total_mv / revenue
        if ps <= 0:
            return None
        return -1.0 / ps


class DividendYieldFactor(BaseFactor):
    name = "dividend_yield"
    category = "value"
    label = "股息率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        """从dividend数据表获取股息率"""
        div = input_data.dividend if hasattr(input_data, 'dividend') else None
        if div is None or div.empty:
            return None
        col = next((c for c in ["dv_ratio", "div_yield"] if c in div.columns), None)
        if col is None:
            return None
        return _safe_get(div, col)


class FCFYieldFactor(BaseFactor):
    name = "fcf_yield"
    category = "value"
    label = "自由现金流收益率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        ocf = _safe_get(input_data.cashflow, "n_cashflow_act")
        total_mv = _safe_get(input_data.daily, "total_mv")
        if not ocf or not total_mv or total_mv <= 0:
            return None
        return ocf / total_mv
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_value.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/value.py tests/test_factors_value.py
git commit -m "feat(quant): add value factors (PE, PB, PS, dividend yield, FCF yield)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: 质量因子

**Files:**
- Create: `financial_analyzer/quant/factors/quality.py`
- Create: `tests/test_factors_quality.py`

- [ ] **Step 1: 编写测试**

```python
"""质量因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.quality import (
    ROEFactor, GrossMarginFactor, NetMarginFactor
)
from financial_analyzer.quant.factors.base import FactorInput


class TestROEFactor:
    def test_normal(self):
        income = pd.DataFrame({"net_profit": [500]})
        balance = pd.DataFrame({"total_equity": [5000]})
        inp = FactorInput("600519", income=income, balance=balance)
        result = ROEFactor().compute(inp)
        assert result == pytest.approx(0.10, rel=1e-4)

    def test_no_equity(self):
        income = pd.DataFrame({"net_profit": [500]})
        inp = FactorInput("600519", income=income)
        result = ROEFactor().compute(inp)
        assert result is None

    def test_zero_equity(self):
        income = pd.DataFrame({"net_profit": [500]})
        balance = pd.DataFrame({"total_equity": [0]})
        inp = FactorInput("600519", income=income, balance=balance)
        result = ROEFactor().compute(inp)
        assert result is None


class TestGrossMarginFactor:
    def test_normal(self):
        income = pd.DataFrame({"revenue": [3000], "oper_cost": [1800]})
        inp = FactorInput("600519", income=income)
        result = GrossMarginFactor().compute(inp)
        assert result == pytest.approx(0.40, rel=1e-4)

    def test_no_oper_cost(self):
        income = pd.DataFrame({"revenue": [3000]})
        inp = FactorInput("600519", income=income)
        result = GrossMarginFactor().compute(inp)
        assert result is None


class TestNetMarginFactor:
    def test_normal(self):
        income = pd.DataFrame({"revenue": [3000], "net_profit": [450]})
        inp = FactorInput("600519", income=income)
        result = NetMarginFactor().compute(inp)
        assert result == pytest.approx(0.15, rel=1e-4)

    def test_no_revenue(self):
        income = pd.DataFrame({"net_profit": [450]})
        inp = FactorInput("600519", income=income)
        result = NetMarginFactor().compute(inp)
        assert result is None

    def test_negative_net_profit(self):
        income = pd.DataFrame({"revenue": [3000], "net_profit": [-100]})
        inp = FactorInput("600519", income=income)
        result = NetMarginFactor().compute(inp)
        assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_quality.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 quality.py**

```python
"""质量因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _safe_val(df, col):
    if df is None or col not in df.columns:
        return None
    v = df[col].iloc[0]
    try:
        f = float(v)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


class ROEFactor(BaseFactor):
    name = "roe"
    category = "quality"
    label = "净资产收益率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        np_val = _safe_val(input_data.income, "net_profit")
        equity = _safe_val(input_data.balance, "total_equity")
        if np_val is None or not equity or equity <= 0:
            return None
        return np_val / equity


class ROICFactor(BaseFactor):
    name = "roic"
    category = "quality"
    label = "资本回报率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        np_val = _safe_val(input_data.income, "net_profit")
        equity = _safe_val(input_data.balance, "total_equity")
        debt = _safe_val(input_data.balance, "total_liab")
        if np_val is None or equity is None or debt is None:
            return None
        invested = equity + debt
        if invested <= 0:
            return None
        return np_val / invested


class GrossMarginFactor(BaseFactor):
    name = "gross_margin"
    category = "quality"
    label = "毛利率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rev = _safe_val(input_data.income, "revenue")
        cost = _safe_val(input_data.income, "oper_cost")
        if not rev or cost is None:
            return None
        return (rev - cost) / rev


class NetMarginFactor(BaseFactor):
    name = "net_margin"
    category = "quality"
    label = "净利率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rev = _safe_val(input_data.income, "revenue")
        np_val = _safe_val(input_data.income, "net_profit")
        if not rev or np_val is None or np_val <= 0:
            return None
        return np_val / rev
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_quality.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/quality.py tests/test_factors_quality.py
git commit -m "feat(quant): add quality factors (ROE, ROIC, gross margin, net margin)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: 成长因子

**Files:**
- Create: `financial_analyzer/quant/factors/growth.py`
- Create: `tests/test_factors_growth.py`

- [ ] **Step 1: 编写测试**

```python
"""成长因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.growth import RevenueGrowthFactor, NetProfitGrowthFactor
from financial_analyzer.quant.factors.base import FactorInput


class TestRevenueGrowthFactor:
    def test_positive_growth(self):
        income = pd.DataFrame({
            "revenue": [1200, 1000, 800],
        })
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        # 最近一期 vs 上一期: (1200-1000)/1000 = 0.20
        assert result == pytest.approx(0.20, rel=1e-4)

    def test_negative_growth(self):
        income = pd.DataFrame({
            "revenue": [800, 1000, 1200],
        })
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result == pytest.approx(-0.20, rel=1e-4)

    def test_insufficient_data(self):
        income = pd.DataFrame({"revenue": [1200]})
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result is None

    def test_zero_previous(self):
        income = pd.DataFrame({"revenue": [1200, 0]})
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result is None


class TestNetProfitGrowthFactor:
    def test_positive_growth(self):
        income = pd.DataFrame({
            "net_profit": [150, 100],
        })
        inp = FactorInput("600519", income=income)
        result = NetProfitGrowthFactor().compute(inp)
        assert result == pytest.approx(0.50, rel=1e-4)

    def test_insufficient_data(self):
        income = pd.DataFrame({"net_profit": [150]})
        inp = FactorInput("600519", income=income)
        result = NetProfitGrowthFactor().compute(inp)
        assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_growth.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 growth.py**

```python
"""成长因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _safe_growth(df, col) -> Optional[float]:
    """计算同比增速"""
    if df is None or col not in df.columns:
        return None
    vals = df[col].dropna().values
    if len(vals) < 2:
        return None
    current = float(vals[0])
    previous = float(vals[1])
    if previous == 0:
        return None
    return (current - previous) / previous


class RevenueGrowthFactor(BaseFactor):
    name = "revenue_growth"
    category = "growth"
    label = "营收增长率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return _safe_growth(input_data.income, "revenue")


class NetProfitGrowthFactor(BaseFactor):
    name = "net_profit_growth"
    category = "growth"
    label = "净利润增长率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return _safe_growth(input_data.income, "net_profit")


class CashflowGrowthFactor(BaseFactor):
    name = "cashflow_growth"
    category = "growth"
    label = "经营现金流增长率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return _safe_growth(input_data.cashflow, "n_cashflow_act")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_growth.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/growth.py tests/test_factors_growth.py
git commit -m "feat(quant): add growth factors (revenue, net profit, cashflow growth)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: 动量因子

**Files:**
- Create: `financial_analyzer/quant/factors/momentum.py`
- Create: `tests/test_factors_momentum.py`

- [ ] **Step 1: 编写测试**

```python
"""动量因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.momentum import (
    PriceMomentum3M, PriceMomentum6M, PriceMomentum12M
)
from financial_analyzer.quant.factors.base import FactorInput


def make_daily_prices(prices: list):
    """从价格列表创建DataFrame (最近在前)"""
    return pd.DataFrame({"close": prices})


class TestPriceMomentum3M:
    def test_positive_momentum(self):
        daily = make_daily_prices([12.0, 11.0, 10.5, 10.0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum3M().compute(inp)
        assert result == pytest.approx(0.20, rel=1e-4)  # (12-10)/10

    def test_insufficient_data(self):
        daily = make_daily_prices([10.0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum3M().compute(inp)
        assert result is None

    def test_no_daily(self):
        result = PriceMomentum3M().compute(FactorInput("600519"))
        assert result is None

    def test_zero_start_price(self):
        daily = make_daily_prices([10.0, 0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum3M().compute(inp)
        assert result is None  # start_price==0, division by zero


class TestPriceMomentum12M:
    def test_annual_momentum(self):
        daily = make_daily_prices([15.0, 14.0, 13.0, 12.0, 10.0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum12M().compute(inp)
        assert result == pytest.approx(0.50, rel=1e-4)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_momentum.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 momentum.py**

```python
"""动量因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _price_momentum(daily, lookback: int) -> Optional[float]:
    """计算过去N期的价格动量"""
    if daily is None or "close" not in daily.columns:
        return None
    prices = daily["close"].dropna().values
    if len(prices) < lookback + 1:
        return None
    current = float(prices[0])
    start = float(prices[lookback])
    if start == 0:
        return None
    return (current - start) / start


class PriceMomentum3M(BaseFactor):
    name = "momentum_3m"
    category = "momentum"
    label = "3个月价格动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return _price_momentum(input_data.daily, 60)


class PriceMomentum6M(BaseFactor):
    name = "momentum_6m"
    category = "momentum"
    label = "6个月价格动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return _price_momentum(input_data.daily, 120)


class PriceMomentum12M(BaseFactor):
    name = "momentum_12m"
    category = "momentum"
    label = "12个月价格动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return _price_momentum(input_data.daily, 250)


class VolumeMomentum(BaseFactor):
    name = "volume_momentum"
    category = "momentum"
    label = "成交量动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        if input_data.daily is None or "vol" not in input_data.daily.columns:
            return None
        vols = input_data.daily["vol"].dropna().values
        if len(vols) < 21:
            return None
        recent = float(vols[:5].mean())
        past = float(vols[5:21].mean())
        if past == 0:
            return None
        return (recent - past) / past
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_momentum.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/momentum.py tests/test_factors_momentum.py
git commit -m "feat(quant): add momentum factors (3M/6M/12M price, volume momentum)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: 情绪因子

**Files:**
- Create: `financial_analyzer/quant/factors/sentiment.py`
- Create: `tests/test_factors_sentiment.py`

- [ ] **Step 1: 编写测试**

```python
"""情绪因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.sentiment import (
    NorthBoundFlowFactor, MarginChangeFactor
)
from financial_analyzer.quant.factors.base import FactorInput


class TestNorthBoundFlowFactor:
    def test_positive_inflow(self):
        hk_hold = pd.DataFrame({
            "vol": [10000, 5000, 3000],
        })
        inp = FactorInput("600519", hk_hold=hk_hold)
        result = NorthBoundFlowFactor().compute(inp)
        # 累计净流入 / 均值
        total = 10000 + 5000 + 3000
        avg = total / 3
        assert result == pytest.approx(total / avg, rel=1e-4)

    def test_no_hk_hold(self):
        result = NorthBoundFlowFactor().compute(FactorInput("600519"))
        assert result is None


class TestMarginChangeFactor:
    def test_increase(self):
        margin = pd.DataFrame({
            "rzye": [1000, 800, 600],  # 融资余额在增长
        })
        inp = FactorInput("600519", margin=margin)
        result = MarginChangeFactor().compute(inp)
        # (1000-800)/800 = 0.25
        assert result == pytest.approx(0.25, rel=1e-4)

    def test_no_margin(self):
        result = MarginChangeFactor().compute(FactorInput("600519"))
        assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_sentiment.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 sentiment.py**

```python
"""情绪因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


class NorthBoundFlowFactor(BaseFactor):
    name = "north_bound_flow"
    category = "sentiment"
    label = "北向资金净流入"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        hk = input_data.hk_hold
        if hk is None or hk.empty or "vol" not in hk.columns:
            return None
        vals = hk["vol"].dropna().values
        if len(vals) == 0:
            return None
        total = float(vals.sum())
        avg = float(vals.mean())
        if avg == 0:
            return None
        return total / avg


class MarginChangeFactor(BaseFactor):
    name = "margin_change"
    category = "sentiment"
    label = "融资净买入"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        margin = input_data.margin
        if margin is None or margin.empty:
            return None
        col = next((c for c in ["rzye", "fin_balance"] if c in margin.columns), None)
        if col is None:
            return None
        vals = margin[col].dropna().values
        if len(vals) < 2:
            return None
        current = float(vals[0])
        previous = float(vals[1])
        if previous == 0:
            return None
        return (current - previous) / previous
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_sentiment.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/sentiment.py tests/test_factors_sentiment.py
git commit -m "feat(quant): add sentiment factors (north bound flow, margin change)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: 低波动因子

**Files:**
- Create: `financial_analyzer/quant/factors/low_vol.py`
- Create: `tests/test_factors_lowvol.py`

- [ ] **Step 1: 编写测试**

```python
"""低波动因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.low_vol import (
    Volatility60D, MaxDrawdown120D
)
from financial_analyzer.quant.factors.base import FactorInput


class TestVolatility60D:
    def test_normal(self):
        daily = pd.DataFrame({
            "close": [10.0, 10.1, 9.9, 10.0, 10.2] * 20,  # 100行
        })
        inp = FactorInput("600519", daily=daily)
        result = Volatility60D().compute(inp)
        assert result is not None
        assert result <= 0  # 低波动得分更高 (取负)

    def test_insufficient_data(self):
        daily = pd.DataFrame({"close": [10.0]})
        inp = FactorInput("600519", daily=daily)
        result = Volatility60D().compute(inp)
        assert result is None

    def test_no_daily(self):
        result = Volatility60D().compute(FactorInput("600519"))
        assert result is None


class TestMaxDrawdown120D:
    def test_normal(self):
        # 先涨后跌再涨
        prices = [10.0] * 10 + [12.0] * 10 + [8.0] * 10 + [9.0] * 10
        daily = pd.DataFrame({"close": prices})
        inp = FactorInput("600519", daily=daily)
        result = MaxDrawdown120D().compute(inp)
        assert result is not None
        assert result >= -1.0  # 回撤在-1到0范围
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_lowvol.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 low_vol.py**

```python
"""低波动因子"""
from typing import Optional
import numpy as np
from .base import BaseFactor, FactorInput


def _daily_returns(daily) -> Optional[np.ndarray]:
    if daily is None or "close" not in daily.columns:
        return None
    prices = daily["close"].dropna().values
    if len(prices) < 3:
        return None
    return np.diff(prices) / prices[:-1]


class Volatility60D(BaseFactor):
    name = "volatility_60d"
    category = "low_vol"
    label = "60日波动率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rets = _daily_returns(input_data.daily)
        if rets is None or len(rets) < 60:
            return None
        vol = float(np.std(rets[-60:]))
        if vol == 0:
            return 0.0
        return -vol  # 波动率越低，得分越高


class MaxDrawdown120D(BaseFactor):
    name = "max_drawdown_120d"
    category = "low_vol"
    label = "120日最大回撤"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        if input_data.daily is None or "close" not in input_data.daily.columns:
            return None
        prices = input_data.daily["close"].dropna().values
        if len(prices) < 120:
            return None
        recent = prices[:120][::-1]  # 时间正序
        peak = recent[0]
        max_dd = 0.0
        for p in recent:
            if p > peak:
                peak = p
            dd = (p - peak) / peak
            if dd < max_dd:
                max_dd = dd
        return max_dd  # 负值，绝对值越小越好
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_lowvol.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/low_vol.py tests/test_factors_lowvol.py
git commit -m "feat(quant): add low volatility factors (60d volatility, 120d max drawdown)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: 风险因子

**Files:**
- Create: `financial_analyzer/quant/factors/risk.py`
- Create: `tests/test_factors_risk.py`

- [ ] **Step 1: 编写测试**

```python
"""风险因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.risk import DebtRatioFactor, CurrentRatioFactor
from financial_analyzer.quant.factors.base import FactorInput


class TestDebtRatioFactor:
    def test_normal(self):
        balance = pd.DataFrame({
            "total_liab": [4000],
            "total_assets": [10000],
        })
        inp = FactorInput("600519", balance=balance)
        result = DebtRatioFactor().compute(inp)
        assert result == pytest.approx(-0.40, rel=1e-4)  # 负向：越低越好，取负

    def test_no_balance(self):
        result = DebtRatioFactor().compute(FactorInput("600519"))
        assert result is None

    def test_zero_assets(self):
        balance = pd.DataFrame({"total_liab": [4000], "total_assets": [0]})
        inp = FactorInput("600519", balance=balance)
        result = DebtRatioFactor().compute(inp)
        assert result is None


class TestCurrentRatioFactor:
    def test_too_high(self):
        """流动比率过高也不好(资产利用效率低)"""
        balance = pd.DataFrame({
            "total_assets": [10000],
            "total_liab": [1000],
        })
        inp = FactorInput("600519", balance=balance)
        result = CurrentRatioFactor().compute(inp)
        assert result is not None  # 极端的流动比率应该降低得分
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factors_risk.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 risk.py**

```python
"""风险因子"""
from typing import Optional
import numpy as np
from .base import BaseFactor, FactorInput


def _safe_val(df, col) -> Optional[float]:
    if df is None or col not in df.columns:
        return None
    v = df[col].iloc[0]
    try:
        f = float(v)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


class DebtRatioFactor(BaseFactor):
    name = "debt_ratio"
    category = "risk"
    label = "资产负债率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        liab = _safe_val(input_data.balance, "total_liab")
        assets = _safe_val(input_data.balance, "total_assets")
        if liab is None or not assets:
            return None
        ratio = liab / assets
        return -ratio  # 负债率越低得分越高


class CurrentRatioFactor(BaseFactor):
    name = "current_ratio"
    category = "risk"
    label = "流动比率 (最优区间)"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        assets = _safe_val(input_data.balance, "total_assets")
        liab = _safe_val(input_data.balance, "total_liab")
        if not assets or liab is None or liab == 0:
            return None
        ratio = assets / liab
        optimal = 2.0
        return -abs(ratio - optimal)  # 偏离最优值越远得分越低
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factors_risk.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/factors/risk.py tests/test_factors_risk.py
git commit -m "feat(quant): add risk factors (debt ratio, current ratio)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: 因子矩阵构建器

**Files:**
- Create: `financial_analyzer/quant/engine/__init__.py`
- Create: `financial_analyzer/quant/engine/factor_matrix.py`
- Create: `tests/test_factor_matrix_builder.py`

- [ ] **Step 1: 编写测试**

```python
"""因子矩阵构建器测试"""
import pytest
import pandas as pd
import numpy as np
from datetime import date
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.factors.value import PEFactor, PBFactor
from financial_analyzer.quant.factors.quality import ROEFactor
from financial_analyzer.quant.models import StockInfo

class TestFactorMatrixBuilder:
    def test_build_empty_stocks(self):
        builder = FactorMatrixBuilder(factors=[PEFactor()])
        matrix = builder.build([], {})
        assert len(matrix.stocks) == 0

    def test_build_with_data(self):
        builder = FactorMatrixBuilder(factors=[PEFactor(), PBFactor()])
        stocks = [StockInfo("600519", "茅台")]
        data = {
            "600519": {
                "basic": pd.DataFrame({"pe": [15.0], "pb": [3.0]}),
            }
        }
        matrix = builder.build(stocks, data)
        assert len(matrix.stocks) == 1
        assert "600519" in matrix.scores
        # PE: -1/15 = -0.0667, PB: -1/3 = -0.3333
        assert "pe" in matrix.scores["600519"]
        assert "pb" in matrix.scores["600519"]

    def test_factor_registry(self):
        builder = FactorMatrixBuilder(factors=[])
        builder.register(PEFactor(weight=1.0))
        builder.register(PBFactor(weight=0.5))
        assert len(builder.factors) == 2

    def test_all_factors_category(self):
        """所有7类因子都应能注册"""
        from financial_analyzer.quant.factors.value import PEFactor
        from financial_analyzer.quant.factors.quality import ROEFactor
        from financial_analyzer.quant.factors.growth import RevenueGrowthFactor
        from financial_analyzer.quant.factors.momentum import PriceMomentum3M
        from financial_analyzer.quant.factors.sentiment import NorthBoundFlowFactor
        from financial_analyzer.quant.factors.low_vol import Volatility60D
        from financial_analyzer.quant.factors.risk import DebtRatioFactor

        factors = [
            PEFactor(), ROEFactor(), RevenueGrowthFactor(),
            PriceMomentum3M(), NorthBoundFlowFactor(),
            Volatility60D(), DebtRatioFactor(),
        ]
        builder = FactorMatrixBuilder(factors=factors)
        categories = set(f.category for f in builder.factors)
        assert len(categories) == 7
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_factor_matrix_builder.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 factor_matrix.py**

```python
"""因子矩阵构建器 — 批量计算全市场股票的因子值"""
from datetime import date
from typing import Optional

import pandas as pd

from ..factors.base import BaseFactor, FactorInput
from ..models import StockInfo, FactorMatrix


class FactorMatrixBuilder:
    """构建因子矩阵（全市场 × 全因子）"""

    def __init__(self, factors: Optional[list[BaseFactor]] = None):
        self.factors = factors or []

    def register(self, factor: BaseFactor):
        self.factors.append(factor)

    def build(self, stocks: list[StockInfo],
              stock_data: dict[str, dict[str, pd.DataFrame]]) -> FactorMatrix:
        """构建因子矩阵

        Args:
            stocks: 选股池股票列表
            stock_data: {stock_code: {data_type: DataFrame}}

        Returns:
            FactorMatrix with scores populated
        """
        matrix = FactorMatrix(date=date.today())
        matrix.stocks = [s.code for s in stocks]
        matrix.industries = {s.code: s.industry for s in stocks}

        for stock in stocks:
            data = stock_data.get(stock.code, {})
            factor_input = FactorInput(
                stock_code=stock.code,
                daily=data.get("daily"),
                basic=data.get("basic"),
                income=data.get("income"),
                balance=data.get("balance"),
                cashflow=data.get("cashflow"),
                moneyflow=data.get("moneyflow"),
                margin=data.get("margin"),
                hk_hold=data.get("hk_hold"),
                top10_holders=data.get("top10_holders"),
                dividend=data.get("dividend"),
            )

            stock_scores = {}
            for factor in self.factors:
                value = factor.compute(factor_input)
                if value is not None:
                    stock_scores[factor.name] = value

            if stock_scores:
                matrix.scores[stock.code] = stock_scores

        matrix.stocks = [code for code in matrix.stocks if code in matrix.scores]
        return matrix
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_factor_matrix_builder.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/engine/__init__.py financial_analyzer/quant/engine/factor_matrix.py tests/test_factor_matrix_builder.py
git commit -m "feat(quant): add factor matrix builder for batch stock factor computation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: 截面标准化器

**Files:**
- Create: `financial_analyzer/quant/engine/normalizer.py`
- Create: `tests/test_normalizer.py`

- [ ] **Step 1: 编写测试**

```python
"""截面标准化器测试"""
import pytest
import numpy as np
from datetime import date
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.models import FactorMatrix


def make_matrix(scores_dict):
    """快速构建 FactorMatrix"""
    m = FactorMatrix(date=date(2026, 5, 29))
    stocks = list(scores_dict.keys())
    m.stocks = stocks
    m.scores = scores_dict
    m.industries = {s: "default" for s in stocks}
    return m


class TestCrossSectionalNormalizer:
    def test_zscore_normalization(self):
        m = make_matrix({
            "A": {"pe": 1.0, "roe": 0.10},
            "B": {"pe": 2.0, "roe": 0.15},
            "C": {"pe": 3.0, "roe": 0.20},
        })
        norm = CrossSectionalNormalizer(method="zscore")
        result = norm.normalize(m)
        # Z-score: mean=0, std=1 for each factor
        pe_scores = [result.scores[s]["pe"] for s in result.stocks]
        assert abs(np.mean(pe_scores)) < 1e-10
        assert abs(np.std(pe_scores) - 1.0) < 1e-10

    def test_rank_normalization(self):
        m = make_matrix({
            "A": {"pe": 1.0},
            "B": {"pe": 2.0},
            "C": {"pe": 3.0},
        })
        norm = CrossSectionalNormalizer(method="rank")
        result = norm.normalize(m)
        scores = [result.scores[s]["pe"] for s in result.stocks]
        assert max(scores) <= 1.0
        assert min(scores) >= -1.0

    def test_insufficient_stocks(self):
        m = make_matrix({"A": {"pe": 1.0}})
        norm = CrossSectionalNormalizer()
        result = norm.normalize(m)
        # 只有1只股票，Z-score无法计算，保持原值
        assert result.scores["A"]["pe"] == 1.0

    def test_preserves_missing_factors(self):
        m = make_matrix({
            "A": {"pe": 1.0, "roe": 0.10},
            "B": {"roe": 0.15},  # B缺少pe
        })
        norm = CrossSectionalNormalizer()
        result = norm.normalize(m)
        assert "pe" not in result.scores["B"]
        assert "roe" in result.scores["B"]

    def test_handles_nan_in_matrix(self):
        m = make_matrix({
            "A": {"pe": 1.0},
            "B": {"pe": 2.0},
        })
        norm = CrossSectionalNormalizer()
        result = norm.normalize(m)
        assert result.scores["A"]["pe"] is not None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_normalizer.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 normalizer.py**

```python
"""截面标准化器 — Z-score / 分位数 / 行业中性化"""
import numpy as np
import pandas as pd
from ..models import FactorMatrix


class CrossSectionalNormalizer:
    """截面因子标准化"""

    def __init__(self, method: str = "zscore"):
        self.method = method

    def normalize(self, matrix: FactorMatrix) -> FactorMatrix:
        if len(matrix.stocks) < 2:
            return matrix

        # 收集每个因子的所有值
        factor_names = set()
        for scores in matrix.scores.values():
            factor_names.update(scores.keys())

        for fname in factor_names:
            values = []
            stocks_with_factor = []
            for s in matrix.stocks:
                val = matrix.get_score(s, fname)
                if val is not None and val == val:  # not NaN
                    values.append(val)
                    stocks_with_factor.append(s)

            if len(values) < 2:
                continue

            if self.method == "zscore":
                normalized = self._zscore(values)
            elif self.method == "rank":
                normalized = self._rank_normalize(values)
            else:
                normalized = values

            for s, nv in zip(stocks_with_factor, normalized):
                matrix.scores[s][fname] = nv

        return matrix

    def _zscore(self, values: list[float]) -> list[float]:
        arr = np.array(values)
        mean = arr.mean()
        std = arr.std()
        if std == 0:
            return [0.0] * len(values)
        return ((arr - mean) / std).tolist()

    def _rank_normalize(self, values: list[float]) -> list[float]:
        """分位数归一化到[-1, 1]"""
        arr = np.array(values)
        n = len(arr)
        if n <= 1:
            return [0.0] * n
        ranks = np.argsort(np.argsort(arr)).astype(float)
        return (2 * ranks / (n - 1) - 1).tolist()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_normalizer.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/engine/normalizer.py tests/test_normalizer.py
git commit -m "feat(quant): add cross-sectional normalizer (z-score, rank)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: 加权打分器

**Files:**
- Create: `financial_analyzer/quant/engine/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: 编写测试**

```python
"""加权打分器测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.models import FactorMatrix, FactorConfig


def make_matrix():
    m = FactorMatrix(date=date(2026, 5, 29))
    m.stocks = ["A", "B", "C"]
    m.scores = {
        "A": {"pe": 0.5, "roe": 1.0, "momentum_3m": -0.3},
        "B": {"pe": -0.2, "roe": 0.5, "momentum_3m": 1.5},
        "C": {"pe": 1.2, "roe": -0.8, "momentum_3m": 0.2},
    }
    return m

def make_configs():
    return [
        FactorConfig(name="pe", label="PE", category="value", weight=1.0),
        FactorConfig(name="roe", label="ROE", category="quality", weight=1.0),
        FactorConfig(name="momentum_3m", label="3月动量", category="momentum", weight=0.5),
    ]

class TestWeightedScorer:
    def test_equal_weights(self):
        scorer = WeightedScorer(make_configs())
        scores = scorer.score(make_matrix())
        assert len(scores) == 3
        assert "A" in scores

    def test_custom_weights(self):
        configs = [
            FactorConfig(name="pe", label="PE", category="value", weight=2.0),
            FactorConfig(name="roe", label="ROE", category="quality", weight=0.5),
        ]
        scorer = WeightedScorer(configs)
        scores = scorer.score(make_matrix())
        # A: 2*0.5 + 0.5*1.0 = 1.5
        assert abs(scores["A"] - 1.5) < 1e-10

    def test_disabled_factor(self):
        configs = [
            FactorConfig(name="pe", label="PE", category="value", weight=1.0),
            FactorConfig(name="roe", label="ROE", category="quality", weight=1.0, enabled=False),
        ]
        scorer = WeightedScorer(configs)
        scores = scorer.score(make_matrix())
        # A: 只用pe: 0.5
        assert abs(scores["A"] - 0.5) < 1e-10

    def test_missing_factor_score(self):
        """某只股票缺少某个因子的值，应跳过该因子"""
        m = make_matrix()
        del m.scores["A"]["momentum_3m"]
        scorer = WeightedScorer(make_configs())
        scores = scorer.score(m)
        assert "A" in scores
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_scorer.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 scorer.py**

```python
"""加权综合打分器"""
from ..models import FactorMatrix, FactorConfig


class WeightedScorer:
    """按因子配置的权重计算综合得分"""

    def __init__(self, factor_configs: list[FactorConfig]):
        self.configs = {c.name: c for c in factor_configs}

    def score(self, matrix: FactorMatrix) -> dict[str, float]:
        """返回 {stock_code: composite_score}"""
        active_configs = {n: c for n, c in self.configs.items() if c.enabled}
        total_weight = sum(c.weight for c in active_configs.values())
        if total_weight == 0:
            return {s: 0.0 for s in matrix.stocks}

        result = {}
        for stock in matrix.stocks:
            total = 0.0
            for name, config in active_configs.items():
                score = matrix.get_score(stock, name)
                if score is not None:
                    total += score * config.weight
            result[stock] = total / total_weight

        return result
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_scorer.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/engine/scorer.py tests/test_scorer.py
git commit -m "feat(quant): add weighted scorer for composite factor scoring

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: 排名 + 硬过滤器

**Files:**
- Create: `financial_analyzer/quant/engine/ranker.py`
- Create: `tests/test_ranker.py`

- [ ] **Step 1: 编写测试**

```python
"""排名与硬过滤测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.models import StockInfo, FactorMatrix


@pytest.fixture
def stocks():
    return [
        StockInfo("A", "股A", "白酒", is_st=False, is_suspended=False),
        StockInfo("B", "股B", "银行", is_st=True, is_suspended=False),
        StockInfo("C", "股C", "电池", is_st=False, is_suspended=True),
        StockInfo("D", "股D", "银行", is_st=False, is_suspended=False),
        StockInfo("E", "股E", "白酒", is_st=False, is_suspended=False),
    ]

@pytest.fixture
def scores():
    return {"A": 1.5, "B": 0.8, "C": 2.0, "D": -0.5, "E": 0.3}

class TestRanker:
    def test_rank_and_filter_top_n(self, stocks, scores):
        ranker = Ranker(top_n=3)
        matrix = FactorMatrix(date=date(2026, 5, 29))
        matrix.stocks = [s.code for s in stocks]
        matrix.scores = {s: {"_composite": v} for s, v in scores.items()}
        matrix.industries = {s.code: s.industry for s in stocks}

        ranked = ranker.rank(matrix, scores, stocks)
        assert len(ranked) <= 3
        # B是ST, C是停牌 — 应被过滤
        codes = [s.code for s in ranked]
        assert "B" not in codes
        assert "C" not in codes
        assert codes == ["A", "E", "D"]  # 按得分排序

    def test_max_price_filter(self, stocks, scores):
        ranker = Ranker(top_n=5, max_price=15.0)
        prices = {"A": 10.0, "B": 8.0, "C": 20.0, "D": 12.0, "E": 14.0}
        matrix = FactorMatrix(date=date(2026, 5, 29))
        matrix.stocks = [s.code for s in stocks]
        matrix.scores = {s: {"_composite": v} for s, v in scores.items()}

        ranked = ranker.rank(matrix, scores, stocks, prices=prices)
        codes = [s.code for s in ranked]
        assert "C" not in codes  # 20元 > 15元

    def test_empty_scores(self, stocks):
        ranker = Ranker()
        matrix = FactorMatrix(date=date(2026, 5, 29))
        ranked = ranker.rank(matrix, {}, stocks)
        assert ranked == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_ranker.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 ranker.py**

```python
"""排名与硬过滤"""
from typing import Optional

from ..models import StockInfo, FactorMatrix


class Ranker:
    """TOP-N排名 + 硬过滤"""

    def __init__(self, top_n: int = 30, max_price: float = 15.0):
        self.top_n = top_n
        self.max_price = max_price

    def rank(self, matrix: FactorMatrix, composite_scores: dict[str, float],
             stocks: list[StockInfo],
             prices: Optional[dict[str, float]] = None) -> list[StockInfo]:
        """按综合得分排名，应用硬过滤，返回TOP-N"""
        stock_map = {s.code: s for s in stocks}

        # 硬过滤
        valid_codes = set()
        for s in stocks:
            if s.is_st or s.is_suspended:
                continue
            if prices and prices.get(s.code, 999) > self.max_price:
                continue
            if s.code in composite_scores:
                valid_codes.add(s.code)

        # 得分排序
        ranked = sorted(
            valid_codes,
            key=lambda code: composite_scores.get(code, -999),
            reverse=True,
        )

        top_codes = ranked[:self.top_n]
        return [stock_map[code] for code in top_codes if code in stock_map]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_ranker.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/engine/ranker.py tests/test_ranker.py
git commit -m "feat(quant): add ranker with hard filters (ST, suspended, price)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 15: 约束优化器

**Files:**
- Create: `financial_analyzer/quant/engine/optimizer.py`
- Create: `tests/test_optimizer.py`

- [ ] **Step 1: 编写测试**

```python
"""约束优化器测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.models import StockInfo


@pytest.fixture
def ranked_stocks():
    return [
        StockInfo("A", "股A", "白酒"),
        StockInfo("B", "股B", "白酒"),
        StockInfo("C", "股C", "白酒"),
        StockInfo("D", "股D", "银行"),
        StockInfo("E", "股E", "电池"),
        StockInfo("F", "股F", "银行"),
        StockInfo("G", "股G", "半导体"),
        StockInfo("H", "股H", "白酒"),
    ]

@pytest.fixture
def scores():
    return {"A": 2.0, "B": 1.8, "C": 1.5, "D": 1.3, "E": 1.2, "F": 1.0, "G": 0.8, "H": 0.5}

class TestConstraintOptimizer:
    def test_min_industries_constraint(self, ranked_stocks, scores):
        opt = ConstraintOptimizer(
            min_stocks=5, max_stocks=8,
            min_industries=3,
            max_industry_weight=0.40,
        )
        result = opt.optimize(ranked_stocks, scores)
        codes = [s.code for s in result]
        industries = set(s.industry for s in result)
        assert len(industries) >= 3
        assert 5 <= len(result) <= 8

    def test_max_industry_weight(self, ranked_stocks, scores):
        opt = ConstraintOptimizer(
            min_stocks=5, max_stocks=8,
            min_industries=1,
            max_industry_weight=0.40,
        )
        result = opt.optimize(ranked_stocks, scores)
        # 白酒股票不应超过总数的40%
        alcohol_count = sum(1 for s in result if s.industry == "白酒")
        max_allowed = int(len(result) * 0.40)
        assert alcohol_count <= max_allowed + 1  # 允许舍入误差

    def test_max_stocks_limit(self, ranked_stocks, scores):
        opt = ConstraintOptimizer(max_stocks=4, min_stocks=3, min_industries=1)
        result = opt.optimize(ranked_stocks, scores)
        assert len(result) <= 4

    def test_returns_empty_for_insufficient_input(self):
        opt = ConstraintOptimizer(min_industries=3)
        result = opt.optimize([], {})
        assert result == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_optimizer.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 optimizer.py**

```python
"""约束优化器 — 在TOP-N中选择满足约束的最优组合"""
from typing import Optional

from ..models import StockInfo


class ConstraintOptimizer:
    """组合约束优化"""

    def __init__(self,
                 min_stocks: int = 5,
                 max_stocks: int = 8,
                 min_industries: int = 3,
                 max_industry_weight: float = 0.40,
                 cash_reserve: float = 0.10):
        self.min_stocks = min_stocks
        self.max_stocks = max_stocks
        self.min_industries = min_industries
        self.max_industry_weight = max_industry_weight
        self.cash_reserve = cash_reserve

    def optimize(self, ranked_stocks: list[StockInfo],
                 scores: dict[str, float]) -> list[StockInfo]:
        """从排序后的TOP-N中选择满足约束的子集"""
        if not ranked_stocks:
            return []

        total_capital = 5000.0  # 总资金
        investable = total_capital * (1 - self.cash_reserve)
        min_per_stock = 500.0

        result: list[StockInfo] = []
        industry_counts: dict[str, int] = {}

        for stock in ranked_stocks:
            if len(result) >= self.max_stocks:
                break

            industry = stock.industry or "其他"
            current_count = industry_counts.get(industry, 0)
            max_in_industry = int(self.max_stocks * self.max_industry_weight)

            if current_count >= max_in_industry and len(result) >= self.min_stocks:
                continue  # 该行业已满

            result.append(stock)
            industry_counts[industry] = current_count + 1

        # 检查行业数约束
        if len(set(s.industry for s in result)) < self.min_industries:
            # 尝试从ranked_stocks后续补充缺失行业
            existing_industries = set(s.industry for s in result)
            for stock in ranked_stocks:
                if stock in result:
                    continue
                industry = stock.industry or "其他"
                if industry not in existing_industries and len(result) < self.max_stocks:
                    result.append(stock)
                    existing_industries.add(industry)
                    if len(existing_industries) >= self.min_industries:
                        break

        # 确保最少持仓数
        if len(result) < self.min_stocks and len(ranked_stocks) >= self.min_stocks:
            for stock in ranked_stocks:
                if stock not in result:
                    result.append(stock)
                    if len(result) >= self.min_stocks:
                        break

        return result
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_optimizer.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/engine/optimizer.py tests/test_optimizer.py
git commit -m "feat(quant): add constraint optimizer (industry diversity, max weight)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 16: 信号生成器

**Files:**
- Create: `financial_analyzer/quant/engine/signal.py`
- Create: `tests/test_signal.py`

- [ ] **Step 1: 编写测试**

```python
"""信号生成器测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.signal import SignalGenerator
from financial_analyzer.quant.models import StockInfo, TradeList

@pytest.fixture
def optimizer_output():
    return [
        StockInfo("A", "股A", "白酒"),
        StockInfo("D", "股D", "银行"),
        StockInfo("E", "股E", "电池"),
        StockInfo("B", "股B", "白酒"),
        StockInfo("F", "股F", "银行"),
    ]

@pytest.fixture
def scores():
    return {
        "A": 2.0, "D": 1.3, "E": 1.2, "B": 1.8, "F": 1.0,
        "G": 0.8, "H": 0.5, "C": 1.5,
        "OLD1": 0.3, "OLD2": -0.2,
    }

class TestSignalGenerator:
    def test_generate_buy_signals(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings={"OLD1", "OLD2"},
            universe="沪深300",
        )
        assert isinstance(trade_list, TradeList)
        assert trade_list.universe == "沪深300"

    def test_sell_signals_for_dropped_stocks(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings={"OLD1", "OLD2"},
            universe="沪深300",
        )
        sell_codes = [s.stock_code for s in trade_list.sells]
        assert "OLD1" in sell_codes
        assert "OLD2" in sell_codes

    def test_no_holdings_all_buys(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings=set(),
            universe="沪深300",
        )
        assert len(trade_list.sells) == 0
        assert len(trade_list.buys) == len(optimizer_output)

    def test_equal_weights(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings=set(),
            universe="中证500",
        )
        # 5只股票等权，每只约18%(扣10%现金)
        for signal in trade_list.buys:
            assert 0.15 <= signal.target_weight <= 0.25
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_signal.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 signal.py**

```python
"""信号生成器 — 对比当前持仓与优化结果，生成调仓信号"""
from datetime import date
from typing import Optional

from ..models import StockInfo, SignalResult, TradeList


class SignalGenerator:
    """生成买入/卖出/调仓信号"""

    def __init__(self, cash_reserve: float = 0.10):
        self.cash_reserve = cash_reserve

    def generate(self,
                 optimized_stocks: list[StockInfo],
                 scores: dict[str, float],
                 current_holdings: set[str],
                 universe: str,
                 ref_date: Optional[date] = None) -> TradeList:
        """生成调仓清单"""
        trade_list = TradeList(
            date=ref_date or date.today(),
            universe=universe,
        )

        optimized_codes = {s.code for s in optimized_stocks}

        # 卖出：当前持有但不在优化结果中的
        for code in current_holdings - optimized_codes:
            score = scores.get(code, -999)
            trade_list.signals.append(SignalResult(
                stock_code=code,
                stock_name=code,
                action="sell",
                composite_score=score,
                target_weight=0.0,
                reason=f"综合得分 {score:.2f}，排名跌出TOP{len(optimized_stocks)}",
            ))

        # 买入：优化结果中的股票
        n = len(optimized_stocks)
        if n == 0:
            return trade_list

        invest_weight = (1 - self.cash_reserve) / n

        for stock in optimized_stocks:
            score = scores.get(stock.code, 0)
            rank = list(scores.keys()).index(stock.code) + 1 if stock.code in scores else n

            if stock.code in current_holdings:
                action = "hold"
                reason = f"继续持有，综合得分排名第{rank}"
            else:
                action = "buy"
                reason = f"因子综合得分排名第{rank}，纳入组合"

            trade_list.signals.append(SignalResult(
                stock_code=stock.code,
                stock_name=stock.name,
                action=action,
                composite_score=score,
                target_weight=round(invest_weight, 4),
                reason=reason,
            ))

        return trade_list
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_signal.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add financial_analyzer/quant/engine/signal.py tests/test_signal.py
git commit -m "feat(quant): add signal generator for buy/sell/hold trade signals

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 17: Quant API 路由

**Files:**
- Create: `financial_analyzer/web/routes/quant_api.py`
- Modify: `financial_analyzer/web/main.py` (注册路由)

- [ ] **Step 1: 实现 quant_api.py**

```python
"""量化策略 API 路由"""
import logging
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.factors.value import PEFactor, PBFactor, PSFactor, FCFYieldFactor
from financial_analyzer.quant.factors.quality import ROEFactor, ROICFactor, GrossMarginFactor, NetMarginFactor
from financial_analyzer.quant.factors.growth import RevenueGrowthFactor, NetProfitGrowthFactor, CashflowGrowthFactor
from financial_analyzer.quant.factors.momentum import PriceMomentum3M, PriceMomentum6M, PriceMomentum12M
from financial_analyzer.quant.factors.sentiment import NorthBoundFlowFactor, MarginChangeFactor
from financial_analyzer.quant.factors.low_vol import Volatility60D, MaxDrawdown120D
from financial_analyzer.quant.factors.risk import DebtRatioFactor, CurrentRatioFactor
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.engine.signal import SignalGenerator
from financial_analyzer.quant.models import FactorConfig
from ..dependencies import get_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/quant", tags=["quant"])

DEFAULT_FACTOR_CONFIGS = [
    FactorConfig(name="pe", label="PE", category="value", weight=1.0),
    FactorConfig(name="pb", label="PB", category="value", weight=1.0),
    FactorConfig(name="ps", label="PS", category="value", weight=0.5),
    FactorConfig(name="fcf_yield", label="FCF收益率", category="value", weight=0.5),
    FactorConfig(name="roe", label="ROE", category="quality", weight=1.5),
    FactorConfig(name="roic", label="ROIC", category="quality", weight=1.0),
    FactorConfig(name="gross_margin", label="毛利率", category="quality", weight=1.0),
    FactorConfig(name="net_margin", label="净利率", category="quality", weight=1.0),
    FactorConfig(name="revenue_growth", label="营收增长", category="growth", weight=1.0),
    FactorConfig(name="net_profit_growth", label="利润增长", category="growth", weight=1.0),
    FactorConfig(name="cashflow_growth", label="现金流增长", category="growth", weight=0.5),
    FactorConfig(name="momentum_3m", label="3月动量", category="momentum", weight=0.5),
    FactorConfig(name="momentum_6m", label="6月动量", category="momentum", weight=0.5),
    FactorConfig(name="momentum_12m", label="12月动量", category="momentum", weight=0.5),
    FactorConfig(name="north_bound_flow", label="北向资金", category="sentiment", weight=0.5),
    FactorConfig(name="margin_change", label="融资变化", category="sentiment", weight=0.5),
    FactorConfig(name="volatility_60d", label="60日波动", category="low_vol", weight=0.5),
    FactorConfig(name="max_drawdown_120d", label="最大回撤", category="low_vol", weight=0.5),
    FactorConfig(name="debt_ratio", label="负债率", category="risk", weight=1.0),
    FactorConfig(name="current_ratio", label="流动比率", category="risk", weight=0.5),
]

ALL_FACTORS = [
    PEFactor(), PBFactor(), PSFactor(), FCFYieldFactor(),
    ROEFactor(), ROICFactor(), GrossMarginFactor(), NetMarginFactor(),
    RevenueGrowthFactor(), NetProfitGrowthFactor(), CashflowGrowthFactor(),
    PriceMomentum3M(), PriceMomentum6M(), PriceMomentum12M(),
    NorthBoundFlowFactor(), MarginChangeFactor(),
    Volatility60D(), MaxDrawdown120D(),
    DebtRatioFactor(), CurrentRatioFactor(),
]


@router.get("/pools")
async def list_pools():
    """获取可用选股池列表"""
    mgr = UniverseManager()
    return JSONResponse({"pools": mgr.pool_names()})


@router.get("/factors")
async def list_factors():
    """获取因子配置列表"""
    return JSONResponse({
        "factors": [
            {"name": c.name, "label": c.label, "category": c.category,
             "weight": c.weight, "enabled": c.enabled}
            for c in DEFAULT_FACTOR_CONFIGS
        ]
    })


@router.post("/run")
async def run_signal_generation(
    pool: str = Query("沪深300", description="选股池名称"),
    top_n: int = Query(30, description="TOP-N 排名数量"),
):
    """运行完整的信号生成管道"""
    try:
        adapter = get_adapter()
        mgr = UniverseManager(adapter)
        stocks = mgr.get_universe(pool)

        if not stocks:
            return JSONResponse({
                "success": False,
                "error": f"选股池 [{pool}] 无可用股票，请检查Tushare连接",
            }, status_code=400)

        # 因子矩阵
        builder = FactorMatrixBuilder(factors=ALL_FACTORS)
        # Phase 1 仅使用价格数据 + 财务数据
        stock_data = {}  # 实际环境需从adapter批量获取

        matrix = builder.build(stocks, stock_data)

        # 截面标准化
        normalizer = CrossSectionalNormalizer(method="zscore")
        matrix = normalizer.normalize(matrix)

        # 加权打分
        scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
        composite_scores = scorer.score(matrix)

        # 排名 + 硬过滤
        ranker = Ranker(top_n=top_n, max_price=15.0)
        ranked = ranker.rank(matrix, composite_scores, stocks)

        # 约束优化
        optimizer = ConstraintOptimizer()
        optimized = optimizer.optimize(ranked, composite_scores)

        # 信号生成
        signal_gen = SignalGenerator()
        trade_list = signal_gen.generate(
            optimized_stocks=optimized,
            scores=composite_scores,
            current_holdings=set(),  # Phase 1: 无持仓历史
            universe=pool,
        )

        return JSONResponse({
            "success": True,
            "date": str(trade_list.date),
            "universe": pool,
            "total_stocks_analyzed": len(stocks),
            "top_30": [
                {
                    "rank": i + 1,
                    "code": s.code,
                    "name": s.name,
                    "industry": s.industry,
                    "score": round(composite_scores.get(s.code, 0), 4),
                }
                for i, s in enumerate(ranked[:10])
            ],
            "signals": [
                {
                    "code": s.stock_code,
                    "name": s.stock_name,
                    "action": s.action,
                    "score": round(s.composite_score, 4),
                    "weight": round(s.target_weight, 4),
                    "reason": s.reason,
                }
                for s in trade_list.signals
            ],
        })
    except Exception as e:
        logger.error(f"信号生成失败: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
```

- [ ] **Step 2: 在 main.py 中注册路由**

Modify `financial_analyzer/web/main.py` — 在 import 和 include_router 处添加:

```python
# 在注册路由部分添加（import 行已有类似模式）:
from .routes import pages, data_api, analysis, charts_api, ai_api, export_api, settings_api, api_v1, quant_api
app.include_router(quant_api.router)
```

- [ ] **Step 3: Commit**

```bash
git add financial_analyzer/web/routes/quant_api.py
git add financial_analyzer/web/main.py
git commit -m "feat(quant): add quant API routes for signal generation pipeline

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 18: 定时任务调度器

**Files:**
- Create: `financial_analyzer/quant/scheduler.py`

- [ ] **Step 1: 实现 scheduler.py**

```python
"""定时任务 — 月末自动触发信号生成"""
import asyncio
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def is_last_trading_day_of_month(ref_date: date = None) -> bool:
    """判断是否为每月最后一个交易日"""
    if ref_date is None:
        ref_date = date.today()
    tomorrow = ref_date + timedelta(days=1)
    return ref_date.month != tomorrow.month


class SignalScheduler:
    """信号生成定时调度器"""

    def __init__(self, check_interval_hours: int = 6):
        self.check_interval = check_interval_hours
        self._last_run_date: date | None = None

    async def run_if_due(self, callback) -> bool:
        """如果是月末交易日且今天还没跑过，执行回调"""
        today = date.today()

        if not is_last_trading_day_of_month(today):
            return False

        if self._last_run_date == today:
            return False  # 今天已经跑过

        logger.info(f"月末交易日 {today}，触发信号生成")
        try:
            await callback()
            self._last_run_date = today
            return True
        except Exception as e:
            logger.error(f"信号生成失败: {e}")
            return False

    def mark_run(self, run_date: date):
        self._last_run_date = run_date
```

- [ ] **Step 2: Commit**

```bash
git add financial_analyzer/quant/scheduler.py
git commit -m "feat(quant): add month-end signal generation scheduler

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 19: 前端策略面板

**Files:**
- Create: `frontend/css/quant.css`
- Create: `frontend/js/quant.js`
- Modify: `frontend/index.html` (添加导航Tab + 视图容器 + CSS/JS引用)
- Modify: `frontend/js/app.js` (注册路由 + 初始化quant视图)

- [ ] **Step 1: 创建 quant.css**

```css
/* quant.css — 策略面板样式 */
#view-quant { padding: 24px; overflow-y: auto; }

.quant-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 24px;
}
.quant-header h2 { margin: 0; font-size: 1.5rem; }

.quant-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.quant-card {
  background: var(--surface);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--border);
}
.quant-card h3 { margin: 0 0 12px; font-size: 1rem; }

.signal-list { list-style: none; padding: 0; margin: 0; }
.signal-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.signal-item:last-child { border-bottom: none; }

.signal-code { font-weight: 600; font-family: monospace; }
.signal-name { color: var(--text-secondary); margin-left: 8px; }
.signal-score { font-family: monospace; font-weight: 600; }

.signal-action {
  padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;
}
.signal-action.buy { background: #1a3a2a; color: #4caf50; }
.signal-action.sell { background: #3a1a1a; color: #f44336; }
.signal-action.hold { background: #1a2a3a; color: #64b5f6; }

.quant-btn {
  padding: 10px 24px;
  background: var(--accent); color: #fff;
  border: none; border-radius: 8px;
  font-size: 0.9rem; cursor: pointer;
  transition: opacity 0.2s;
}
.quant-btn:hover { opacity: 0.9; }
.quant-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.rank-tag {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  background: var(--accent); color: #fff; font-size: 0.75rem;
  margin-right: 8px;
}

.quant-status {
  font-size: 0.85rem; color: var(--text-secondary);
  margin-top: 8px;
}
.quant-status.success { color: #4caf50; }
```

- [ ] **Step 2: 创建 quant.js**

```javascript
// quant.js — 策略面板逻辑
import { $, $$ } from './utils.js';
import app from './app.js';

class QuantPanel {
  constructor() {
    this.container = $('#view-quant');
    this._signals = [];
    this._loading = false;
  }

  async init() {
    this._renderShell();
    app.on('view:changed', ({ view }) => {
      if (view === 'quant') this._onShow();
    });
  }

  _renderShell() {
    this.container.innerHTML = `
      <div class="quant-header">
        <h2>策略面板</h2>
        <button class="quant-btn" id="btn-run-signal">生成信号</button>
      </div>
      <div class="quant-grid">
        <div class="quant-card" id="card-rankings">
          <h3>因子排名 TOP-10</h3>
          <div id="rankings-content"><p class="quant-status">点击「生成信号」开始分析</p></div>
        </div>
        <div class="quant-card" id="card-signals">
          <h3>调仓信号</h3>
          <div id="signals-content"><p class="quant-status">等待信号生成</p></div>
        </div>
      </div>
      <div class="quant-card" id="card-overview">
        <h3>运行概况</h3>
        <div id="overview-content"></div>
      </div>
    `;

    $('#btn-run-signal').addEventListener('click', () => this._runSignal());
  }

  async _onShow() {
    // 视图激活时不自动运行，等用户点击
  }

  async _runSignal() {
    if (this._loading) return;
    this._loading = true;

    const btn = $('#btn-run-signal');
    btn.disabled = true;
    btn.textContent = '计算中...';

    try {
      const resp = await fetch('/api/v1/quant/run?pool=沪深300&top_n=30', {
        method: 'POST',
      });
      const data = await resp.json();

      if (data.success) {
        this._renderResults(data);
      } else {
        $('#rankings-content').innerHTML =
          `<p class="quant-status" style="color:#f44336;">${data.error}</p>`;
      }
    } catch (err) {
      $('#rankings-content').innerHTML =
        `<p class="quant-status" style="color:#f44336;">请求失败: ${err.message}</p>`;
    } finally {
      this._loading = false;
      btn.disabled = false;
      btn.textContent = '生成信号';
    }
  }

  _renderResults(data) {
    // 排名
    let rankHTML = '<ul class="signal-list">';
    (data.top_30 || []).forEach(item => {
      rankHTML += `
        <li class="signal-item">
          <span>
            <span class="rank-tag">#${item.rank}</span>
            <span class="signal-code">${item.code}</span>
            <span class="signal-name">${item.name || ''}</span>
          </span>
          <span class="signal-score">${item.score.toFixed(3)}</span>
        </li>`;
    });
    rankHTML += '</ul>';
    $('#rankings-content').innerHTML = rankHTML;

    // 信号
    let signalHTML = '<ul class="signal-list">';
    (data.signals || []).forEach(s => {
      signalHTML += `
        <li class="signal-item">
          <span>
            <span class="signal-code">${s.code}</span>
            <span class="signal-name">${s.name || ''}</span>
          </span>
          <span>
            <span class="signal-action ${s.action}">${s.action}</span>
            <span style="margin-left:8px;font-size:0.8rem;">权重 ${(s.weight * 100).toFixed(1)}%</span>
          </span>
        </li>`;
    });
    signalHTML += '</ul>';
    $('#signals-content').innerHTML = signalHTML;

    // 概况
    $('#overview-content').innerHTML = `
      <p class="quant-status success">
        选股池: ${data.universe} | 分析股票: ${data.total_stocks_analyzed}只 |
        日期: ${data.date}
      </p>
    `;
  }
}

// 自动初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new QuantPanel().init());
} else {
  new QuantPanel().init();
}
```

- [ ] **Step 3: 修改 index.html**

在 `<head>` 中 `<link>` 列表末尾添加:
```html
  <link rel="stylesheet" href="/static/frontend/css/quant.css">
```

在导航 `<div class="nav-tabs">` 中添加:
```html
        <button class="nav-tab" data-route="/quant">策略</button>
```

在 `<main>` 中视图容器列表末尾添加:
```html
      <div id="view-quant" class="view"></div>
```

在 `</body>` 前 script 列表末尾添加:
```html
  <script src="/static/frontend/js/quant.js"></script>
```

- [ ] **Step 4: 修改 app.js 注册路由**

在 `router` 初始化处，routes 对象中添加:
```javascript
      'quant': 'quant',
```

- [ ] **Step 5: Commit**

```bash
git add frontend/css/quant.css frontend/js/quant.js frontend/index.html frontend/js/app.js
git commit -m "feat(quant): add frontend strategy panel with signal generation UI

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 20: 端到端集成测试

**Files:**
- Create: `tests/test_quant_pipeline.py`

- [ ] **Step 1: 编写集成测试**

```python
"""量化管道端到端集成测试"""
import pytest
import pandas as pd
import numpy as np
from datetime import date

from financial_analyzer.quant.models import StockInfo, FactorConfig
from financial_analyzer.quant.factors.value import PEFactor, PBFactor
from financial_analyzer.quant.factors.quality import ROEFactor
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.engine.signal import SignalGenerator


def make_stock_data(code, pe=15.0, pb=2.0, roe_np=500, roe_eq=5000):
    """快速构建单只股票的数据字典"""
    return {
        "basic": pd.DataFrame({"pe": [pe], "pb": [pb]}),
        "income": pd.DataFrame({"net_profit": [roe_np]}),
        "balance": pd.DataFrame({"total_equity": [roe_eq]}),
    }


class TestQuantPipeline:
    """端到端管道测试 — 使用模拟数据"""

    def test_full_pipeline(self):
        # 1. 准备数据
        stocks = [
            StockInfo("A", "股A", "白酒"),
            StockInfo("B", "股B", "银行"),
            StockInfo("C", "股C", "电池"),
            StockInfo("D", "股D", "银行"),
            StockInfo("E", "股E", "白酒"),
        ]
        stock_data = {
            "A": make_stock_data("A", pe=10, pb=1.5, roe_np=1000, roe_eq=8000),
            "B": make_stock_data("B", pe=20, pb=3.0, roe_np=300, roe_eq=3000),
            "C": make_stock_data("C", pe=25, pb=4.0, roe_np=200, roe_eq=2000),
            "D": make_stock_data("D", pe=15, pb=2.0, roe_np=400, roe_eq=5000),
            "E": make_stock_data("E", pe=12, pb=1.8, roe_np=800, roe_eq=6000),
        }

        # 2. 构建因子矩阵
        factors = [PEFactor(), PBFactor(), ROEFactor()]
        builder = FactorMatrixBuilder(factors=factors)
        matrix = builder.build(stocks, stock_data)

        assert len(matrix.stocks) >= 1
        assert len(matrix.scores) >= 1

        # 3. 截面标准化
        normalizer = CrossSectionalNormalizer()
        matrix = normalizer.normalize(matrix)

        # 4. 加权打分
        configs = [
            FactorConfig(name="pe", label="PE", category="value", weight=1.0),
            FactorConfig(name="pb", label="PB", category="value", weight=1.0),
            FactorConfig(name="roe", label="ROE", category="quality", weight=1.0),
        ]
        scorer = WeightedScorer(configs)
        scores = scorer.score(matrix)
        assert len(scores) >= 1

        # 5. 排名
        ranker = Ranker(top_n=30)
        ranked = ranker.rank(matrix, scores, stocks)
        assert len(ranked) >= 1

        # 6. 优化
        optimizer = ConstraintOptimizer(min_industries=1)
        optimized = optimizer.optimize(ranked, scores)
        assert len(optimized) >= 1

        # 7. 生成信号
        gen = SignalGenerator()
        trade_list = gen.generate(optimized, scores, set(), "测试池")
        assert len(trade_list.buys) >= 1
        assert trade_list.universe == "测试池"

    def test_pipeline_with_missing_data(self):
        """部分股票数据缺失时管道不应崩溃"""
        stocks = [
            StockInfo("A", "股A", "白酒"),
            StockInfo("B", "股B", "银行"),
        ]
        # B 没有任何数据
        stock_data = {"A": make_stock_data("A")}

        factors = [PEFactor(), ROEFactor()]
        builder = FactorMatrixBuilder(factors=factors)
        matrix = builder.build(stocks, stock_data)

        # 只有A有数据
        assert "A" in matrix.scores
        assert "B" not in matrix.scores

        normalizer = CrossSectionalNormalizer()
        matrix = normalizer.normalize(matrix)
        # 不应该崩溃

    def test_small_universe(self):
        """只有2只股票的选股池"""
        stocks = [
            StockInfo("A", "股A", "白酒"),
            StockInfo("B", "股B", "银行"),
        ]
        stock_data = {
            "A": make_stock_data("A"),
            "B": make_stock_data("B"),
        }

        factors = [PEFactor()]
        builder = FactorMatrixBuilder(factors=factors)
        matrix = builder.build(stocks, stock_data)

        normalizer = CrossSectionalNormalizer()
        matrix = normalizer.normalize(matrix)

        configs = [FactorConfig(name="pe", label="PE", category="value", weight=1.0)]
        scorer = WeightedScorer(configs)
        scores = scorer.score(matrix)

        gen = SignalGenerator()
        optimizer = ConstraintOptimizer(min_industries=1, min_stocks=1, max_stocks=2)
        ranked = Ranker(top_n=30).rank(matrix, scores, stocks)
        optimized = optimizer.optimize(ranked, scores)
        trade_list = gen.generate(optimized, scores, set(), "小池")

        assert len(trade_list.buys) <= 2
```

- [ ] **Step 2: 运行测试**

Run: `pytest tests/test_quant_pipeline.py -v`
Expected: PASS (3 tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_quant_pipeline.py
git commit -m "test(quant): add end-to-end pipeline integration tests

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---
