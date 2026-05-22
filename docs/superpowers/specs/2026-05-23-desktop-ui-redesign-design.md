# 桌面 GUI 全量重构设计文档

## 概述

将现有 Tkinter 桌面 GUI 替换为基于 Web 技术的 Modern Dark SaaS 风格界面，通过 pywebview 打包为桌面应用。后端 API、分析引擎、数据层全部保持不变，仅重构前端 UI 层。

### 设计目标

- 视觉效果达到并超越现有 Web 界面水平
- 保留全部 40+ 分析模块功能完整性
- 仪表盘优先的信息架构，打开即见数据
- 三种功能访问路径覆盖新手到专家用户

---

## 1. 系统架构

### 1.1 分层架构

```
┌──────────────────────────────────────────────┐
│ Desktop Shell (NEW)                          │
│ pywebview 窗口 · 1200×800 · 系统托盘 · 单实例 │
├──────────────────────────────────────────────┤
│ Frontend SPA (NEW)                           │
│ HTML/CSS/JS · Hash 路由 · Chart.js           │
├──────────────────────────────────────────────┤
│ FastAPI 服务层 (KEEP)                         │
│ REST API · WebSocket · 静态文件               │
├──────────────────────────────────────────────┤
│ 分析引擎层 (KEEP)                             │
│ Analyzers · Pipeline · AI Orchestrator        │
├──────────────────────────────────────────────┤
│ 数据层 (KEEP)                                 │
│ TushareAdapter · CacheManager · Normalizer    │
└──────────────────────────────────────────────┘
```

### 1.2 改动范围

**新建：**
- `frontend/index.html` — SPA 入口
- `frontend/css/` — 8 个 CSS 模块（tokens, base, layout, dashboard, analysis, chat, data, overlays）
- `frontend/js/` — 10 个 JS 模块（app, router, api, dashboard, analysis, chat, data-browser, command-palette, settings, utils）
- `desktop_app.py` — pywebview 启动器

**复用不变：**
- `financial_analyzer/` 下全部后端代码
- `web/routes/` 全部 API 路由
- `web/services/` 全部服务层
- `ai/` AI 编排引擎

**废弃：**
- `ui/` 整个 Tkinter UI 层（app.py, theme.py, dialogs.py 等）
- `web/templates/` 旧 Jinja2 模板
- `web/static/` 旧 CSS/JS

### 1.3 技术选型

纯 HTML/CSS/JS，零构建工具，零 Node 依赖。仅引入三个轻量 CDN 库：
- Chart.js — 图表渲染
- SortableJS — 仪表盘卡片拖拽排序
- marked.js — Markdown 渲染

### 1.4 运行方式

```bash
# 方式一：分别启动
python run_web.py                    # 启动 FastAPI (http://127.0.0.1:8000)
python desktop_app.py                # pywebview 加载前端

# 方式二：一键启动
python desktop_app.py --serve        # 自动启动 FastAPI + 桌面窗口
```

---

## 2. 页面结构与路由

### 2.1 Hash 路由表

| 路由 | 页面 | 核心内容 |
|------|------|----------|
| `#/dashboard` | 仪表盘（默认） | 初始态：搜索入口 + 历史记录；数据态：KPI条 + K线图 + AI快评 |
| `#/analysis` | 分析中心 | 左列9分类标签 + 右列模块卡片网格 + 搜索过滤 |
| `#/analysis/:module` | 分析结果详情 | 面包屑 + Markdown报告 + 图表 + 推荐链 + 导出 |
| `#/ai` | AI 投研工作台 | 三子标签：自由对话/模板分析/三方辩论 |
| `#/data` | 数据浏览 | 数据类型选择 + 可排序筛选表格 + 分页 |
| `#/settings` | 设置 | Token管理/数据源切换/缓存设置/主题/关于 |

### 2.2 全局覆盖层（非路由）

- **Ctrl+K 命令面板** — 模态浮层，模糊搜索全部40+模块 + AI模板，回车直达
- **AI 侧边面板** — 右侧滑出，任意页面 Ctrl+Space 触发，上下文感知
- **导出/设置弹窗** — 模态对话框，不占用路由

### 2.3 页面切换流程

```
打开应用 → #/dashboard (初始态，搜索框自动聚焦)
输入600519 → #/dashboard (数据态，KPI+图表加载)
点击「分析中心」→ #/analysis (分类浏览)
点击「杜邦分析」→ #/analysis/dupont (报告+瀑布图+推荐)
Ctrl+K "估值" → #/analysis/pe_valuation
Ctrl+Space → AI侧边面板（带上杜邦分析上下文）
```

