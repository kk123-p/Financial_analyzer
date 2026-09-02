# Cycle 3 — 分析模块图表增强实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将分析模块的三个核心图表（杜邦瀑布图、估值仪表盘、技术指标多面板）从 matplotlib PNG 迁移到 ECharts JSON，实现前端交互式渲染，提升用户体验和性能。

**关键约束:**
- ECharts 5.5.1 已通过 CDN 加载（base.html line 14）
- EchartsUtils 工具库已存在（echarts-utils.js），提供 init/setOption/resize/dispose
- 前端保持 Vanilla JS 架构，新文件 analysis-charts.js 遵循 quant-charts.js 的 IIFE 模式
- 后端数据依赖 ReportBuilder.build()，需确保 session 中有 data
- 与现有 matplotlib 按钮共存（不删除旧按钮，新增 ECharts 版本按钮）

---

## 现状分析

### 已有基础设施
- charts_api.py: 已有 /chart/candlestick, /chart/ma, /chart/bar（ECharts JSON）+ /chart/img/{type}（matplotlib PNG）
- app.js: loadChart(type) 获取 ECharts JSON 并渲染到 #chart-container；loadChartImg(type) 获取 PNG blob
- echarts-utils.js: EchartsUtils.init(domId), .setOption(chart, option), .resize(domId), .dispose(domId)
- quant-charts.js: IIFE 模式，暴露 QuantCharts 全局对象，提供 renderEquityCurve 等函数
- charts.css: .chart-container (500px height), .chart-controls (flex), .chart-type-btn (pill buttons)

### 数据可用性
- 杜邦数据: ReportBuilder.build()["dupont_analysis"]["three_factor"] — 含 end_date, roe, net_margin, asset_turnover, equity_multiplier（最多3年）
- 估值数据: ReportBuilder.build()["valuation"] — 含 pe_percentile (current/percentile/avg/min/max) 和 pb_percentile (current/percentile/avg)。无 PS 数据。
- 技术指标: 需从 session daily DataFrame 计算 MACD/RSI/KDJ，数据量取决于 days 参数
- 风险模型: ReportBuilder.build()["risk_models"] — 含 fscore (score/max/details), zscore (z_score/zone/components), mscore

### 容器冲突
当前只有一个 #chart-container。方案：复用现有容器，新旧按钮共用同一容器，通过按钮 active 状态互斥切换。

---

## 布局设计

    图表 Tab（tab-charts）:
    +----------------------------------------------------------+
    | [K线图] [均线图] [涨跌柱] | [杜邦瀑布] [估值仪表] [技术面板] |
    +----------------------------------------------------------+
    |  #chart-container  （ECharts 动态渲染区）                  |
    +----------------------------------------------------------+

---
## Task 1: 后端 — 杜邦瀑布图 ECharts 端点

**文件:** financial_analyzer/web/routes/charts_api.py
**新增路由:** GET /chart/dupont_waterfall

**逻辑:**
1. 从 _get_session(request) 获取 session
2. 获取 session["data"] 和 session["stock_code"]
3. 调用 ReportBuilder.build(data, stock_code) 获取 report
4. 从 report["dupont_analysis"]["three_factor"] 提取最近两期数据
5. 使用连环替代法计算净利率贡献、周转率贡献、杠杆贡献
6. 构建 ECharts waterfall bar chart option JSON：
   - 类型: bar + stack，使用透明隐形 bar 作为瀑布图底部支撑
   - 5 个柱子: ROE(期初) -> 净利率贡献 -> 周转率贡献 -> 杠杆贡献 -> ROE(期末)
   - 颜色: 期初/期末用金色 #D29922，正贡献用 #3FB950，负贡献用 #F85149
   - 标注: 每个柱子上方显示数值（贡献值用 +/-pp，ROE 用 %）
7. 返回 JSON Response

**数据不足时:** 若 three_factor 长度 < 2，返回 _empty_chart()

**验证:**
- 有杜邦数据时返回有效 ECharts option（含 series、xAxis、yAxis）
- 无数据时返回空图表（不报错）
- 连环替代法计算结果与 matplotlib 版本一致

---

## Task 2: 后端 — 估值仪表盘 ECharts 端点

