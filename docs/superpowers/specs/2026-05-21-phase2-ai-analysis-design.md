# Phase 2 AI 智能财务分析模块 — 设计说明

## 背景与目标

第一阶段（传统财务分析）已完成：数据获取 → 标准化财务计算 → 结构化报告 + 图表。

第二阶段目标：
1. **提示词升级** — 将专业财务分析框架（哈佛分析、三表联动、生命周期、预警清单）编码进提示词
2. **输出质量可控** — 约束 AI 输出为「数据→推理→结论」三段式，附置信度与数据来源
3. **交互式分析** — 分析中可介入引导 + 报告后可追问，统一对话式体验

## 架构决策

### 三层分离

```
Web UI (Jinja2 + htmx + WebSocket)
  → AI Analysis Service (核心逻辑，独立于 UI)
    → LLM Adapter (DeepSeek / OpenAI / Claude / Ollama)
```

核心分析逻辑不绑定任何 UI 层，可复用至桌面端。

### 模块职责

**新增模块（`financial_analyzer/ai/`）：**

| 模块 | 文件 | 职责 |
|------|------|------|
| PromptFramework | `ai/prompt_framework.py` | 可组合提示词构建器，注入专业框架 |
| OutputParser | `ai/output_parser.py` | 流式解析 + 结构化提取（数据/推理/结论/标签） |
| ConversationManager | `ai/conversation.py` | 多轮对话上下文、消息历史、分支话题 |
| AnalysisOrchestrator | `ai/orchestrator.py` | 意图识别 → 模式选择 → 工具调度 → 格式化 |

**复用/重构模块：**

| 模块 | 策略 |
|------|------|
| `deepseek/prompts.py` | 重构为 PromptFramework 的下层引擎 |
| `deepseek/client.py` | 保留，作为 LLM Adapter 的 DeepSeek 实现 |
| `ai/debate_engine.py` | 保留，由 Orchestrator 在 `/debate` 模式下调用 |
| `ai/report_builder.py`, `ai/signal_detector.py`, `ai/briefing_generator.py` | 保留不变 |

### UI 变更

- **替换** `index.html` 中 AI Tab 的两个子面板（AI 智能分析 / 三方辩论）为一个统一对话面板
- **新增** `static/css/chat.css` — 对话消息样式
- **更新** `static/js/app.js` — 统一 WebSocket 连接 + 消息类型分发 + 流式渲染
- 保持 Precision Glass 设计风格一致

### API 变更

- **新增** `WebSocket /ai/conversation` — 统一对话入口，替换 `/ai/chat` (HTTP POST) 和 `/ai/debate` (WebSocket)
- **保留** 旧端点，标记 deprecated，确保向后兼容

### 提示词框架

**4 个可组合框架层：**

1. **哈佛分析框架** — 战略→会计→财务→前景，作为深度分析顶层纲领
2. **三表联动验证** — 经营性资产→营业利润→经营现金流 勾稽关系强制检查
3. **生命周期定位** — 导入/成长/成熟/衰退期现金流特征矩阵
4. **利润质量 13 条预警** — 强制逐条核验（扩张过快/应收异常/过度举债/会计变更等）

**4 种分析模式：**

| 模式 | 触发方式 | 提示词策略 |
|------|---------|-----------|
| 快速问答 | 默认 | 数据 + 问题，轻量提示词 |
| 深度分析 | `/deep` | 数据 + 框架 + 交叉验证，完整提示词 |
| 三方辩论 | `/debate` | 三视角 prompt + 3 轮辩论流程 |
| 追问 | 自然对话 | 上下文注入 + 局部数据补充 |

**输出约束：** 每个分析结论必须以「📊 数据依据 → 🔍 推理过程 → ✅ 综合结论」三段式输出，附带置信度标签（高/中/低）和信号评分标签。

### 对话交互协议（WebSocket 消息类型）

```
chunk      — 文本流片段
meta       — 阶段切换（round1_start / round2_start / round3_start）
tool_call  — AI 调用计算工具（工具名 + 参数 + 结果）
structured — 解析完成的结构化卡片（JSON）
done       — 当前分析流结束
error      — 异常信息
```

## 实现路线图

### Step 1：核心模块新建（不改现有代码）

- 新建 `ai/prompt_framework.py`
- 新建 `ai/output_parser.py`
- 新建 `ai/conversation.py`
- 新建 `ai/orchestrator.py`
- 重构 `deepseek/prompts.py`

### Step 2：WebSocket 对话式 API

- 新建 `WebSocket /ai/conversation` 统一入口
- 消息类型分发与流式推送
- 旧接口保留（`/ai/chat`, `/ai/debate`）

### Step 3：Web UI 统一对话面板

- 新增 `css/chat.css`
- 更新 `index.html` AI Tab
- 更新 `js/app.js` 对话 WebSocket 客户端

### Step 4：集成测试 + 打磨

- 端到端测试
- 提示词效果调优
- 样式动画打磨

## 风险控制

- API Token 消耗：深度分析模式消耗较大，建议限制 `/debate` 频率
- 流式解析：结构化输出需在流式接收中分块解析，注意标签边界处理
- 向后兼容：旧接口保留，不影响现有功能
- 可回退：核心模块独立于 UI，问题只影响对话面板，不波及主分析功能
- 渐进发布：4 步线性递进，每步可独立验证
