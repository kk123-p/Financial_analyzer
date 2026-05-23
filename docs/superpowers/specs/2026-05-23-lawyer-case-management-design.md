# 律师案件流程管理系统 — 设计文档

## 概述

独立的 Windows 桌面应用程序，用于律师管理诉讼案件和非诉项目的全流程。从纸质/Excel 管理模式迁移到数字化系统。

## 技术选型

| 层 | 技术 |
|---|------|
| 桌面壳 | Electron |
| 前端 UI | React + Tailwind CSS |
| 本地数据库 | SQLite (better-sqlite3) |
| IPC 通信 | contextBridge (安全暴露 API) |
| 提醒调度 | node-cron (主进程) |
| 系统通知 | Electron Notification API |
| 打包 | electron-builder |

## 系统架构

```
Electron Shell
  ├── 系统托盘 (托盘图标 + 右键菜单)
  ├── 本地通知 (截止日期提醒弹窗)
  └── 开机自启动 (可选)

React Frontend (Renderer Process)
  ├── 仪表盘  — 统计卡片 + 今日日程 + 最近动态
  ├── 案件列表 — 搜索/筛选/分组
  ├── 案件详情 — 垂直时间线 + 阶段管理
  ├── 日历视图 — 月历 + 右侧日程列表
  ├── 非诉项目 — 项目列表 + 任务管理
  ├── 模板管理 — 流程模板 CRUD
  ├── 文档管理 — 文件关联与打开
  └── 设置     — 提醒规则/通用配置

IPC Bridge (contextBridge)
  ├── db: cases/projects/templates 增删改查
  ├── file: 文件操作 (复制/打开)
  ├── notify: 系统通知触发
  └── export: PDF/Excel 导出

Main Process
  ├── 数据库服务 (better-sqlite3)
  ├── 提醒调度器 (node-cron, 定时扫描 reminders 表)
  └── 导出服务 (PDF 生成)
```

## 数据模型

### cases (诉讼案件)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| case_number | TEXT | 案号，如 (2025)京0105民初12345号 |
| title | TEXT NOT NULL | 案件名称 |
| case_type | TEXT | 民事/刑事/行政/执行 |
| court | TEXT | 受理法院 |
| judge | TEXT | 承办法官 |
| plaintiff | TEXT | 原告 |
| defendant | TEXT | 被告 |
| filing_date | TEXT | 收案日期 |
| closing_date | TEXT | 结案日期 (可为空) |
| status | TEXT | 进行中/已结案/已归档 |
| notes | TEXT | 备注 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### case_stages (案件阶段)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| case_id | INTEGER FK | 关联 cases.id |
| stage_name | TEXT NOT NULL | 阶段名称 |
| sort_order | INTEGER | 排序序号 |
| planned_start | TEXT | 计划开始日期 |
| planned_end | TEXT | 计划结束日期 |
| actual_start | TEXT | 实际开始日期 |
| actual_end | TEXT | 实际结束日期 |
| status | TEXT | 待开始/进行中/已完成/超期 |
| notes | TEXT | 阶段备注 |

默认诉讼模板 11 个阶段：委托谈判 → 签合同 → 立案 → 保全 → 庭前准备 → 收集证据 → 预判对方证据 → 开庭审理 → 庭后答复 → 调解判决 → 归档

### projects (非诉项目)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT NOT NULL | 项目名称 |
| project_type | TEXT | 法律顾问/合同审查/尽职调查/并购/其他 |
| client | TEXT | 客户名称 |
| status | TEXT | 进行中/已完成/已终止 |
| start_date | TEXT | 开始日期 |
| expected_end_date | TEXT | 预计结束日期 |
| actual_end_date | TEXT | 实际结束日期 |
| description | TEXT | 项目描述 |
| notes | TEXT | 备注 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### project_tasks (项目任务)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| project_id | INTEGER FK | 关联 projects.id |
| title | TEXT NOT NULL | 任务标题 |
| description | TEXT | 任务描述 |
| deadline | TEXT | 截止日期 |
| completed_at | TEXT | 完成时间 |
| priority | TEXT | 高/中/低 |
| status | TEXT | 待办/进行中/已完成 |
| sort_order | INTEGER | 排序序号 |

### templates (流程模板)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT NOT NULL | 模板名称 |
| category | TEXT | 诉讼/非诉 |
| case_type | TEXT | 适用案件类型 (诉讼) |
| project_type | TEXT | 适用项目类型 (非诉) |
| is_default | INTEGER | 是否默认模板 (0/1) |
| description | TEXT | 模板说明 |