**文件:** financial_analyzer/web/routes/charts_api.py
**新增路由:** GET /chart/valuation_dashboard

**逻辑:**
1. 从 session 获取 data 和 stock_code
2. 调用 ReportBuilder.build(data, stock_code) 获取 report
3. 从 report["valuation"] 提取 PE/PB 分位数据
4. 从 report["company_snapshot"] 提取当前 PE/PB 值
5. 构建 ECharts option，包含两个 gauge 图表：
   - 左 gauge: PE 历史分位（0-100%），指针指向当前百分位
   - 右 gauge: PB 历史分位（0-100%），指针指向当前百分位
   - 颜色区间: 0-30% 绿色（低估）、30-70% 黄色（合理）、70-100% 红色（高估）
   - 标题显示当前 PE/PB 绝对值
6. 返回 JSON Response

**数据不足时:** 若无 PE/PB 分位数据，返回 _empty_chart()

**验证:**
- PE/PB 分位数据正确映射到 gauge 指针位置
- 无数据时优雅降级
- 颜色区间与估值逻辑一致（低分位=低估=绿色）

---
## Task 3: 后端 — 技术指标多面板 ECharts 端点

**文件:** financial_analyzer/web/routes/charts_api.py
**新增路由:** GET /chart/tech_panel
**参数:** days: int = Query(120)

**逻辑:**
1. 从 session 获取 daily DataFrame（复用 _get_daily(session)）
2. 取最近 days 天数据
3. 计算三个技术指标：
   - MACD: EMA(12) - EMA(26) = DIF, DIF 的 EMA(9) = DEA, (DIF-DEA)*2 = MACD柱
   - RSI(14): 基于涨跌幅的 14 日相对强弱指标
   - KDJ(9,3,3): RSV = (C-L9)/(H9-L9)*100, K=SMA(RSV,3), D=SMA(K,3), J=3K-2D
4. 构建 ECharts 多面板 option：
   - 4 个 grid: 价格+均线(40%) / MACD(20%) / RSI(20%) / KDJ(20%)
   - 共享 xAxis（日期），使用 axisPointer.link 联动
   - 价格面板: 收盘价折线 + MA5/MA10/MA20
   - MACD 面板: DIF 线 + DEA 线 + MACD 柱（红绿）
   - RSI 面板: RSI 线 + 30/70 超买超卖线
   - KDJ 面板: K 线 + D 线 + J 线
   - dataZoom slider 底部控制
5. 返回 JSON Response

**性能优化:**
- 使用 _safe_float 批量转换，避免逐个 NaN 检查
- animation: False 减少渲染开销
- 限制 days 最大值为 500

**验证:**
- MACD/RSI/KDJ 计算结果正确
- 4 个面板联动（tooltip、dataZoom 同步）
- 大数据量（500天）下序列化时间 < 100ms

---

## Task 4: 前端 — 创建 analysis-charts.js

**文件:** financial_analyzer/web/static/js/analysis-charts.js（新建）
**模式:** 遵循 quant-charts.js 的 IIFE 模式

**结构（暴露全局对象 AnalysisCharts）:**
- renderDupontWaterfall(option) — 接收后端 ECharts option，渲染到容器
- renderValuationDashboard(option) — 渲染估值仪表盘（双 gauge）
- renderTechPanel(option) — 渲染技术指标多面板
- loadAnalysisChart(chartType, containerId) — 统一加载函数

**每个渲染函数:**
1. EchartsUtils.init(containerId) 初始化
2. EchartsUtils.setOption(chart, option) 设置配置
3. 空数据检查：若 !option.series || option.series.length === 0，显示暂无数据

**loadAnalysisChart:**
1. 显示加载状态
2. fetch /chart/ + chartType
3. 检查 response.ok 和 option.series
4. 根据 chartType 调用对应 render 函数
5. 错误处理：显示图表加载失败

**验证:**
- 三个渲染函数均能正确初始化 ECharts 并显示图表
- 空数据时不崩溃，显示友好提示
- resize 事件正确传播

---
## Task 5: 前端 — 修改 base.html 添加图表按钮

**文件:** financial_analyzer/web/templates/base.html
**位置:** tab-charts 内的 .chart-controls div（约 line 137-143）