---

## 3. 导航系统

### 3.1 顶部导航栏（始终可见）

- Logo + 4个主标签（仪表盘/分析中心/AI投研/数据浏览）
- 居中股票搜索栏（支持代码/名称模糊搜索）
- 快捷键提示 + 设置入口
- 当前页面标签高亮 + 靛蓝底部指示线

### 3.2 分析中心（#/analysis）

**布局：** 左侧垂直分类列表 + 右侧模块卡片网格（3列）+ 顶部搜索过滤

**9大分类：**

| # | 分类 | 模块数 | 内容 |
|---|------|--------|------|
| 01 | 市场行情 | 3 | 行情概览、价格趋势(MA)、技术指标(RSI/MACD/布林带) |
| 02 | 财务报表 | 3 | 资产负债表(7节)、利润表(6节)、现金流量表(6节) |
| 03 | 能力分析 | 5 | 盈利能力、营运能力、偿债能力、成长能力、财务比率(20+指标) |
| 04 | 深度分析 | 9 | 杜邦、ROIC、Z-Score、F-Score、M-Score、自由现金流(DCF)、现金流象限、护城河、深度综合 |
| 05 | 估值分析 | 7 | PE估值、PE历史分位、PB-ROE、EV/EBITDA、综合投资评级(7维)、财报质量、股东回报 |
| 06 | 财务审计 | 6 | 全面审计(32信号)、资产端、利润端、现金流、勾稽验证、ML舞弊检测 |
| 07 | 股东与资金 | 4 | 股东结构、资金流向(主力/融资融券/北向)、分红分析、行业对比 |
| 08 | 风险与综合 | 4 | 风险评估、量价结合、趋势评分、周度PE分位 |
| 09 | Tushare数据 | 3 | 审计意见、财务指标原始表、主营业务构成 |

每张模块卡片显示：名称、简介、输出类型标签（文字/图表）、上次运行时间。

### 3.3 Ctrl+K 命令面板

- 全局快捷键，任意页面触发
- 模态浮层，居中显示
- 输入即搜，模糊匹配所有模块名称 + 分类路径 + AI模板
- 键盘上下导航，回车直达
- Esc 关闭

### 3.4 分析结果页（#/analysis/:module）

- 顶部面包屑导航 + 股票信息
- 主区域：Markdown 渲染的分析报告（支持表格、代码块、层级标题）
- 图表型模块：侧边渲染 Chart.js 图表（瀑布图/雷达图/柱状图/K线图）
- 底部操作栏：复制报告 / 导出（Excel/CSV/JSON）/ 推荐相关模块
- 每个二级标题旁自动生成复制按钮

---

## 4. 仪表盘设计

### 4.1 双状态设计

**初始态（无股票）：**
- 居中大搜索框，自动聚焦
- 右侧面板：最近查看的股票（一键切换）+ 快捷模板入口
- AI 投研和数据分析按钮灰显或隐藏

**数据态（有股票）：**
- KPI 条：5 卡片横排（最新价、PE、总市值、ROE、综合评分）
- 左侧 2/3：交互式 K 线图（支持日/周/月切换）+ 最近分析记录
- 右侧 1/3：AI 快评摘要 + "开始 AI 分析" CTA 按钮
- 动态卡片系统：可拖拽排序、展开/折叠、添加移除
- 布局偏好持久化到 localStorage

### 4.2 KPI 卡片交互

- 每张卡片：指标名 + 数值 + 涨跌标签 + 行业对比
- 点击卡片展开迷你趋势图（sparkline）
- 涨跌颜色：涨 #10B981 / 跌 #EF4444

---

## 5. AI 投研集成

### 5.1 全页模式（#/ai）

**三个子标签：**

| 标签 | 功能 | 交互 |
|------|------|------|
| 自由对话 | 开放式问答，带轻量数据摘要 | 消息气泡 + 流式输出 + Markdown渲染 |
| 模板分析 | 6 预置模板驱动深度分析 | 模板卡片选择 → 自动加载数据 → 分段流式展示 |
| 三方辩论 | 价值/成长/风控三视角辩论 | 三列并排实时流式 + 底部共识栏 |

**6 个 AI 模板：**
1. 盈利能力深度解读（income, financial）
2. 财务异常信号排查（balance, income, cashflow）
3. 估值合理性判断（daily_basic, financial）
4. 股东结构评估（top10_holders, stk_holdernumber）
5. 资金面多空分析（moneyflow, margin）
6. 成长质量检查（income, cashflow, financial）

