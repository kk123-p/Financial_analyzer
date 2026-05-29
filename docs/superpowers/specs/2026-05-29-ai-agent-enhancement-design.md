# AI 问答模块与辩论模块 Agent 增强 — 设计规格

## 概述

当前 AI 模块（deepseek/、ai/）的 agent 智力和设定未充分利用 DeepSeek API 的高级能力。本次迭代目标是通过三轮渐进式增强，将 AI 辩论系统的分析深度和专业度提升到新水平。

## 当前状态

### 已有代码

**DeepSeek 客户端：**
- `deepseek/client.py` — API 客户端，支持流式/非流式调用
- `deepseek/prompts.py` — 提示词体系，包含分析师角色、辩论流程、信号检测等
- `deepseek/app.py` — 配置管理

**AI 分析模块：**
- `ai/debate_engine.py` — 三方辩论引擎（价值/成长/风控三轮辩论）
- `ai/orchestrator.py` — 统一分析调度器
- `ai/conversation.py` — 多轮对话上下文管理
- `ai/prompt_framework.py` — 可组合提示词构建器（哈佛框架、三表联动等）
- `ai/templates.py` — 6 个预置分析模板

### 关键问题

| 问题 | 影响 |
|------|------|
| 使用已废弃模型名 `deepseek-chat` | 7月24日后将无法使用 |
| `frequency_penalty`/`presence_penalty` 已废弃 | 设置无效，增加无用参数 |
| `max_tokens` 默认 1024 | 深度分析输出被截断 |
| 未启用 thinking 推理模式 | 分析深度受限，无法展示推理过程 |
| 未使用 tool calls | 分析师无法查询精确数据，只能依赖 prompt 中的数据 |
| prompt 结构未优化 KV 缓存 | 成本高，响应慢 |
| 辩论角色 prompt 过于简单 | 分析师缺乏专业思维框架和自我质疑机制 |

## 修复方案

### 循环 1：API 基础设施升级

**目标：** 升级客户端，启用 DeepSeek 最新 API 能力

**变更文件：**
- `financial_analyzer/deepseek/client.py`
- `financial_analyzer/deepseek/prompts.py`

**具体改动：**

#### 1.1 模型名迁移

```python
# 旧
model: str = "deepseek-chat"
# 新
model: str = "deepseek-v4-flash"
# 深度分析使用 pro 模型
reasoning_model: str = "deepseek-v4-pro"
```

新增 `reasoning_model` 配置字段，深度分析和辩论场景自动使用 pro 模型。

#### 1.2 移除废弃参数

从 `DeepSeekConfig` 和所有 API 调用中移除：
- `frequency_penalty`
- `presence_penalty`

#### 1.3 启用 Thinking 推理模式

新增配置字段：
```python
thinking_enabled: bool = True
reasoning_effort: str = "high"  # "high" 或 "max"
```

在 API 请求中添加：
```python
payload = {
    ...
    "thinking": {"type": "enabled"},
    # thinking 模式下不设置 temperature/top_p（API 忽略）
}
```

流式输出时解析 `reasoning_content` 字段：
```python
delta = chunk.get("choices", [{}])[0].get("delta", {})
reasoning = delta.get("reasoning_content", "")  # 推理过程
content = delta.get("content", "")               # 最终答案
```

#### 1.4 max_tokens 调整

```python
# 旧
max_tokens: int = 1024
# 新
max_tokens: int = 8192  # 深度分析
# 快速问答保持较小值
quick_max_tokens: int = 2048
```

#### 1.5 KV 缓存优化

将 system prompt 中的固定部分（角色定义、分析框架）放在最前面，可变数据放在后面。确保多次调用同一分析师时，system prompt 前缀命中缓存。

#### 1.6 回调接口增强

```python
# 旧 callback
callback(content: str, done: bool)

# 新 callback — 增加 reasoning 参数
callback(content: str, done: bool, reasoning: str = "")
```

### 循环 2：工具调用系统

**目标：** 为分析师 agent 添加数据查询工具，辩论时可调用

**变更文件：**
- `financial_analyzer/deepseek/client.py` — 新增 tool_calls 支持
- `financial_analyzer/ai/tools.py` — **新建** — 工具定义与执行
- `financial_analyzer/ai/debate_engine.py` — 辩论流程支持工具调用

