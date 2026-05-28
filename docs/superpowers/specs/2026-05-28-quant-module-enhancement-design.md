# 量化模块四大功能增强 — 设计规格

## 概述

量化模块核心流水线（数据→因子→信号→回测→模拟盘）已完整贯通，API 和前端均已对接。本次迭代在已有基础上，按自底向上顺序增强四大功能：因子分析深度挖掘、回测分析增强、风控与仓位管理、策略模板与批量回测。

## 当前状态

### 已有能力

| 模块 | 能力 | 局限 |
|------|------|------|
| engine/ | 因子矩阵→标准化→线性加权打分→贪心优化→均等权重信号 | 无行业中性化、无非线性打分、无风险平价 |
| backtest/ | 月频调仓回测、基础绩效指标（Sharpe/回撤/胜率）、单因子相关归因 | 无基准对比、无滚动指标、无滑点/印花税 |
| factors/ | 6 类 22 个因子，BaseFactor 抽象接口 | 无 TTM 滚动、无行业中性化预处理 |
| paper_trading/ | 持仓管理、交易流水、盈亏快照 | 无涨跌停/T+1/止损止盈、均等权重 |

### 技术约束

- 保持现有代码架构不变，扩展现有模块
- 不引入新的前端依赖（使用已有 ECharts + htmx）
- 使用已有的 task_store + 轮询模式处理异步任务
- 新因子只需继承 BaseFactor 并注册
- 新优化器/仓位策略通过抽象基类 + 具体实现扩展

---

## 阶段 1：因子分析深度挖掘

### 1.1 因子 IC/IR 分析

**核心逻辑（`quant/engine/factor_analyzer.py`）：**

- IC（Information Coefficient）：每期因子截面值与下一期收益的 Spearman 秩相关系数
- IR（Information Ratio）：IC 均值 / IC 标准差，衡量因子预测稳定性
- 计算流程：在回测循环的每月调仓点，记录当期各因子的截面 IC 值，回测结束后汇总统计
- 输出指标：IC 均值、IC 标准差、IR、IC>0 占比、IC 时序数据

**类设计：**

```python
class FactorAnalyzer:
    def __init__(self, factors: list[BaseFactor], normalizer: CrossSectionalNormalizer):
        ...

    def compute_monthly_ic(self, factor_matrix: FactorMatrix, forward_returns: pd.Series) -> dict[str, float]:
        """计算单月各因子的 IC 值"""
        ...

    def compute_ic_summary(self) -> pd.DataFrame:
        """汇总所有月份的 IC，计算均值/标准差/IR/胜率"""
        ...

    def get_ic_timeseries(self) -> dict[str, list[float]]:
        """返回各因子 IC 的时序数据，用于绘图"""
        ...
```

**集成方式：** 在 `BacktestEngine` 的月度循环中，调用 `factor_analyzer.compute_monthly_ic()` 收集数据，回测结束后调用 `compute_ic_summary()` 生成报告。

### 1.2 因子衰减分析

- 计算因子在不同持仓周期（1/2/3/6/12 个月）下的平均 IC
- 实现：对回测结果的时间序列，按不同窗口计算 forward return，分别求 IC
- 输出：衰减曲线数据（x=持仓月数, y=平均 IC）

```python
def compute_decay_curve(self, holding_periods: list[int] = [1,2,3,6,12]) -> dict[str, list[float]]:
    """各因子在不同持仓周期下的平均 IC"""
    ...
```

### 1.3 因子相关性矩阵

- 计算所有因子截面值的 Spearman 相关系数矩阵
- 取所有月份的相关矩阵求平均
- 高相关因子（|corr| > 0.7）标红警告
- 输出：二维矩阵 + 标签列表，前端用 ECharts heatmap 渲染

```python
def compute_correlation_matrix(self) -> tuple[np.ndarray, list[str]]:
    """返回因子相关性矩阵和因子名称列表"""
    ...
```

### 1.4 因子表现报告

- 分年度因子多空收益：每年按因子排序分 5 组，计算 TOP 组 - BOTTOM 组的收益
- 因子排名变化度：复用已有的 `compute_factor_turnover`
- 综合评分：`score = IC_mean × IR × (1 - max_corr)` 排序，帮助用户选择低相关高 IC 的因子组合