### template_stages (模板阶段)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| template_id | INTEGER FK | 关联 templates.id |
| stage_name | TEXT NOT NULL | 阶段名称 |
| sort_order | INTEGER | 排序序号 |
| is_critical | INTEGER | 是否关键节点 (0/1，用于提醒) |

注意：模板仅定义阶段结构，不包含自动时间计算。所有时间由用户手动设定。

### documents (文档)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| case_id | INTEGER FK | 关联案件 (可为空) |
| project_id | INTEGER FK | 关联项目 (可为空) |
| name | TEXT NOT NULL | 文件名 |
| file_path | TEXT NOT NULL | 存储路径 |
| category | TEXT | 起诉状/证据材料/判决书/代理词/合同/法律意见书/其他 |
| file_size | INTEGER | 文件大小 (bytes) |
| file_type | TEXT | 文件扩展名 |
| upload_date | TEXT | 上传日期 |
| notes | TEXT | 备注 |

文件物理存储：`{userData}/case-files/{case_id}/` 目录下。

### reminders (提醒)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| target_type | TEXT | case_stage / project_task |
| target_id | INTEGER | 关联目标 ID |
| title | TEXT | 提醒标题 |
| remind_at | TEXT | 提醒时间 |
| is_dismissed | INTEGER | 是否已消除 (0/1) |
| created_at | TEXT | 创建时间 |

## UI 设计

### 整体布局
- 左侧固定侧边栏导航 (180px)，深色背景
- 导航项：仪表盘、案件列表、日历视图、非诉项目、模板管理、设置
- 右侧内容区自适应

### 仪表盘
- 4 个统计卡片 (进行中案件、临近截止、今日待办、本月归档)
- 今日日程列表
- 最近案件动态
- 快捷新建按钮

### 案件详情
- 左栏 (280px)：案件基本信息卡片 + 关联文档列表
- 右栏：垂直时间线展示案件阶段
  - 已完成：绿色圆点 + 打勾
  - 进行中：蓝色圆点 + 高亮
  - 超期：红色圆点
  - 待开始：灰色圆点

### 日历视图
- 左侧月历 (约 60% 宽度)：高亮标记截止日期
- 右侧日程列表 (约 40% 宽度)：选中日期的所有事件
- 颜色编码：红色=超期，黄色=临近，蓝色=今日/正常

### 非诉项目
- 项目列表页：表格/卡片视图
- 项目详情页：项目信息 + 可勾选任务清单
- 任务支持优先级标记、拖拽排序

### 模板管理
- 模板列表 + 编辑/删除
- 预设默认模板：诉讼 11 阶段、法律顾问 6 阶段、尽调 6 阶段
- 新建案件/项目时从模板下拉选择

## 提醒机制

1. 用户为案件阶段或项目任务设定截止日期后，自动生成提醒记录
2. 主进程通过 node-cron 定时扫描 reminders 表
3. 匹配到当前时间的提醒 → 触发系统通知弹窗
4. 通知内容：提醒标题 + 来源案件/项目 + 截止时间
5. 设置页面可配置默认提前提醒天数 (默认：截止前 1 天、3 天、7 天)

## 数据导出

- 案件清单导出为 Excel
- 单个案件报告导出为 PDF (含基本信息 + 阶段时间线)
- 非诉项目报告导出为 PDF

## 技术要点

- SQLite 数据库存放在 `{app.getPath('userData')}/lawyer-cms.db`
- 通过 contextBridge 暴露安全的 IPC 接口，渲染进程不直接访问 Node.js API
- 使用 React Router 管理页面路由
- 日历组件使用 FullCalendar 或自建月历组件
- UI 样式使用 Tailwind CSS

## 预设默认模板

### 诉讼模板 (11 阶段)
委托谈判 → 签合同 → 立案 → 保全 → 庭前准备 → 收集证据 → 预判对方证据 → 开庭审理 → 庭后答复 → 调解判决 → 归档

关键节点 (默认触发提醒)：签合同、立案、保全、收集证据、开庭审理、庭后答复、调解判决

### 法律顾问模板 (6 阶段)
需求沟通 → 材料收集 → 法律检索 → 出具意见 → 客户确认 → 归档

### 尽职调查模板 (6 阶段)
项目启动 → 资料清单发出 → 现场尽调 → 尽调报告撰写 → 报告审核 → 交付归档