#### 2.1 工具定义（ai/tools.py）

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_metric",
            "description": "查询公司具体财务指标的精确数值。用于验证分析中的数据点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "指标名称，如 roe, pe_ttm, grossprofit_margin, debt_to_assets"
                    },
                    "period": {
                        "type": "string",
                        "description": "报告期，如 20241231。默认最新期。"
                    }
                },
                "required": ["metric"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_peer_comparison",
            "description": "获取同行业公司的对比数据，用于横向比较。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "对比指标，如 pe_ttm, roe, grossprofit_margin"
                    }
                },
                "required": ["metric"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_trend",
            "description": "获取公司某指标的历史趋势数据（近N年）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "指标名称，如 roe, net_profit, revenue"
                    },
                    "years": {
                        "type": "integer",
                        "description": "回溯年数，默认 3"
                    }
                },
                "required": ["metric"]
            }
        }
    }
]
```

#### 2.2 工具执行器

```python
class ToolExecutor:
    """根据 session 数据执行工具调用"""

    def __init__(self, data: dict, stock_code: str):
        self._data = data
        self._stock_code = stock_code

    def execute(self, tool_name: str, arguments: dict) -> str:
        """执行工具调用，返回 JSON 字符串结果"""
        ...
```

#### 2.3 client.py 新增 tool_calls 支持

```python
def generate_with_tools(self, messages, tools, tool_executor, system_prompt=None):
    """支持工具调用的生成方法"""
    # 1. 发送请求（含 tools 定义）
    # 2. 如果响应含 tool_calls，执行工具并回传结果
    # 3. 循环直到模型返回最终文本响应
    # 4. 返回最终结果
```

#### 2.4 辩论引擎集成工具调用

辩论第一轮和第二轮中，分析师可调用工具获取精确数据：
- 旧：`prompt → LLM → 文本`
- 新：`prompt → LLM → [tool_calls → 执行 → 回传] → LLM → 文本`

### 循环 3：提示词工程 + 辩论流程优化

**目标：** 增强分析师角色设定，优化辩论质量

**变更文件：**
- `financial_analyzer/deepseek/prompts.py` — 角色 prompt 增强
- `financial_analyzer/ai/debate_engine.py` — 辩论流程优化

#### 3.1 分析师角色 prompt 增强

每位分析师的 system_prompt 增加：

```
思维框架：
- 分析前先列出你将检查的 3-5 个关键维度
- 每个论点必须附带具体数据（可使用 get_financial_metric 工具查询）
- 明确区分「数据事实」和「推断判断」

自我质疑清单：
- 我的判断是否过度依赖单一指标？
- 是否存在幸存者偏差（只看到支持我观点的数据）？
- 相反的论点有哪些证据？

引用规范：
- 引用数据时必须标注：指标名、数值、报告期
- 例如：「ROE = 15.3%（2024年报）」而非「ROE 较高」
```

#### 3.2 辩论流程优化

**第一轮增加：** 要求每位分析师使用工具查询至少 2 个关键指标
**第二轮增加：** 要求引用对方具体数据点进行反驳（而非泛泛而谈）
**第三轮增加：** 添加「共识置信度」— 每个共识点标注三位分析师的一致程度

#### 3.3 引用验证机制

在辩论完成后，自动检查：
- 分析师引用的数据是否与 session 数据一致
- 标记所有无法验证的「幻觉数据」

## 验证标准

### 循环 1 验证
- 客户端可成功调用 `deepseek-v4-flash` 和 `deepseek-v4-pro`
- thinking 模式下返回 `reasoning_content`
- 流式输出正确解析推理过程和最终答案
- 无 `frequency_penalty`/`presence_penalty` 参数
- max_tokens 生效（深度分析输出不被截断）

### 循环 2 验证
- 分析师在辩论中可成功调用工具
- 工具返回的数据显示在分析结果中
- 工具调用失败时优雅降级（不中断辩论）

### 循环 3 验证
- 分析师输出包含具体数据引用
- 交叉质询引用对方具体论点
- 无明显数据幻觉

## 技术约束

- 保持现有代码架构不变（客户端、辩论引擎、调度器的接口不变）
- 向后兼容：thinking 模式可关闭，工具调用可禁用
- 不引入新依赖（使用已有的 requests 库）
- 每个循环独立可验证
