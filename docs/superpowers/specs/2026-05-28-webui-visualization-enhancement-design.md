# WebUI 可视化增强设计文档

## 背景

当前 WebUI（浏览器访问的 FastAPI 应用）的图表系统存在以下问题：
- 图表库不统一（Plotly 用于 K 线/均线，Matplotlib 生成静态 PNG）
- 量化模块无可交互图表（仅 HTML/CSS 柱状图）
- 分析模块图表类型单一（大多为通用柱状图）
- 缺乏交互功能（缩放、悬停、钻取）

## 目标

1. 停用桌面 GUI 的 SPA 前端，隔离相关文件
2. 引入 ECharts 作为统一图表库（保留现有 K 线/均线 Plotly 图表）
3. 量化模块添加 4 个专业图表
4. 分析模块添加 3 个专用图表
5. 为所有图表添加统一交互功能

## 设计方案

### 1. SPA 前端停用与隔离

**操作：**
- 将 `frontend/` 目录移动到 `_disabled/frontend_archive/`
- 在原位置留 `frontend/README.md` 说明文件已归档
- 更新 `.gitignore` 忽略 `_disabled/` 目录

**保留不动：**
- `financial_analyzer/web/` — WebUI 完整保留
- `desktop_app.py` — 桌面入口保留（但前端已归档）
- `web_app.py` — Web 入口保留

### 2. ECharts 引入与基础设施

**引入 ECharts：**
- 在 `financial_analyzer/web/templates/base.html` 添加 ECharts 5.5.0 CDN
- 保留现有 Plotly.js（K 线图和均线图继续用 Plotly）

**新建工具模块：**
- `financial_analyzer/web/static/js/echarts-utils.js` — 统一图表工具
  - 主题配置（深色商务风格）
  - 初始化函数（自动适配容器）
  - 通用配置项（tooltip、legend、grid）
  - 响应式处理（窗口 resize）
  - 销毁函数（避免内存泄漏）

**后端 API 调整：**
- 新增 `/api/v1/chart/echarts/{type}` 端点返回 ECharts 格式数据
- 保留现有 `/chart/candlestick` 和 `/chart/ma`（Plotly 格式）

**目录结构：**
```
financial_analyzer/web/
├── static/
│   ├── js/
│   │   ├── echarts-utils.js    ← 新增
│   │   └── app.js              ← 修改
│   └── css/
│       └── charts.css          ← 新增
└── routes/
    └── charts_api.py           ← 修改
```

### 3. 量化模块图表增强

**新增 4 个图表：**

| 图表 | 类型 | 数据源 | 说明 |
|------|------|--------|------|
| 累计收益曲线 | 折线图 | `snapshots[].date` + `snapshots[].total_value` | 策略 vs 基准双线对比 |
| 回撤曲线 | 面积图 | 从 `snapshots` 计算 | 标注最大回撤点 |
| 月度收益热力图 | 热力图 | `metrics.monthly_returns` | 年×月，颜色表示收益 |
| 因子归因图 | 水平柱状图 | `attribution` | 正负贡献分左右 |

**API 变更：** 无（现有返回数据已包含所需字段）

**文件变更：**
- `frontend/js/quant.js` — 新增 4 个图表渲染函数
- `frontend/css/quant.css` — 新增图表容器样式
- `financial_analyzer/web/static/js/echarts-utils.js` — 新增量化图表配置

### 4. 分析模块图表增强

**新增 3 个图表：**

| 图表 | 类型 | 数据源 | 说明 |
|------|------|--------|------|
| 杜邦分析瀑布图 | 瀑布图 | 分析结果中的杜邦因子 | ROE 分解路径 |
| 估值仪表盘 | 仪表盘 | PE/PB/PS 百分位 | 半圆形，三色区间 |
| 技术指标多面板 | 联动图表 | 日线数据 | 价格+MA、成交量、MACD、RSI |

**API 变更：**
- `/api/v1/analyze/{moduleKey}` — 返回结构化图表数据（当前返回 markdown 文本）

**文件变更：**
- `financial_analyzer/web/static/js/app.js` — 新增 3 个图表渲染函数
- `financial_analyzer/web/static/css/charts.css` — 新增图表容器样式
- `financial_analyzer/web/routes/analysis_api.py` — 修改返回格式
- `financial_analyzer/analyzers/*.py` — 提取结构化数据

### 5. 交互性提升

**新增 4 个交互功能：**

| 功能 | 说明 | 实现方式 |
|------|------|----------|
| 缩放与平移 | 滚轮缩放、拖拽平移、框选放大 | ECharts dataZoom 组件 |
| 悬停提示增强 | 十字准线、多指标联动显示 | ECharts tooltip + axisPointer |
| 数据钻取 | 点击显示详情弹窗 | 自定义 click 事件 + 弹窗 |
| 图表联动 | 多图表 X 轴同步 | ECharts connect 组件 |

**实现工具：**
```javascript
// echarts-utils.js 中新增
const InteractionUtils = {
  crosshair(chart, charts) { ... },
  drillDown(chart, data) { ... },
  linkCharts(charts) { ... }
};
```

**文件变更：**
- `financial_analyzer/web/static/js/echarts-utils.js` — 新增交互工具
- `financial_analyzer/web/static/css/charts.css` — 新增弹窗、准线样式
- 所有图表渲染文件 — 调用交互工具

## 实施计划

采用渐进式迁移（方案 A），分 4 轮循环：

| 循环 | 聚焦内容 | 产出 |
|------|----------|------|
| 1 | 停用 SPA + 引入 ECharts + 修复基础问题 | 统一图表基础设施 |
| 2 | 量化模块图表增强 | 累计收益、回撤、热力图、因子归因 |
| 3 | 分析模块图表增强 | 瀑布图、仪表盘、多面板技术指标 |
| 4 | 交互性提升 | 缩放、悬停、钻取、动画 |

## 保留不变

- K 线图（Plotly）— 效果好，不改动
- 均线图（Plotly）— 效果好，不改动
- 桌面 GUI 入口（`desktop_app.py`）— 保留但前端已归档

## 验收标准

1. 所有图表使用 ECharts 渲染（K 线/均线除外）
2. 量化模块展示 4 个新图表
3. 分析模块展示 3 个新图表
4. 所有图表支持缩放、悬停提示
5. 图表联动正常工作
6. 无 JavaScript 控制台错误
7. 响应式布局适配不同屏幕尺寸