### API 端点

```
POST /api/v1/quant/factor-analysis/run
  参数：pool, factors（因子列表）, start_date, end_date
  返回：task_id

GET /api/v1/quant/factor-analysis/status/{task_id}
  返回：进度信息

GET /api/v1/quant/factor-analysis/result/{task_id}
  返回：
    - ic_summary: [{factor, ic_mean, ic_std, ir, ic_positive_rate}]
    - ic_timeseries: {factor_name: [ic_values]}
    - decay_curve: {factor_name: [ic_by_period]}
    - correlation_matrix: {labels, matrix}
    - annual_performance: [{year, factor, long_short_return}]
    - composite_score: [{factor, score}]
```

### 前端设计

新增"因子分析"Tab（与信号生成、回测分析、敏感性分析、模拟交易并列）：

```
┌─────────────────────────────────────────────────────────────┐
│  因子分析                                                     │
│                                                               │
│  参数区: [选股池] [因子选择] [起止日期] [运行分析]              │
│                                                               │
│  结果区:                                                      │
│  ┌─────────────────────┐ ┌────────────────────────────────┐  │
│  │  IC 时序图           │ │  因子排名表                     │  │
│  │  (ECharts 折线图)    │ │  因子 | IC均值 | IR | 胜率 | 评分│  │
│  └─────────────────────┘ └────────────────────────────────┘  │
│  ┌─────────────────────┐ ┌────────────────────────────────┐  │
│  │  相关性热力图         │ │  衰减曲线                      │  │
│  │  (ECharts heatmap)  │ │  (ECharts 折线图)              │  │
│  └─────────────────────┘ └────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  分年度多空收益柱状图                                   │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 阶段 2：回测分析增强

### 2.1 基准对比

**新增模块（`quant/backtest/benchmark.py`）：**

- 基准数据获取：复用 `DataFetcher` 获取基准指数（沪深300: 000300.SH、中证500: 000905.SH）日线数据
- 超额收益计算：`excess_return = portfolio_return - benchmark_return`
- 信息比率：`IR = annualized_excess_return / tracking_error`
- 跟踪误差：`TE = std(excess_returns) × sqrt(12)`

```python
class BenchmarkComparator:
    def __init__(self, benchmark_code: str, data_fetcher: DataFetcher):
        ...

    def compute_excess_returns(self, portfolio_returns: pd.Series) -> pd.Series:
        ...

    def compute_information_ratio(self, excess_returns: pd.Series) -> float:
        ...

    def compute_tracking_error(self, excess_returns: pd.Series) -> float:
        ...
