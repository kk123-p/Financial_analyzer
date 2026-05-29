# 循环 1：API 基础设施升级 — 实现计划

## 目标
将 DeepSeek 客户端从废弃的 `deepseek-chat` 模型迁移到新模型，移除废弃参数，提升 token 上限，并优化 prompt 结构以利用 KV 缓存。

## 任务列表

### Task 1: Update DeepSeekConfig defaults in client.py
- File: `financial_analyzer/deepseek/client.py`
- Change: `model` default from `"deepseek-chat"` to `"deepseek-v4-flash"`, `max_tokens` from `1024` to `8192`, remove `frequency_penalty` and `presence_penalty` fields

### Task 2: Remove frequency_penalty/presence_penalty from generate_deep_analysis_stream
- File: `financial_analyzer/deepseek/client.py`
- Change: Lines 286-287 -- remove deprecated params from payload dict

### Task 3: Remove frequency_penalty/presence_penalty from generate_report_stream
- File: `financial_analyzer/deepseek/client.py`
- Change: Lines 380-381 -- remove deprecated params from payload dict

### Task 4: Fix get_analysis_prompt call sites and refactor prompt structure
- Files: `client.py` + `prompts.py`
- Fix bug: `get_analysis_prompt(analysis_focus)` passes focus as first arg (wrong)
- Refactor: role context in system message, focus+data in user message

### Task 5: Optimize build_multi_perspective_prompt for KV cache
- File: `financial_analyzer/deepseek/prompts.py`
- Remove `DEEP_ANALYSIS_SYSTEM_PROMPT` from user message (already in system message)
- Restructure: fixed instructions first, variable data last

### Task 6: Update default model in debate_engine.py
- File: `financial_analyzer/ai/debate_engine.py`
- Change: Line 41 -- `deepseek-chat` to `deepseek-v4-flash`

### Task 7: Update desktop app model defaults (app.py)
- File: `financial_analyzer/deepseek/app.py`
- Update default model, dropdown options, add migration warning

### Task 8: Add unit tests
- File: `tests/test_deepseek_client.py` (new)
- Test config defaults, payload cleanup, prompt structure

## Key Finding
Bug discovered: `client.py` lines 234 and 270 call `get_analysis_prompt(analysis_focus)` with wrong arg order.

## Complexity: medium
