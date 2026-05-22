# AI 问答模块模板化重构 — 设计说明

## 概述

重构 AI 问答模块，从当前"空 system_prompt 透传 LLM"的通用对话模式，转变为"模板驱动 + 数据智能注入"的差异化分析工具。

## 问题分析

当前 `/ai/conversation` WebSocket 的 quick/deep 模式下，`_stream_chat()` 将用户消息直接发送给 LLM（`system_prompt=""`），未注入任何财务数据。用户完全可以用任何免费 AI 网页代替。

## 差异化定位

**不用本系统做的事：** 打开 free AI 网页 → 手动复制粘贴数据 → 自由提问 → 得到随意回答

**用本系统做的事：** 选模板 → 系统自动匹配并裁剪数据 → AI 按框架解读 → 结构化报告（格式统一、同模板不同股票可对比）

## 核心设计原则

- 不计算财务指标（这些数据已由 Tushare `fina_indicator` 和其他模块提供）
- 不提供评分（AI 评分无意义）
- 专注于**解读和综合**已有数据

---

## 一、模板系统

### 存储

JSON 文件存储在 `~/.financialanalyzer/prompts/`（复用现有 PromptStore）。分为系统预置（不可删除，可复制编辑）和用户自定义（自由 CRUD）。

### 模板 JSON Schema

```json
{
  "name": "盈利能力深度解读",
  "description": "基于毛利率、净利率、ROE、盈利质量解读企业盈利水平",
  "mode": "template",
  "system_role": "你是一位拥有20年经验的买方财务分析师...",
  "data_required": {
    "primary": ["financial", "income"],
    "secondary": ["balance", "cashflow"]
  },
  "analysis_sections": [
    {
      "title": "毛利率趋势与竞争壁垒",
      "focus_metrics": ["grossprofit_margin", "revenue"],
      "guidance": "分析近5年毛利率趋势，判断定价权和竞争壁垒..."
    }
  ],
  "output_format": {
    "section_template": "▌ {title}\n  数据现状: ...\n  趋势判断: ...\n  解读: ...",
    "final_output": "▌ 核心发现\n  {key_findings}"
  }
}
```

### 首批 6 个预置模板

| # | 模板名称 | Primary 数据 | 解读维度 |
|---|---|---|---|
| 1 | 盈利能力深度解读 | financial, income | 毛利率/净利率/ROE驱动/盈利质量 |
| 2 | 财务异常信号排查 | balance, income, cashflow | 资产端/利润端/现金流/勾稽关系 |
| 3 | 估值合理性判断 | daily_basic, financial, dividend | PE分位/股息率/DCF锚点 |
| 4 | 股东结构评估 | top10_holders, stk_holdernumber | 股权集中度/机构持仓/筹码趋势 |
| 5 | 资金面多空分析 | moneyflow, margin, hk_hold | 主力方向/融资情绪/北向态度 |
| 6 | 成长质量检查 | income, cashflow, financial | 营收CAGR/利润CAGR/现金流画像 |

---

## 二、Prompt 组装机制

### 处理流程

```
用户选模板 → Step 1: 数据筛选 → Step 2: 数据裁剪 → Step 3: 格式化注入 → Step 4: 组装 Prompt
```

### Step 1: 数据筛选

按 `data_required.primary` 和 `secondary` 从 session 数据中提取。primary 缺失则提示用户，secondary 有则加入。

### Step 2: 数据裁剪

- 只取每个 section 的 `focus_metrics` 列
- 财务表取近 5 期，行情表取近 20 条
- 避免全量注入，控制 token 消耗在 800-1500 tokens 级别

### Step 3: 格式化注入

不同类型用不同格式：

| 数据类型 | 格式化方式 | 行数 |
|---|---|---|
| financial/income/balance/cashflow | Markdown 表格（只取 focus_metrics 列） | 近 5 期 |
| daily/weekly/monthly | 最新值 + 区间统计 | 最新 1 期 |
| moneyflow/margin/hk_hold | 最新值 + 趋势文本 | 近 20 日 |
| top10_holders/stk_holdernumber | 文字摘要 | 最新期 + 趋势 |
| dividend | 最新一次 + 近5年累计 | 近 5 期 |