```

**集成方式：** `BacktestEngine` 的 `run()` 方法增加 `benchmark_code` 参数，回测结束后调用 `BenchmarkComparator` 生成基准对比数据。

### 2.2 滚动绩效指标

**新增模块（`quant/backtest/rolling_metrics.py`）：**

- 滚动 Sharpe（12 个月窗口）：每月底计算过去 12 个月的年化 Sharpe
- 滚动最大回撤（12 个月窗口）
- 滚动 Alpha/Beta（相对基准，12 个月窗口）：OLS 回归 `portfolio_return = alpha + beta × benchmark_return + epsilon`

```python
class RollingMetricsCalculator:
    def __init__(self, window: int = 12):
        ...

    def rolling_sharpe(self, returns: pd.Series) -> pd.Series:
        ...

    def rolling_drawdown(self, equity_curve: pd.Series) -> pd.Series:
        ...

    def rolling_alpha_beta(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> tuple[pd.Series, pd.Series]:
        ...
```

### 2.3 分段归因增强

**扩展 `quant/backtest/attribution.py`：**

- 多因子回归归因：截面 OLS `R_i = beta_1×F_1 + beta_2×F_2 + ... + epsilon`，计算各因子的平均 beta 和 t 统计量
- 行业归因：按行业分组计算各行业对组合收益的贡献
- 分年度/季度绩效表：按时间分组汇总收益、Sharpe、回撤

```python
def multi_factor_attribution(self, factor_matrix: FactorMatrix, returns: pd.Series) -> dict[str, float]:
    """多因子截面回归归因，返回各因子 beta"""
    ...

def industry_attribution(self, holdings: dict, returns: pd.Series) -> dict[str, float]:
    """按行业分组计算收益贡献"""
    ...

def period_performance_table(self, returns: pd.Series, freq: str = 'Y') -> pd.DataFrame:
    """分年度/季度绩效汇总"""
    ...
```

### 2.4 交易成本精细化

- 滑点：买入加 X%，卖出减 X%（默认 0.1%，可配置 0.05%~0.3%）
- 印花税：卖出收取 0.05%（A 股标准）
- 修改 `BacktestEngine._execute_trades()` 中的价格计算逻辑
- 前端：回测参数区新增"交易成本"面板（滑点滑块、印花税开关）

### API 变更

扩展现有回测端点 `POST /api/v1/backtest/run`：

```
新增参数：
  - benchmark_code: str = "000300.SH"
  - slippage_pct: float = 0.1
  - stamp_tax: bool = True
  - rolling_window: int = 12

返回结果新增字段：
  - benchmark_returns: [float]  # 基准收益序列
  - excess_returns: [float]  # 超额收益序列
  - information_ratio: float
  - tracking_error: float
  - rolling_sharpe: [float]
  - rolling_drawdown: [float]
  - rolling_alpha: [float]
  - rolling_beta: [float]
  - factor_betas: {factor: beta}  # 多因子归因
  - industry_attribution: {industry: contribution}
  - period_performance: [{period, return, sharpe, max_dd}]
  - cost_breakdown: {commission, slippage, stamp_tax, total}
```

### 前端设计

回测结果区新增：

```
┌──────────────────────────────────────────────────────┐
│  基准对比                                              │
│  ┌─────────────────────┐ ┌────────────────────────┐  │
│  │  权益曲线（含基准）   │ │  超额收益柱状图         │  │
│  └─────────────────────┘ └────────────────────────┘  │
│  ┌─────────────────────┐ ┌────────────────────────┐  │
│  │  滚动 Sharpe / Alpha │ │  滚动 Beta / 回撤      │  │
│  └─────────────────────┘ └────────────────────────┘  │
│  ┌─────────────────────┐ ┌────────────────────────┐  │
│  │  多因子归因柱状图     │ │  行业归因饼图           │  │
│  └─────────────────────┘ └────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐    │
│  │  分年度绩效表 + 成本明细                       │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

---

## 阶段 3：风控与仓位管理

### 3.1 仓位分配策略

**新增模块（`quant/engine/position_sizer.py`）：**

```python
class PositionSizer(ABC):
    @abstractmethod
    def compute_weights(self, scores: pd.Series, cov_matrix: np.ndarray, risk_budget: float = None) -> pd.Series:
        """根据打分和协方差矩阵计算各资产权重"""
        ...

class EqualWeightSizer(PositionSizer):
    """均等分配（现有逻辑）"""
    ...

class RiskParitySizer(PositionSizer):
    """风险平价：各资产对组合风险贡献相等"""
    ...

class MinVarianceSizer(PositionSizer):
    """最小方差：全局最小方差组合"""
    ...

class KellySizer(PositionSizer):
    """Kelly 公式：基于胜率和赔率"""
    ...

class MarketCapSizer(PositionSizer):
    """市值加权"""
    ...
```

**集成方式：** `ConstraintOptimizer` 原来硬编码均等权重，改为接受 `PositionSizer` 参数。`SignalGenerator` 的权重分配调用 `PositionSizer.compute_weights()`。

### 3.2 最大回撤控制

**新增模块（`quant/risk/drawdown_control.py`）：**

```python
class DrawdownController:
    def __init__(self, max_drawdown_pct: float = 15.0, step_pct: float = 5.0, reduce_ratio: float = 0.25):
        self.max_drawdown_pct = max_drawdown_pct  # 回撤阈值
        self.step_pct = step_pct  # 每超 5% 减仓
        self.reduce_ratio = reduce_ratio  # 每步减 25%

    def compute_position_scale(self, current_drawdown: float) -> float:
        """根据当前回撤计算仓位比例（0~1）"""
        if current_drawdown < self.max_drawdown_pct:
            return 1.0
        excess = current_drawdown - self.max_drawdown_pct
        steps = int(excess / self.step_pct) + 1
        return max(0.0, 1.0 - steps * self.reduce_ratio)
```

**集成方式：** 在 `BacktestEngine` 的月度循环中，计算当前组合回撤，调用 `DrawdownController.compute_position_scale()` 得到仓位比例，按比例调整持仓。

### 3.3 止盈止损规则

**新增模块（`quant/risk/stop_loss.py`）：**

```python
class StopLossManager:
    def __init__(self, stop_loss_pct: float = -10.0, take_profit_pct: float = 30.0, portfolio_stop_pct: float = None):
        self.stop_loss_pct = stop_loss_pct / 100  # 个股止损
        self.take_profit_pct = take_profit_pct / 100  # 个股止盈
        self.portfolio_stop_pct = portfolio_stop_pct / 100 if portfolio_stop_pct else None  # 组合止损

    def check_stock_stop(self, cost_price: float, current_price: float) -> str | None:
        """检查个股止盈止损，返回 'stop_loss'/'take_profit'/None"""
        pnl_pct = (current_price - cost_price) / cost_price
        if pnl_pct <= self.stop_loss_pct:
            return 'stop_loss'
        if pnl_pct >= self.take_profit_pct:
            return 'take_profit'
        return None

    def check_portfolio_stop(self, current_drawdown: float) -> bool:
        """检查组合止损，返回是否触发"""
        if self.portfolio_stop_pct is None:
            return False
        return current_drawdown >= self.portfolio_stop_pct
```

**集成方式：** 在 `PortfolioManager.execute()` 中，买卖前检查止盈止损规则。

### 3.4 交易约束增强

- T+1 交割：`PortfolioManager` 记录每笔买入的日期，卖出时检查是否满足 T+1
- 涨跌停模拟：`BacktestEngine._execute_trades()` 中检查当日涨跌幅是否触及 10% 限制
- 前端：参数区可开关这些约束（默认关闭，避免影响现有行为）

### API 变更

扩展现有端点参数：

```
POST /api/v1/backtest/run 新增参数：
  - position_sizer: str = "equal"  # equal/risk_parity/min_variance/kelly/market_cap
  - max_drawdown_pct: float = 15.0
  - stop_loss_pct: float = -10.0
  - take_profit_pct: float = 30.0
  - enable_t_plus_1: bool = False
  - enable_limit_check: bool = False

POST /api/v1/quant/run 新增参数：
  - position_sizer: str = "equal"

返回结果新增字段：
  - risk_events: [{date, type, detail}]  # 止盈止损/回撤控制触发记录
  - position_sizer_used: str
```

### 前端设计

回测参数区新增"风控配置"折叠面板：

```
┌─────────────────────────────────────────┐
│  风控配置 [展开/折叠]                     │
│                                          │
│  仓位策略: [均等 ▼]                       │
│  最大回撤阈值: [15]%                      │
│  个股止损: [-10]%                         │
│  个股止盈: [+30]%                         │
│  □ 启用 T+1 交割约束                      │
│  □ 启用涨跌停限制                         │
└─────────────────────────────────────────┘
```

回测结果区新增风控事件时间线。

---

## 阶段 4：策略模板与批量回测

### 4.1 策略模板库

**模板格式（JSON）：**

```json
{
  "name": "价值投资",
  "description": "低估值 + 高分红 + 低波动，适合长期持有",
  "factors": [
    {"name": "pe_ttm", "weight": 0.3, "direction": -1},
    {"name": "pb", "weight": 0.2, "direction": -1},
    {"name": "dividend_yield", "weight": 0.3, "direction": 1},
    {"name": "volatility_60d", "weight": 0.2, "direction": -1}
  ],
  "position_sizer": "risk_parity",
  "risk": {
    "max_drawdown_pct": 15,
    "stop_loss_pct": -10,
    "take_profit_pct": 30
  },
  "rebalance_freq": "monthly"
}
```

**预置模板（5 个）：**

| 模板名 | 因子组合 | 仓位策略 | 适合场景 |
|--------|----------|----------|----------|
| 价值投资 | PE + PB + FCFYield + LowVol | 风险平价 | 长期稳健 |
| 成长动量 | RevenueGrowth + ProfitGrowth + Momentum12M | 均等 | 趋势跟踪 |
| 质量红利 | ROE + DividendYield + PiotroskiF | 最小方差 | 防守配置 |
| 多因子均衡 | 7 类各选 1 个代表因子 | 均等 | 通用策略 |
| 低波防守 | LowVol + MaxDrawdown + 流动比率 | 风险平价 | 熊市防守 |

**新增模块（`quant/engine/strategy_template.py`）：**

```python
class StrategyTemplate:
    def __init__(self, name, description, factors, position_sizer, risk, rebalance_freq):
        ...

    @classmethod
    def from_json(cls, path: str) -> 'StrategyTemplate':
        ...

    def to_json(self, path: str):
        ...

    def to_factor_configs(self) -> list[FactorConfig]:
        """转换为引擎可用的 FactorConfig 列表"""
        ...

class TemplateManager:
    TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

    def list_templates(self) -> list[dict]:
        ...

    def load_template(self, name: str) -> StrategyTemplate:
        ...

    def save_template(self, template: StrategyTemplate):
        ...

    def clone_template(self, source_name: str, new_name: str, overrides: dict) -> StrategyTemplate:
        ...
```

### 4.2 参数网格搜索

**新增模块（`quant/engine/grid_search.py`）：**

```python
class GridSearchEngine:
    def __init__(self, backtest_engine: BacktestEngine):
        ...

    def search(self, param_grid: dict[str, list], pool: str, start_date: str, end_date: str) -> list[dict]:
        """
        param_grid 示例：
        {
            "pe_ttm.weight": [0.1, 0.2, 0.3, 0.4],
            "momentum_12m.weight": [0.1, 0.2, 0.3]
        }
        返回：[{params, sharpe, total_return, max_drawdown, ...}]
        """
        ...
```

- 反过拟合：训练集/验证集 70/30 分割，报告两个集合的绩效差异
- 输出：最优参数组合 + 参数敏感性热力图（复用已有 heatmap 组件）

### 4.3 批量回测对比

**新增模块（`quant/backtest/batch_backtest.py`）：**

```python
class BatchBacktestRunner:
    def __init__(self, backtest_engine: BacktestEngine, scheduler: TaskScheduler):
        ...

    def run_batch(self, strategies: list[StrategyTemplate], pool: str, start_date: str, end_date: str) -> str:
        """并行运行多个策略回测，返回 batch_id"""
        ...

    def get_batch_status(self, batch_id: str) -> dict:
        """返回各策略的进度"""
        ...

    def get_batch_result(self, batch_id: str) -> dict:
        """返回对比结果"""
        ...
```

**对比结果：**
- 权益曲线叠加图（所有策略 + 基准）
- 指标对比表（Sharpe/回撤/收益/换手率 等并排显示）
- 策略排名（按 Sharpe 排序）

### API 端点

```
GET /api/v1/quant/templates
  返回：模板列表 [{name, description, factors, ...}]

POST /api/v1/quant/templates
  参数：模板 JSON
  返回：保存结果

POST /api/v1/quant/templates/{name}/clone
  参数：new_name, overrides
  返回：克隆结果

POST /api/v1/quant/grid-search
  参数：pool, param_grid, start_date, end_date
  返回：task_id

GET /api/v1/quant/grid-search/result/{task_id}
  返回：搜索结果 + 敏感性热力图数据

POST /api/v1/quant/batch-backtest
  参数：strategies（模板名列表）, pool, start_date, end_date
  返回：batch_id

GET /api/v1/quant/batch-backtest/status/{batch_id}
  返回：各策略进度

GET /api/v1/quant/batch-backtest/result/{batch_id}
  返回：对比结果
```

### 前端设计

新增"策略管理"Tab：

```
┌──────────────────────────────────────────────────────┐
│  策略管理                                              │
│                                                        │
│  ┌─ 策略模板库 ──────────────────────────────────────┐ │
│  │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │ │
│  │ │价值   │ │成长   │ │质量   │ │均衡   │ │低波   │    │ │
│  │ │投资   │ │动量   │ │红利   │ │多因子 │ │防守   │    │ │
│  │ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │ │
│  │ [克隆] [编辑] [自定义策略...]                      │ │
│  └───────────────────────────────────────────────────┘ │
│                                                        │
│  ┌─ 批量回测 ────────────────────────────────────────┐ │
│  │ 选择策略: ☐价值 ☐成长 ☐质量 ☐均衡 ☐自定义1        │ │
│  │ [选股池] [起止日期] [运行批量回测]                   │ │
│  │                                                    │ │
│  │ 结果对比:                                          │ │
│  │ ┌─────────────────────┐ ┌──────────────────────┐  │ │
│  │ │ 权益曲线叠加图        │ │ 指标对比表            │  │ │
│  │ └─────────────────────┘ └──────────────────────┘  │ │
│  └───────────────────────────────────────────────────┘ │
│                                                        │
│  ┌─ 参数搜索 ────────────────────────────────────────┐ │
│  │ 因子1: [PE ▼] 权重范围: [0.1]~[0.5] 步长: [0.1]   │ │
│  │ 因子2: [动量 ▼] 权重范围: [0.1]~[0.5] 步长: [0.1] │ │
│  │ [运行搜索]                                         │ │
│  │ ┌─────────────────────┐ ┌──────────────────────┐  │ │
│  │ │ 敏感性热力图          │ │ 最优参数详情          │  │ │ │
│  │ └─────────────────────┘ └──────────────────────┘  │ │
│  └───────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 文件变更汇总

### 新增文件

| 文件 | 阶段 | 用途 |
|------|------|------|
| `quant/engine/factor_analyzer.py` | 1 | 因子 IC/IR/衰减/相关性分析 |
| `quant/backtest/benchmark.py` | 2 | 基准数据获取和超额收益计算 |
| `quant/backtest/rolling_metrics.py` | 2 | 滚动绩效指标 |
| `quant/engine/position_sizer.py` | 3 | 仓位分配策略（5 种） |
| `quant/risk/drawdown_control.py` | 3 | 回撤控制 |
| `quant/risk/stop_loss.py` | 3 | 止盈止损规则 |
| `quant/engine/strategy_template.py` | 4 | 策略模板加载/保存/克隆 |
| `quant/engine/grid_search.py` | 4 | 参数网格搜索 |
| `quant/backtest/batch_backtest.py` | 4 | 批量回测编排 |
| `quant/templates/*.json` | 4 | 预置策略模板 |

### 修改文件

| 文件 | 阶段 | 变更 |
|------|------|------|
| `quant/backtest/engine.py` | 1,2,3 | 集成因子分析、基准对比、仓位策略、风控 |
| `quant/backtest/metrics.py` | 2 | 新增基准对比指标 |
| `quant/backtest/attribution.py` | 2 | 多因子回归归因、行业归因 |
| `quant/engine/optimizer.py` | 3 | 集成 PositionSizer |
| `quant/engine/signal.py` | 3 | 权重分配调用 PositionSizer |
| `quant/paper_trading/portfolio.py` | 3 | 集成止盈止损、T+1、涨跌停 |
| `quant/models.py` | 3 | 扩展配置模型 |
| `web/routes/quant_api.py` | 1,2,3,4 | 新增/扩展 API 端点 |
| `web/static/quant-charts.js` | 1,2,4 | 新增图表渲染器 |
| `web/templates/base.html` | 1,4 | 新增 Tab 和 UI 面板 |

---

## 验证标准

每个阶段完成后：
- 新增单元测试覆盖核心逻辑（IC 计算、仓位策略、止盈止损等）
- Web 服务器可启动，新功能在浏览器中可正常操作
- 控制台无 JavaScript 错误
- 现有功能无回归
