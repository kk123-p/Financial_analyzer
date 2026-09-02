# DeepSeek API 知识库

为量化 Agent 开发准备的 DeepSeek API 接入文档。

## 文档目录

### 快速开始
| 文件 | 内容 |
|------|------|
| [01_first_api_call.md](01_first_api_call.md) | 首次调用 API - 基本配置、Python/Node.js/curl 示例 |
| [02_pricing.md](02_pricing.md) | 模型与价格 - deepseek-v4-flash/pro 定价 |
| [03_token_usage.md](03_token_usage.md) | Token 用量计算 - 中英文 token 换算 |
| [04_rate_limit.md](04_rate_limit.md) | 限速与隔离 - 并发限制、user_id 隔离 |
| [05_error_codes.md](05_error_codes.md) | 错误码 - 400/401/402/429/500/503 |

### API 指南
| 文件 | 内容 |
|------|------|
| [06_thinking_mode.md](06_thinking_mode.md) | 思考模式 - 开关控制、思考强度、reasoning_effort |
| [07_multi_round_chat.md](07_multi_round_chat.md) | 多轮对话 - 上下文拼接、messages 数组组装 |
| [08_chat_prefix_completion.md](08_chat_prefix_completion.md) | 对话前缀续写 (Beta) - assistant prefix 参数 |
| [09_fim_completion.md](09_fim_completion.md) | FIM 补全 (Beta) - 前缀/后缀补全机制 |
| [10_json_output.md](10_json_output.md) | JSON Output - response_format 参数 |
| [11_tool_calls.md](11_tool_calls.md) | Tool Calls - 函数调用、strict 模式 |
| [12_kv_cache.md](12_kv_cache.md) | 上下文硬盘缓存 - 落盘规则、命中机制 |
| [13_anthropic_api.md](13_anthropic_api.md) | Anthropic API 兼容层 - 模型映射 |

### 参考文档
| 文件 | 内容 |
|------|------|
| [14_faq.md](14_faq.md) | 常见问题 - 账户、认证、计费 |
| [15_api_reference.md](15_api_reference.md) | API 参考 - 4 个端点详细参数 |

## 关键信息速查

### 基本配置
```python
from openai import OpenAI
client = OpenAI(
    api_key="your_api_key",
    base_url="https://api.deepseek.com"
)
```

### 可用模型
- `deepseek-v4-flash` - 轻量级模型
- `deepseek-v4-pro` - 专业级模型

### 核心功能
- **思考模式**: `thinking={"type": "enabled"}`, `reasoning_effort="high"`
- **流式输出**: `stream=True`
- **Tool Calls**: 支持函数调用
- **JSON 输出**: `response_format={"type": "json_object"}`
- **上下文缓存**: 自动缓存长上下文，降低成本

### API 端点
- `POST /chat/completions` - 对话补全
- `POST /completions` - FIM 补全 (Beta)
- `GET /models` - 获取模型列表
- `GET /user/balance` - 查询账户余额