**页面布局：**
- 左侧 2/3：对话区（消息气泡 + 流式光标）
- 右侧 1/3：上下文面板（股票摘要 + 数据就绪状态 + 异常信号 + 分析历史）

### 5.2 侧边面板模式

- 快捷键：Ctrl+Space
- 右侧滑出，宽度 ~360px
- 半透明遮罩，不遮挡主内容滚动
- 自动带入当前页面分析结果作为 AI 上下文
- 对话历史独立保留

### 5.3 WebSocket 协议

**客户端 → 服务端：**
```json
{"type": "chat", "message": "..."}
{"type": "template", "template_id": "profitability"}
{"type": "debate", "topic": "..."}
```

**服务端 → 客户端（流式事件）：**
```json
{"event": "token", "data": "..."}          // 逐字流式
{"event": "section", "title": "...", "index": 1}  // 模板分段
{"event": "debate_round", "round": 1, "analyst": "value"}  // 辩论轮次
{"event": "done"}                          // 完成
```

---

## 6. 视觉设计系统

### 6.1 设计方向

**调性：** 专业权威但不冰冷 · 现代精致但不高冷 · 数据密集但不压抑
**记忆点：** 靛蓝(#6C5CE7)替代传统蓝色 · 玻璃卡片悬浮在微噪点背景上 · 大胆使用负空间
**参考：** Vercel · Stripe · Linear

### 6.2 色彩系统

| Token | 色值 | 用途 |
|-------|------|------|
| --color-surface | #06080F | 页面底色 |
| --color-surface-elevated | #0C0E18 | 卡片背景 |
| --color-surface-glass | rgba(255,255,255,0.03) | 玻璃面板 |
| --color-border | #1A1D2E | 默认边框 |
| --color-border-accent | rgba(108,92,231,0.3) | 靛蓝边框 |
| --color-accent | #6C5CE7 | 主色调 |
| --color-accent-soft | rgba(108,92,231,0.12) | 主色背景 |
| --color-success | #10B981 | 上涨/利好 |
| --color-danger | #EF4444 | 下跌/风险 |
| --color-warning | #F59E0B | 预警/注意 |
| --color-text-primary | #F1F5F9 | 主文本 |
| --color-text-secondary | #94A3B8 | 次要文本 |
| --color-text-muted | #64748B | 辅助文本 |
| --color-text-disabled | #334155 | 禁用文本 |

### 6.3 排版系统

| 角色 | 字体 | 用途 |
|------|------|------|
| Display/Heading | Satoshi Bold | h1-h3 标题、导航标签、KPI 数值 |
| Body/UI | Geist Sans | 正文、标签、按钮、表单 |
| Mono/Data | JetBrains Mono | 代码、财务数据、表格 |

中文字体回退：Microsoft YaHei UI (Win) → PingFang SC (Mac) → Noto Sans SC (Linux)

| 层级 | 字号/行高 | 用途 |
|------|-----------|------|
| Heading XL | 26/34 | 页面主标题 |
| Heading L | 20/28 | 区块标题 |
| Heading M | 16/24 | 卡片标题 |
| Heading S | 13/20 | 小节标题 |
| Body | 13/22 | 正文段落、分析报告 |
| Small | 11/16 | 辅助信息、标签、时间戳 |
| Caption | 10/14 | 图表标注、脚注、快捷键 |

### 6.4 间距与圆角

**间距：** 4px 为基数 — 4/8/12/16/20/24/32/48
**圆角：** sm 4px / md 8px / lg 12px / xl 16px

### 6.5 效果与氛围

- **玻璃面板：** background rgba + backdrop-filter blur(12px) + 半透明边框
- **渐变强调：** linear-gradient(135deg, #6C5CE7, #A78BFA) 用于 Logo、CTA、选中态
- **微噪点纹理：** body::before 层叠 <0.02 不透明度的 SVG 噪点纹理
- **过渡动画：** 150-250ms ease-out，使用 transform/opacity 避免重排
- **聚焦环：** 2px 靛蓝外发光，不偏移

### 6.6 组件状态

| 组件 | 默认 | 悬停/聚焦 | 激活/选中 | 禁用 | 错误 |
|------|------|-----------|-----------|------|------|
| 按钮 | 靛蓝底/幽灵/危险 | 亮度+8% | 缩放0.98 | 透明度0.4 | - |
| 输入框 | 暗色底+浅边框 | 靛蓝边框 | - | 透明度0.4 | 红底+红边框 |
| 卡片 | 玻璃面+微边框 | 靛蓝边框+微提亮 | 靛蓝底+全边框 | - | - |
| 标签 | 语义色10%底 | - | - | - | - |

---

## 7. 前端文件结构

```
frontend/
├── index.html                  // SPA 入口，包含所有视图容器
├── css/
│   ├── tokens.css              // CSS 变量（颜色/字体/间距/圆角/阴影）
│   ├── base.css                // 重置 + 排版 + 基础组件
│   ├── layout.css              // 顶部导航 + 页面布局 + 响应式
│   ├── dashboard.css           // 仪表盘：KPI卡片、图表、AI快评
│   ├── analysis.css            // 分析中心：分类标签、模块网格、结果页
│   ├── chat.css                // AI 对话：消息气泡、流式输出、辩论三列
│   ├── data.css                // 数据表格：排序、筛选、分页
│   └── overlays.css            // 命令面板、AI侧边面板、弹窗
└── js/
    ├── app.js                  // 入口：路由初始化、全局状态、事件绑定
    ├── router.js               // Hash 路由：匹配规则、视图切换、浏览器前进后退
    ├── api.js                  // API 封装：fetch 请求、WebSocket 连接管理
    ├── dashboard.js            // 仪表盘：搜索、KPI加载、图表渲染、AI快评轮询
    ├── analysis.js             // 分析中心：分类切换、模块列表、结果渲染
    ├── chat.js                 // AI 对话：模板选择、WebSocket流式、Markdown渲染、辩论
    ├── data-browser.js         // 数据浏览：表格渲染、排序、筛选、分页、导出
    ├── command-palette.js      // 命令面板：模糊搜索、键盘导航、模块索引
    ├── settings.js             // 设置：Token/数据源/缓存管理
    └── utils.js                // 工具函数：日期格式化、数字格式化、Markdown渲染
```

---

## 8. 关键交互细节

### 8.1 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+K | 打开命令面板 |
| Ctrl+Space | 打开/关闭 AI 侧边面板 |
| Enter (搜索框) | 加载股票数据 |
| Esc | 关闭弹窗/面板/命令面板 |
| ↑↓ (命令面板) | 导航搜索结果 |

### 8.2 加载与空状态

- **仪表盘初始态：** 搜索框居中 + 历史记录 + 快捷模板
- **分析中心无股票：** 模块卡片正常显示，点击提示"请先输入股票代码"
- **数据加载中：** 骨架屏（skeleton shimmer），300ms 内不显示
- **分析执行中：** 进度指示器 + 状态文字
- **空数据：** "暂无数据" 引导提示 + 建议操作

### 8.3 响应式适应

- pywebview 默认窗口 1200×800，最小 960×600
- KPI 卡片自动缩窄/换行
- 模块网格在小窗口变为 2 列
- AI 侧边面板在小窗口变为全宽覆盖

### 8.4 启动体验

- 自动恢复上次查看的股票
- 自动恢复仪表盘卡片布局
- API 连接状态指示（顶部绿色圆点）
- 离线时显示断连提示

---

## 9. 实施策略

### 9.1 实施顺序

1. **CSS 设计系统** — tokens.css + base.css + layout.css，建立视觉基础
2. **SPA 框架** — index.html + router.js + app.js，路由和视图容器
3. **顶栏导航 + 布局壳** — 全局框架搭建
4. **仪表盘** — 初始态 + 数据态 + K线图 + AI快评
5. **分析中心** — 分类标签 + 模块网格 + 结果页
6. **AI 投研** — 全页模式 + 侧边面板 + 模板分析 + 辩论
7. **命令面板 + 快捷键** — Ctrl+K 搜索
8. **数据浏览 + 设置** — 表格 + 配置管理
9. **pywebview 集成** — desktop_app.py + 启动流程
10. **清理废弃代码** — 移除 ui/ + 旧 web/templates/ + 旧 web/static/

### 9.2 风险与应对

| 风险 | 应对 |
|------|------|
| pywebview 兼容性 | 测试 Windows/Mac 两端；备选 CEF/python-cef |
| Chart.js 性能 | 大数据集降采样；图表懒加载 |
| WebSocket 断连 | 自动重连 + 指数退避 + 状态提示 |
| 中文字体渲染 | 指定多个回退字体 + 测试各平台效果 |

---

## 10. 不包含的内容

- 后端 API 改动（全部复用现有路由）
- 移动端/响应式 Web（桌面专用）
- 多语言/国际化
- 暗色/亮色主题切换（仅暗色模式）
- Tkinter UI 维护（全部废弃）
