# Cycle 3 — 回测可视化图表实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在回测结果面板中添加三个可视化图表 — 累计收益曲线（Chart.js Line）、回撤曲线（Chart.js Line + 填充）、月度收益热力图（HTML Table + CSS）。

**设计规格:** `docs/superpowers/specs/2026-05-28-backtest-enhancement-design.md`（阶段 2）

**关键约束:**
- Chart.js 已通过 `bundle.js` 加载为 `window.Chart`，无需额外引入 CDN
- 前端保持 Vanilla JS SPA 架构
- 后端数据通过现有 `_serialize_result` 函数返回，前端 `renderBacktestResults` 消费

---

## 现状分析

### 已有数据
- `cumulative_returns`: 已在 `_serialize_result` 中从 snapshots 计算（line 113-120）
- `benchmark_cumulative`: 已在 `_serialize_result` 中从 benchmark_values 计算（line 123-129）
- `monthly_returns`: 由 `MetricsCalculator.compute` 返回，已在 metrics dict 中
- `benchmark_monthly_returns`: 同上
- `snapshots[].date`: YYYYMMDD 格式日期字符串

### 缺失数据
- `drawdown_series`: 需从 `cumulative_returns` 计算逐期回撤
- `monthly_grid`: 需从 `monthly_returns` + snapshot dates 构建年x月二维网格

### 前端现状
- `renderBacktestResults()` (quant.js line 921) 拼接 summaryHTML + metricsHTML + benchmarkHTML + monthlyHTML + tradesHTML + attrHTML
- 无任何 Chart.js 图表渲染
- 月度收益使用自定义柱状图 `renderMonthlyBars()`

---

## 布局设计

```text
+---------------------------------------------------+
|  指标卡片（已有）                                   |
+---------------------------------------------------+
|  累计收益曲线 chart-cumulative（全宽，Chart.js）     |
+------------------------+--------------------------+
|  回撤曲线 chart-dd     |  月度收益热力图 heatmap    |
|  （Chart.js Line+填充） |  （HTML Table + CSS）     |
+------------------------+--------------------------+
|  调仓记录 / 因子归因（已有）                         |
+---------------------------------------------------+
```

---

## Task 1: 后端 — 计算 drawdown_series

**文件:** `financial_analyzer/web/routes/backtest_api.py`
**函数:** `_serialize_result`
**位置:** 在现有 `cumulative_returns` 计算之后（约 line 120）

**逻辑:**
```python
drawdown_series = []
if cumulative_returns:
    peak = 0.0
    for cr in cumulative_returns:
        if cr > peak:
            peak = cr
        dd = cr - peak
        drawdown_series.append(round(dd, 6))
```

**返回值:** 新增 `"drawdown_series": drawdown_series` 到返回 dict（放在 `benchmark_cumulative` 之后）

**验证:** drawdown_series 长度应与 cumulative_returns 一致，所有值 <= 0

---

## Task 2: 后端 — 计算 monthly_grid

**文件:** `financial_analyzer/web/routes/backtest_api.py`
**函数:** `_serialize_result`
**位置:** 在 drawdown_series 之后

**逻辑:**
```python
monthly_grid = {}
monthly_rets = metrics_dict.get("monthly_returns", []) if metrics_dict else []
if monthly_rets and snapshots_list:
    for i, ret in enumerate(monthly_rets):
        safe_ret = _safe_json_value(ret)
        if safe_ret is None:
            safe_ret = 0.0
        snap_idx = i + 1
        if snap_idx < len(snapshots_list):
            dt_str = snapshots_list[snap_idx]["date"]
        elif snapshots_list:
            dt_str = snapshots_list[-1]["date"]
        else:
            continue
        year = dt_str[:4]
        month = int(dt_str[4:6])
        if year not in monthly_grid:
            monthly_grid[year] = {}
        monthly_grid[year][str(month)] = round(safe_ret, 6)
```

**返回值:** 新增 `"monthly_grid": monthly_grid` 到返回 dict

**数据格式:** `{"2024": {"1": 0.021, "2": -0.015, ...}, "2025": {...}}`

**验证:** monthly_grid 总条目数应等于 len(monthly_returns)

---

## Task 3: 前端 — 累计收益曲线渲染函数

**文件:** `frontend/js/quant.js`
**函数:** 新增 `renderCumulativeChart(cumulative, benchmarkCum, startDate, endDate)`
**位置:** 在 `renderMonthlyBars` 函数之后

**逻辑:**
1. 获取目标容器 `#chart-cumulative-container`，创建 canvas 元素
2. 生成 X 轴日期标签（从 startDate 到 endDate，逐月）
3. 将 cumulative_returns（百分比形式）转换为净值形式（1 + r）
4. 使用 `new Chart(canvas, { type: 'line', ... })` 渲染
5. 双线数据集：策略（绿色 #4caf50）+ 基准（灰色 #90a4ae）
6. Y 轴 tick callback 显示百分比格式
7. Tooltip 显示日期和对应收益率

**Chart.js 配置要点:**
- `responsive: true, maintainAspectRatio: false`
- 图表容器高度: 280px
- 网格线颜色: `rgba(255,255,255,0.08)`
- 填充: `fill: false`
- `tension: 0.3` 使曲线平滑
- `pointRadius: 0` 减少数据点噪音（hover 时显示）

---

## Task 4: 前端 — 回撤曲线渲染函数

**文件:** `frontend/js/quant.js`
**函数:** 新增 `renderDrawdownChart(drawdownSeries, startDate, endDate)`
**位置:** 在 `renderCumulativeChart` 之后