**变更:**
1. 在现有 5 个按钮之后，添加分隔符和 3 个新按钮：
   - chart-divider span
   - 杜邦瀑布 (ECharts) -> loadAnalysisChart
   - 估值仪表 -> loadAnalysisChart
   - 技术面板 -> loadAnalysisChart

2. 旧的 loadChartImg 按钮文字改为杜邦(旧)和F-score(旧)

3. 在 script 标签区域添加 analysis-charts.js 的引用（在 quant-charts.js 之后，app.js 之前）

**验证:**
- 新按钮正确显示，与旧按钮视觉一致
- 点击新按钮触发 loadAnalysisChart 函数
- 旧按钮仍可正常工作（降级方案）

---

## Task 6: 前端 — 在 app.js 添加 loadAnalysisChart 函数

**文件:** financial_analyzer/web/static/js/app.js
**位置:** 在 loadChartImg 函数之后（约 line 200）

**新增函数:** loadAnalysisChart(chartType, btn)
- 按钮 active 状态切换（与 loadChart/loadChartImg 一致）
- 委托给 AnalysisCharts.loadAnalysisChart 执行实际加载
- 需要动态调整容器高度（技术面板需要更高容器）

**验证:**
- 点击杜邦瀑布按钮 -> fetch /chart/dupont_waterfall -> ECharts 渲染
- 点击估值仪表按钮 -> fetch /chart/valuation_dashboard -> ECharts 渲染
- 点击技术面板按钮 -> fetch /chart/tech_panel -> ECharts 渲染
- 按钮 active 状态正确切换

---

## Task 7: 前端 — CSS 样式增强

**文件:** financial_analyzer/web/static/css/charts.css

**新增样式:**
1. .chart-divider — 按钮组分隔符（color: rgba(48,54,61,0.6), padding: 0 4px）
2. .chart-container--tall — 技术面板用，min-height: 600px, height: 650px
3. .chart-container--gauge — 估值仪表用，min-height: 400px, height: 450px
4. @media (max-width: 900px) 响应式适配

**验证:**
- 分隔符在按钮组中正确显示
- 技术面板容器高度足够显示 4 个 grid
- 移动端布局正常

---
## 执行顺序与依赖

    Task 7 (CSS) ----------- 独立，可在任意时刻完成
    Task 1 (后端杜邦) ------+
    Task 2 (后端估值) ------+-- 独立，可并行
    Task 3 (后端技术面板) --+
    Task 4 (前端 analysis-charts.js) -- 依赖 Task 1-3 的 API 端点
    Task 5 (base.html 按钮) -- 依赖 Task 4 的函数存在
    Task 6 (app.js loadAnalysisChart) -- 依赖 Task 4

**推荐执行顺序:**
1. Task 7 (CSS) — 独立
2. Task 1 + Task 2 + Task 3 (后端三个端点) — 可并行
3. Task 4 (前端 analysis-charts.js) — 依赖后端端点
4. Task 5 + Task 6 (前端集成) — 依赖 Task 4

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 估值数据只有 PE/PB 百分位，无 PS | 估值仪表盘只能显示 2 个 gauge | 仅使用 PE/PB，不引入 PS；仪表盘设计为可扩展 |
| ReportBuilder.build() 计算开销 | 每次请求都重新计算 | 考虑在 session 中缓存 report 结果 |
| 技术图表数据量大 | JSON 序列化和传输慢 | 限制 days 最大 500；animation=False |
| 图表容器冲突 | 新旧图表互相覆盖 | 复用同一 #chart-container，按钮 active 状态互斥 |
| matplotlib 按钮共存 | 用户困惑 | 旧按钮文字加(旧)标记 |

---

## 测试要点

- 无 session data 时（未获取数据），点击新按钮应显示暂无数据
- 杜邦数据不足 2 期时，瀑布图降级为空图表
- 估值数据为空时，仪表盘降级为空图表
- 技术面板 500 天数据渲染流畅（< 2s）
- 4 个面板的 tooltip/dataZoom 联动正常
- 按钮 active 状态正确切换
- resize 窗口后图表自动适应
- 移动端（< 900px）布局正常
