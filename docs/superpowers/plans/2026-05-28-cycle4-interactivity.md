# Cycle 4 — 图表交互增强实施计划

**Goal:** 为 ECharts 图表添加交互能力 — 缩放控制、数据钻取弹窗、十字联动高亮、图表导出。

**设计规格:** 基于 cycle 3 已有的图表渲染基础设施。

**关键约束:**
- ECharts 已通过 CDN 加载为全局 `echarts`
- EchartsUtils 在 echarts-utils.js 中提供基础生命周期管理
- 保持 Vanilla JS SPA 架构

---

## Task 1: echarts-utils.js — 新增 InteractionUtils

**文件:** `financial_analyzer/web/static/js/echarts-utils.js`

在现有 `EchartsUtils` 对象之后，新增 `InteractionUtils` 模块：

1. `enableZoom(chart, opts)` — 为 ECharts 实例添加 dataZoom（slider + inside 拖拽缩放）
2. `enableDrillDown(chart, callback)` — 为 chart 添加 click 事件，调用 `showDrillDownModal(title, html)` 显示钻取弹窗
3. `showDrillDownModal(title, html)` — 打开 `#drilldown-overlay` 弹窗，设置标题和内容
4. `closeDrillDownModal()` — 关闭钻取弹窗
5. `addZoomControls(containerId, chart)` — 在容器顶部注入缩放按钮组（放大/缩小/重置）
6. `linkCharts(chartIdArray)` — 多图表 X 轴联动（一个图表 hover 时，其他图表同步显示 tooltip 和 axisPointer）
7. `exportChart(chart)` — 将当前 ECharts 实例导出为 PNG 并触发下载

---

## Task 2: charts.css — 新增钻取弹窗和缩放控件样式

**文件:** `financial_analyzer/web/static/css/charts.css`

新增样式块：
1. `.drilldown-overlay` — 全屏遮罩层，z-index 9999，背景 rgba(0,0,0,0.6)，居中 flex
2. `.drilldown-modal` — 弹窗主体，暗色主题，max-width 800px，max-height 80vh，可滚动
3. `.drilldown-header` — 弹窗头部，标题 + 关闭按钮
4. `.drilldown-body` — 弹窗内容区域
5. `.drilldown-close` — 关闭按钮样式
6. `.chart-zoom-controls` — 缩放按钮组，绝对定位在图表容器右上角
7. `.chart-zoom-btn` — 单个缩放按钮，圆形，暗色主题
8. `.chart-export-btn` — 导出按钮样式

---

## Task 3: base.html — 新增钻取弹窗 DOM 容器

**文件:** `financial_analyzer/web/templates/base.html`

在 `</body>` 之前插入钻取弹窗 DOM 结构：
```html
<div id="drilldown-overlay" class="drilldown-overlay" style="display:none;">
  <div class="drilldown-modal">
    <div class="drilldown-header">
      <h3 id="drilldown-title"></h3>
      <button class="drilldown-close" onclick="InteractionUtils.closeDrillDownModal()">&times;</button>
    </div>
    <div class="drilldown-body" id="drilldown-body"></div>
  </div>
</div>
```

---

## Task 4: quant-charts.js — 集成 InteractionUtils

**文件:** `financial_analyzer/web/static/js/quant-charts.js`

变更：
1. `renderEquityCurve` — 启用 dataZoom，添加缩放控件，启用图表导出
2. `renderDrawdownCurve` — 启用 dataZoom，添加缩放控件
3. `renderMonthlyHeatmap` — 启用钻取（点击热力图单元格显示该月详情弹窗）
4. `renderTradeDistribution` — 添加导出按钮
5. 新增 `linkAllCharts()` — 调用 InteractionUtils.linkCharts 联动 equity + drawdown

---

## Task 5: analysis-charts.js — 集成 InteractionUtils

**文件:** `financial_analyzer/web/static/js/analysis-charts.js`

变更：
1. `renderTechPanel` — 启用 dataZoom（时间序列图表最需要缩放），添加缩放控件
2. `renderDupontWaterfall` — 添加导出按钮
3. `renderValuationDashboard` — 添加导出按钮
4. `loadAnalysisChart` — 图表加载完成后自动添加交互控件

---

## 执行顺序

```text
Task 1 (InteractionUtils) ── 基础，所有后续任务依赖
Task 2 (CSS) ────────────── 独立，可与 Task 1 并行
Task 3 (DOM) ────────────── 独立，可与 Task 1 并行
Task 4 (quant-charts) ───── 依赖 Task 1-3
Task 5 (analysis-charts) ── 依赖 Task 1-3
```