### Step 4: 组装 Prompt

```
## SYSTEM
{system_role}

## 分析任务
对 {stock_code} {company_name} 执行「{template_name}」

## 分析框架
{sections_guidance}

## 输出格式
{output_format}

## 当前数据
{formatted_data}

## 用户补充（如有）
{extra_question}
```

---

## 三、WebSocket 执行流

### 新增消息类型

现有 `/ai/conversation` WebSocket 支持 `message`/`stop`。新增：

```json
// 前端 → 后端
{"type": "template", "template_name": "...", "extra_question": ""}

// 后端 → 前端：模板开始
{"type": "meta", "content": "template_start", "meta": {"template": "...", "sections": 5}}

// 后端 → 前端：每个 section 完成
{"type": "template_section", "content": "<分析文本>", "meta": {"section_index": 0, "section_title": "..."}}

// 后端 → 前端：全部完成
{"type": "template_done", "content": "", "meta": {"key_findings": "..."}}
```

### Orchestrator 改动

`_identify_intent()` 新增 `template` 意图识别（用户选模板的消息格式）。

`_stream_template()` 新方法：
1. 加载模板 JSON
2. 数据筛选 + 裁剪 + 格式化
3. 组装 prompt
4. 流式调用 LLM
5. 按 section 边界拆分输出，每个 section 完成即 callback `template_section`
6. 全部完成 callback `template_done`

### 自由提问增强

自由提问模式不再空 system_prompt，改为注入轻量数据摘要（价格、PE、市值、营收、净利润、毛利率、净利率、ROE、资产负债率、主力净流入、融资余额、北向持股、股东人数），约 300-500 tokens。

---

## 四、前端 UI

### AI 对话面板改动

```
┌─────────────────────────────────────────┐
│  📋 模板快速分析                          │
│                                          │
│  📊 盈利能力深度解读        [执行]         │
│  🔍 财务异常信号排查        [执行]         │
│  💰 估值合理性判断          [执行]         │
│  🏦 股东结构评估            [执行]         │
│  📈 成长质量检查            [执行]         │
│  ⚡ 资金面多空分析          [执行]         │
│  ─────────────────────────────           │
│  或自由提问...                             │
│  [_______________________________] [发送] │
└─────────────────────────────────────────┘
```

### 模板结果渲染

每个 section 作为独立卡片渲染，最后汇总核心发现：

```
┌────────────────────────────────────────┐
│  📊 盈利能力深度解读 — 比亚迪(002594.SZ) │
│                                        │
│  ┌─ ▌ 毛利率趋势与竞争壁垒 ──────────┐  │
│  │  数据现状: ...                     │  │
│  │  趋势判断: ...                     │  │
│  │  解读: ...                         │  │
│  └──────────────────────────────────┘  │
│  ...（共 N 个 section 卡片）           │
│                                        │
│  ┌─ ▌ 核心发现 ─────────────────────┐  │
│  │  毛利率+净利率双重提升，新能源车    │  │
│  │  规模效应显现，ROE由利润驱动可持续。│  │
│  └──────────────────────────────────┘  │
│                                        │
│  [📋 换模板] [💾 导出报告]              │
└────────────────────────────────────────┘
```

### 模板选择交互

- 模板列表横向排列，点击即选中
- 选中后自动发送 `{"type": "template", ...}` 消息
- 支持一次对话中多次切换模板
- 自由提问输入框始终保留，模板执行完后可追问

---

## 五、错误处理

- 模板 primary 数据缺失 → 提示"需要 {data_type} 数据，请先获取财务数据"
- 模板加载失败 → 提示"模板已损坏或不存在"
- LLM 调用失败 → 显示错误信息，允许重试
- section 解析失败 → 降级为完整文本输出（不做卡片分割）

---

## 六、不改动部分

- 三方辩论模块（debate_engine.py, `/ai/debate` WebSocket）保持不变
- 现有数据管道、analyzer 模块不涉及
- 现有 Prompt CRUD API（`/ai/prompts/*`）复用，仅新增模板字段
