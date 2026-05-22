# Tushare 数据扩展与导入优化 — 设计说明

## 概述

基于用户持有的高权限 Tushare Token（2000+ 积分级别），扩展数据导入能力，从当前的 7 个接口增至 19 个，分阶段推进。Phase 1 聚焦于直接增强 7 维分析框架的核心数据。

## 当前状态

**已接入 Tushare 接口（7 个）**：daily, daily_basic, stock_basic, fina_indicator, income, balancesheet, cashflow

**已声明数据类型但 Tushare handler 缺失（2 个）**：fina_audit, fina_mainbz

**确认可用的新增接口（12 个）**：moneyflow, stk_holdernumber, top10_holders, top10_floatholders, dividend, block_trade, margin, margin_detail, hk_hold, weekly, monthly, index_daily

**可调用但数据因测试标的为空（5 个，Phase 2 处理）**：forecast, express, repurchase, stk_holdertrade, share_float

## 实现方案

方案 A：适配器扩展 + 分层标准化，沿用现有 `adapter → normalizer → data_service → analyzer` 管道。

## Phase 1 接口清单（12 新增 + 2 修复）

| # | Tushare API | 数据内容 | 增强维度 | 列名策略 |
|---|---|---|---|---|
| 1 | moneyflow | 个股资金流向（超大单/大单/中单/小单） | L1 市场 | 保持原始 |
| 2 | stk_holdernumber | 股东人数变化趋势 | L2 会计质量 | 保持原始 |
| 3 | top10_holders | 前十大股东明细 | L1/L2 | 保持原始 |
| 4 | top10_floatholders | 前十大流通股东 | L1/L2 | 保持原始 |
| 5 | margin | 融资融券交易汇总 | L1 市场 | 保持原始 |
| 6 | margin_detail | 融资融券交易明细 | L1 市场 | 保持原始 |
| 7 | dividend | 分红送股记录 | L6 估值 | 保持原始 |
| 8 | block_trade | 大宗交易明细 | L1/L2 | 保持原始 |
| 9 | hk_hold | 沪深股通持股明细 | L1 市场 | 保持原始 |
| 10 | weekly / monthly | 周线/月线行情 | L1/L6 | 保持原始 |
| 11 | fina_audit | 审计意见（handler 补全） | L2 | 保持原始 |
| 12 | fina_mainbz | 主营业务构成（handler 补全） | L1 | 保持原始 |

## 数据管道架构

### 数据类型分组

| 分组 | 加载时机 | 包含类型 |
|---|---|---|
| BASIC_DATA_TYPES | 即时阻塞 | daily, basic, daily_basic, stock_basic |
| MARKET_DATA_TYPES (新) | 后台异步 | moneyflow, margin, margin_detail, hk_hold, block_trade, weekly, monthly, stk_holdernumber |
| FINANCIAL_DATA_TYPES | 后台异步 | income, balance, cashflow, financial, dividend, top10_holders, top10_floatholders, fina_audit, fina_mainbz |

首屏保持快速加载（< 2秒），市场数据和财务报表后台异步加载，完成后通过 HX-Trigger 刷新 UI。

### 列名策略

新增 12 个接口保持 Tushare 原始列名，不做标准化映射。只做基本类型转换：日期格式化、`pd.to_numeric` 处理数值列。原因：这些接口是 Tushare 独有的，不存在多源切换需求，标准化层维护成本大于收益。

已有的跨源数据类型（daily/income/balance/cashflow）继续保持现有标准化逻辑。

## 新增分析模块

### 1. ShareholderAnalyzer（股东分析）
- 数据源：top10_holders, top10_floatholders, stk_holdernumber
- 输出：股东人数趋势、机构持股占比变化、股权集中度评分
- 增强：L1 商业模式（+股权结构子维度）+ L2 治理质量

### 2. CapitalFlowAnalyzer（资金面分析）
- 数据源：moneyflow, margin, margin_detail, hk_hold, block_trade
- 输出：主力资金净流向趋势、融资余额变化、北向资金持仓变化、大宗交易折溢价
- 增强：L1 市场维度（新增"资金面"子维度）

### 3. 估值增强（扩展 DCF 分析 + PE 分位）
- 数据源：dividend, weekly, monthly
- 输出：股息率历史及稳定性、DDM 估值锚点、周线/月线 PE 分位
- 增强：L6 估值维度

### 综合评分权重调整
L1（商业模式）权重 5% → 8%，吸纳股东结构和资金面子维度。

## Web UI

### KPI 卡片区（用户可配置）
- 顶部提供「自定义卡片」入口（齿轮图标按钮）
- 弹出勾选面板，用户自由选择展示哪些 KPI 卡片
- 默认选中：当前价格、涨跌幅、PE、总市值、成交量（5 个核心卡片）
- 新增可选：主力净流入、融资余额、北向持股占比、股东人数、股息率
- 选择持久化到 config.json，自适应列布局

### 数据表格面板
在已加载数据类型表格中显示新增类型及其加载状态（加载中/已完成/不可用）

### 分析结果区
新增 3 个可折叠面板：股东结构、资金面、估值增强。数据缺失时显示「暂无相关数据」

### 导出
新增数据类型自动出现在导出模态框的数据类型选择列表中，现有 Excel/CSV/PDF/Word 导出逻辑基于 DataFrame 列名自动生成表头，无需额外适配。

## 配置扩展

config.json 新增 `data_modules` 配置段：

```json
{
  "data_modules": {
    "moneyflow": true,
    "margin": true,
    "hk_hold": true,
    "block_trade": true,
    "stk_holdernumber": true,
    "top10_holders": true,
    "dividend": true,
    "weekly_monthly": true
  }
}
```

`data_modules` 缺失时默认全部启用。可在 Web UI Token 配置面板中勾选。

## 错误处理

- Tushare 接口调用失败 → 对应类型标记 unavailable，UI 显示「数据暂不可用」，不阻塞其他数据
- Token 未配置 → 核心行情通过 akshare/sina 可用，扩展数据 KPI 显示 `--`
- 数据为空（如无分红记录）→ KPI 显示 `--`，分析面板显示「暂无相关数据」

## 测试策略

1. 单元测试：新增 normalizer 基本类型转换验证（列存在性、日期格式、数值类型）
2. 集成测试：adapter `_get_tushare` 新增 handler 正确调用并返回 DataFrame
3. Web 集成测试：data_api 验证新数据类型的获取和 session 存储
4. 手动验证：真实 Token 对 000001.SZ 端到端验证

## Phase 2/3 预览（不在本次范围）

- Phase 2：forecast, express, repurchase, stk_holdertrade, broker_recommend, 行业对标（ths_daily/index_weight）
- Phase 3：宏观指标（cn_cpi/cn_pmi/cn_m/macro）、基金持仓（fund_portfolio）