**逻辑:**
1. 在目标容器 `#chart-drawdown-container` 中创建 canvas 元素
2. 生成 X 轴日期标签（同累计收益曲线）
3. 使用 `new Chart(canvas, { type: 'line', ... })` 渲染
4. 单线数据集，红色 #f44336，填充 `backgroundColor: rgba(244, 67, 54, 0.3)`
5. Y 轴 tick callback 显示百分比格式（负数）
6. `fill: true` 填充曲线下方区域

**Chart.js 配置要点:**
- 容器高度: 240px
- `pointRadius: 0` 减少视觉噪音
- Tooltip 显示日期和回撤百分比

---

## Task 5: 前端 — 月度收益热力图渲染函数

**文件:** `frontend/js/quant.js`
**函数:** 新增 `renderMonthlyHeatmap(monthlyGrid)`
**位置:** 在 `renderDrawdownChart` 之后

**逻辑:**
1. 在目标容器 `#heatmap-container` 中构建 HTML table
2. thead: `<th>年份</th><th>1月</th>...<th>12月</th>`
3. tbody: 每年一行，每个单元格显示月度收益率
4. 单元格背景色计算:
   - 找到全局最大绝对值 maxAbs
   - 正收益: `rgba(76, 175, 80, opacity)` — opacity = min(0.8, abs(ret)/maxAbs * 0.8 + 0.1)
   - 负收益: `rgba(244, 67, 54, opacity)` — 同上
   - 无数据: 背景色 `var(--surface-elevated)`
5. 单元格文字: 正值绿色，负值红色
6. title 属性显示精确收益率

---

## Task 6: 前端 — 更新 renderBacktestResults 布局

**文件:** `frontend/js/quant.js`
**函数:** `renderBacktestResults`（现有，约 line 921）

**变更:**
1. 在 metricsHTML + benchmarkHTML 之后，插入 chartsHTML 容器
2. chartsHTML 包含:
   - 全宽累计收益曲线容器
   - 两列布局（回撤曲线 + 热力图）
3. 最终拼接: summaryHTML + metricsHTML + benchmarkHTML + chartsHTML + tradesHTML + attrHTML
4. 在 `innerHTML` 设置之后，用 `setTimeout(fn, 0)` 确保 DOM 已更新
5. 调用三个渲染函数:
   - `renderCumulativeChart(data.cumulative_returns, data.benchmark_cumulative, data.start_date, data.end_date)`
   - `renderDrawdownChart(data.drawdown_series, data.start_date, data.end_date)`
   - `renderMonthlyHeatmap(data.monthly_grid)`

**chartsHTML 结构:**
```html
<div class="backtest-charts-row">
  <div class="backtest-chart-full" id="chart-cumulative-container"></div>
</div>
<div class="backtest-charts-grid">
  <div class="backtest-chart-half" id="chart-drawdown-container"></div>
  <div class="backtest-chart-half" id="heatmap-container"></div>
</div>
```

---

## Task 7: 前端 — CSS 样式

**文件:** `frontend/css/quant.css`
**位置:** 在 `.backtest-metrics` 相关样式之后（约 line 358）

**新增样式块:**

1. `.backtest-charts-row` — 全宽图表行，margin-bottom: 20px
2. `.backtest-charts-grid` — 两列 grid 布局，gap: 20px，margin-bottom: 20px
3. `.backtest-chart-full` — 全宽图表容器，surface 背景，圆角边框 12px，padding 20px，height 320px，position relative
4. `.backtest-chart-half` — 半宽图表容器，surface 背景，圆角边框 12px，padding 16px，min-height 280px
5. `.heatmap-table` — 热力图表格，width 100%，border-collapse collapse，font-size 0.8rem，font-family var(--font-mono)
6. `.heatmap-table th` — 表头样式，padding 6px 4px，font-size 0.75rem，color var(--text-secondary)，text-align center
7. `.heatmap-table td` — 单元格样式，padding 8px 4px，text-align center，border-radius 4px，hover transform scale(1.05)
8. 响应式: @media (max-width: 900px) `.backtest-charts-grid` grid-template-columns: 1fr
9. 响应式: @media (max-width: 600px) 容器高度缩小

---

## 执行顺序与依赖

```text
Task 7 (CSS) ───────────── 独立，可在任意时刻完成
Task 1 (后端 drawdown) ──┐
                          ├── Task 6 (前端布局 + 调用渲染)
Task 2 (后端 grid) ──────┘
Task 3 (前端累计收益) ───┐
Task 4 (前端回撤) ───────┤── Task 6 依赖这三个函数存在
Task 5 (前端热力图) ─────┘
```

**推荐执行顺序:**
1. Task 7 (CSS) — 独立，无依赖
2. Task 1 + Task 2 (后端) — 可并行
3. Task 3 + Task 4 + Task 5 (前端渲染函数) — 可并行
4. Task 6 (前端布局整合) — 依赖 Task 1-5 全部完成

---

## 测试要点

- 回测空数据时（无 snapshots/metrics），三个图表应优雅降级（不渲染，不报错）
- 仅 1-2 个月数据时，图表应正常渲染（无崩溃）
- Chart.js canvas 在 tab 切换后重绘（view:changed 事件）
- 热力图 NaN/None 值处理（灰色空单元格）
- 移动端响应式布局（900px 以下单列）
- drawdown_series 全为 0 时（无回撤），曲线应为平坦零线
