# 循环 3：工具调用系统 — 实现计划

## 目标
为 AI 问答模块和辩论引擎引入 Tool Calls 能力，让 LLM 在分析过程中主动请求数据查询和计算，而非仅依赖 prompt 中预注入的数据。通过工具调用实现 "LLM 主动索取数据" 的智能分析模式。

## 前置条件
- 循环 1（API 升级）和循环 2（Thinking 模式）已完成
- DeepSeek API 支持 OpenAI 兼容的 tool_calls 协议
- 辩论引擎、orchestrator、conversation 管理器已就绪

## 架构设计

### 数据流
```
用户请求 → 辩论引擎 → generate_with_tools() → DeepSeek API
                                                      ↓
                                              返回 tool_calls?
                                              ↓ yes          ↓ no
                                         ToolExecutor      返回最终文本
                                         执行工具
                                         追加 tool message
                                         再次调用 API ←┘
                                         (最多 N 轮)
```

### 工具列表
| 工具名 | 用途 | 数据源 |
|--------|------|--------|
| `get_financial_ratio` | 查询指定财务比率 | data dict 中已加载的 DataFrame |
| `get_peer_comparison` | 获取同行业对比数据 | 从已加载数据中提取（降级方案） |
| `detect_anomalies` | 检测财务异常信号 | SignalDetector 模块 |
| `get_historical_trend` | 获取指定指标历史趋势 | data dict 中的 DataFrame |

---

## 任务列表

### Task 1: 新建 `financial_analyzer/ai/tools.py` — 工具定义
- **文件**: `financial_analyzer/ai/tools.py`（新建）
- **内容**:
  - `TOOL_DEFINITIONS` 列表：4 个工具的 OpenAI 兼容 JSON Schema 定义
  - 每个工具定义包含 `type: "function"`, `function: {name, description, parameters}`
  - 工具参数使用 JSON Schema 格式（type, properties, required）
  - 参数示例：
    - `get_financial_ratio`: `{"ratio_name": str, "period": str}`
    - `get_peer_comparison`: `{"metric": str, "industry": str}`
    - `detect_anomalies`: `{"check_type": str}` (可选)
    - `get_historical_trend`: `{"metric_name": str, "periods": int}`
  - 导出 `get_tool_definitions()` 函数返回工具列表

### Task 2: 新建 `financial_analyzer/ai/tools.py` — ToolExecutor 类
- **文件**: `financial_analyzer/ai/tools.py`（同上）
- **类**: `ToolExecutor`
- **构造函数**: `__init__(self, data: dict, stock_code: str)`
  - 接收原始数据 dict 和股票代码
  - 保存为实例变量供工具执行使用
- **方法**: `execute(self, tool_name: str, arguments: dict) -> str`
  - 根据 tool_name 路由到对应执行函数
  - 每个执行函数返回 JSON 字符串结果
  - 异常时返回 `{"error": "..."}` 格式
- **内部方法**:
  - `_exec_get_financial_ratio(args)`: 从 data dict 中查找指定比率
    - 支持 roe, grossprofit_margin, netprofit_margin, debt_to_assets, current_ratio 等
    - 从 `data["financial"]` 或通过 report_builder 计算
  - `_exec_get_peer_comparison(args)`: 从已加载数据中提取同行数据
    - 降级方案：如果没有实时行业数据，返回 "数据不可用" 提示
    - 优先从 `data["industry"]` 或 `data["peer"]` 字段提取
  - `_exec_detect_anomalies(args)`: 调用 SignalDetector.detect()
    - 需要先构建 report（复用 ReportBuilder.build）
    - 返回 JSON 格式的异常信号列表
  - `_exec_get_historical_trend(args)`: 从 DataFrame 中提取多期数据
    - 支持 revenue, net_profit, roe, grossprofit_margin 等指标
    - 返回最近 N 期的趋势数据

### Task 3: 新增 `generate_with_tools()` 到 `client.py`
- **文件**: `financial_analyzer/deepseek/client.py`
- **位置**: 在 `DeepSeekClient` 类中，`generate_deep_analysis` 方法之后
- **方法签名**:
  ```python
  def generate_with_tools(
      self,
      user_message: str,
      tools: list[dict],
      tool_executor: callable,  # (tool_name, arguments) -> str
      system_prompt: str = None,
      max_tool_rounds: int = 3,
  ) -> AnalysisReport:
  ```
- **实现逻辑**:
  1. 构建初始 payload（messages 含 system + user，tools 字段传入工具定义）
  2. 调用 `_apply_thinking_config(payload)` — 保持 thinking 模式兼容
  3. 进入工具调用循环（最多 `max_tool_rounds` 轮）：
     a. POST 请求到 `/v1/chat/completions`
     b. 解析响应：检查 `message.tool_calls` 是否存在
     c. 若无 tool_calls → 提取 content 作为最终回答，跳出循环
     d. 若有 tool_calls → 遍历每个 tool_call：
        - 解析 `function.name` 和 `function.arguments`（JSON 字符串）
        - 调用 `tool_executor(name, arguments)` 获取结果
        - 追加 assistant message（含 tool_calls）到 messages
        - 追加 tool role message（`{"role": "tool", "tool_call_id": ..., "content": ...}`）
     e. 继续下一轮循环
  4. 返回 AnalysisReport（content = 最终文本，reasoning_content 保留）
