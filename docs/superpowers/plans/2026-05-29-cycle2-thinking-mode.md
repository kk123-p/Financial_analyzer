# 循环 2：Thinking 推理模式 — 实现计划

## 目标
启用 Thinking 推理模式，让 agent 先推理再回答，提升分析深度。

## 后端状态
- 循环 1 已铺设 thinking payload 注入、reasoning 回调链、WebSocket reasoning 字段传输
- debate_engine.py、orchestrator.py、ai_api.py 回调链已就绪
- 唯一缺口：chat_stream 方法缺少 thinking 注入和 reasoning 解析

## 任务列表

### Task 1: Flip thinking_enabled default and reasoning_effort
- File: `financial_analyzer/deepseek/client.py`
- `thinking_enabled: bool = False` → `True`
- `reasoning_effort: str = "medium"` → `"high"`

### Task 2: Add thinking payload injection to chat_stream
- File: `financial_analyzer/deepseek/client.py`
- Add same `if self.config.thinking_enabled:` block used in other methods

### Task 3: Add reasoning_content parsing to chat_stream
- File: `financial_analyzer/deepseek/client.py`
- Parse `reasoning_content` from delta, yield structured dicts

### Task 4: Handle reasoning in chatWs.onmessage
- File: `financial_analyzer/web/static/js/app.js`
- Add `msg.type === 'reasoning'` branch with collapsible `<details>` UI

### Task 5: Handle reasoning in debateWs.onmessage
- File: `financial_analyzer/web/static/js/app.js`
- Extract `msg.reasoning` from chunks, show in collapsible UI per analyst

### Task 6: Add CSS for reasoning collapsible UI
- File: `financial_analyzer/web/static/css/chat.css`
- Styles for `.chat-reasoning`, `.reasoning-content`, `.debate-reasoning`

### Task 7: Update api_v1.py SSE callback
- File: `financial_analyzer/web/routes/api_v1.py`
- Accept reasoning kwarg in callback signature

### Task 8: Verify temperature handling in thinking mode
- File: `financial_analyzer/deepseek/client.py`
- Confirm all methods pop temperature when thinking enabled

## Complexity: medium