- **关键实现细节**:
  - `tools=None` 时行为与 `_call_api()` 完全一致（向后兼容）
  - payload 中 `"stream": False` — 工具调用暂不支持流式
  - 保留 `reasoning_content` 提取（thinking 模式兼容）
  - tool_calls 响应中 content 可能为 None，需处理
  - 每轮循环记录 token 使用量（累加）

### Task 4: 辩论引擎集成工具调用 — round1
- **文件**: `financial_analyzer/ai/debate_engine.py`
- **修改位置**: `_run_debate()` 方法，round1 循环中
- **变更**:
  1. 在 `__init__` 中接收 `ToolExecutor` 实例（可选参数）
  2. 在 round1 中，将 `_stream_call` 替换为工具调用版本：
     - 当 tool_executor 存在时，调用 `generate_with_tools()`
     - 传入分析师专属 system_prompt + report 数据
     - 工具定义从 `get_tool_definitions()` 获取
  3. 由于 `generate_with_tools()` 是非流式的，需要特殊处理：
     - 调用完成后，将完整内容通过 callback 一次性发送
     - 保持 `_meta` 事件（analyst_start/analyst_done）不变

### Task 5: 辩论引擎集成工具调用 — round2
- **文件**: `financial_analyzer/ai/debate_engine.py`
- **修改位置**: `_run_debate()` 方法，round2 循环中
- **变更**:
  1. 同 round1 模式：tool_executor 存在时使用 `generate_with_tools()`
  2. round2 的 prompt 已包含 round1 的完整陈述，分析师可在此轮调用工具验证数据
  3. round3 保持不变 — 共识地图不需要工具调用

### Task 6: DebateEngine 构造函数扩展
- **文件**: `financial_analyzer/ai/debate_engine.py`
- **变更**:
  1. `__init__` 新增可选参数 `tool_executor: ToolExecutor = None`
  2. 保存为 `self.tool_executor`
  3. `prepare()` 方法中，基于传入的 data 构建 ToolExecutor（如未传入）
  4. 确保 `tool_executor=None` 时行为完全不变（向后兼容）

### Task 7: Orchestrator 传递 tool_executor
- **文件**: `financial_analyzer/ai/orchestrator.py`
- **变更**:
  1. `_stream_debate()` 中，在创建 DebateEngine 时传入 data
  2. DebateEngine 内部会自动构建 ToolExecutor
  3. 无需修改 orchestrator 的外部接口

### Task 8: 新建测试 `tests/test_tools.py`
- **文件**: `tests/test_tools.py`（新建）
- **测试用例**:
  1. `TestToolDefinitions`:
     - `test_tool_definitions_count` — 4 个工具
     - `test_each_tool_has_required_fields` — name, description, parameters
     - `test_tool_parameters_valid_json_schema` — 参数符合 JSON Schema
  2. `TestToolExecutor`:
     - `test_execute_unknown_tool` — 返回 error
     - `test_exec_get_financial_ratio` — mock data 中查找 roe
     - `test_exec_get_financial_ratio_missing` — 比率不存在时返回提示
     - `test_exec_detect_anomalies` — 调用 SignalDetector
     - `test_exec_get_historical_trend` — 从 DataFrame 提取趋势
     - `test_executor_with_empty_data` — 空数据不崩溃
  3. `TestGenerateWithTools`:
     - `test_tools_none_backward_compatible` — tools=None 时行为不变
     - `test_tool_call_loop` — mock API 返回 tool_calls，验证循环执行
     - `test_max_rounds_limit` — 超过 max_tool_rounds 时停止
     - `test_tool_call_with_thinking` — thinking 模式下工具调用正常工作
     - `test_tool_call_preserves_reasoning` — reasoning_content 正确提取

---

## 向后兼容性保证
1. `tools=None` 时 `generate_with_tools()` 行为等同于 `_call_api()`
2. `tool_executor=None` 时 DebateEngine 行为完全不变
3. 现有 `_stream_call()` 方法不修改，保持流式输出路径
4. `generate_with_tools()` 为新增方法，不影响现有 API

## 风险缓解
| 风险 | 缓解措施 |
|------|---------|
| tool_calls 与 thinking 交互 | 保留 reasoning_content 提取；thinking payload 照常注入 |
| 流式 tool_calls 解析复杂 | 先实现非流式版本；后续可扩展流式 |
| 辩论时间增加 | max_tool_rounds=3 限制；单次工具执行有 timeout |
| get_peer_comparison 数据可用性 | 降级为从已加载数据提取；无数据时返回提示 |
| 循环调用导致 token 爆炸 | max_tool_rounds 硬限制；每轮有 max_tokens 限制 |

## 预估工作量
- Task 1-2 (tools.py): ~120 行新代码
- Task 3 (generate_with_tools): ~80 行新代码
- Task 4-6 (debate 集成): ~50 行修改
- Task 7 (orchestrator): ~10 行修改
- Task 8 (tests): ~150 行测试代码
- 总计: ~410 行

## 复杂度: medium
