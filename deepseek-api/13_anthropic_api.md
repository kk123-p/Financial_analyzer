<!-- markdownlint-disable MD036 -->
# Anthropic API

为了满足大家对 Anthropic API 生态的使用需求，DeepSeek API 新增了对 Anthropic API 格式的支持，其 `base_url` 为 `https://api.deepseek.com/anthropic`。

通过简单的配置，即可将 DeepSeek 的能力，接入到 Anthropic API 生态中。

## 将 DeepSeek 模型接入 Claude Code

请参考[接入 Agent 工具](/zh-cn/guides/coding_agents)。

## 通过 Anthropic API 调用 DeepSeek 模型

**1. 安装 Anthropic SDK**

```bash
pip install anthropic
```

**2. 配置环境变量**

```bash
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_API_KEY=${YOUR_API_KEY}
```

**3. 调用 API**

```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="deepseek-chat",
    max_tokens=1000,
    system="You are a helpful assistant.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Hi, how are you?"
                }
            ]
        }
    ]
)

print(message.content)
```

**注意**：当您给 DeepSeek 的 Anthropic API 传入不支持的模型名时，API 后端会自动将其映射到 `deepseek-chat` 模型。

## Anthropic 模型映射

您在使用 Anthropic API 时，DeepSeek 会对您传入的 claude 模型名进行映射：

- `claude-opus` 开头的模型，会映射到 `deepseek-reasoner`
- `claude-haiku`、`claude-sonnet` 开头的模型，会映射到 `deepseek-chat`

通过这样的映射，您在使用新版 Claude Desktop APP 的 developer 模式时，可以绕过 APP 对模型名的限制，只需改动 `base_url` 和 `api_key`，即可在其中接入 DeepSeek 模型。

## Anthropic API 兼容性细节

### HTTP Header

| Field | Support Status |
| --- | --- |
| `anthropic-beta` | Ignored |
| `anthropic-version` | Ignored |
| `x-api-key` | Fully Supported |

### Simple Fields

| Field | Support Status |
| --- | --- |
| `model` | Use DeepSeek Model Instead |
| `max_tokens` | Fully Supported |
| `container` | Ignored |
| `mcp_servers` | Ignored |
| `metadata` | `user_id` is supported, others are ignored. Please refer to [Rate Limit & Isolation](/zh-cn/quick_start/rate_limit) for more information about `user_id` parameter. |
| `service_tier` | Ignored |
| `stop_sequences` | Fully Supported |
| `stream` | Fully Supported |
| `system` | Fully Supported |
| `temperature` | Fully Supported (range [0.0 ~ 2.0]) |
| `thinking` | Supported (`budget_tokens` is ignored) |
| `output_config` | Only `effort` is supported |
| `top_k` | Ignored |
| `top_p` | Fully Supported |

### Tool Fields

#### tools

| Field | Support Status |
| --- | --- |
| `name` | Fully Supported |
| `input_schema` | Fully Supported |
| `description` | Fully Supported |
| `cache_control` | Ignored |

#### tool_choice

| Value | Support Status |
| --- | --- |
| `none` | Fully Supported |
| `auto` | Supported (`disable_parallel_tool_use` is ignored) |
| `any` | Supported (`disable_parallel_tool_use` is ignored) |
| `tool` | Supported (`disable_parallel_tool_use` is ignored) |

### Message Fields

| Field | Variant | Sub-Field | Support Status |
| --- | --- | --- | --- |
| `content` | string | | Fully Supported |
| | array, type="text" | `text` | Fully Supported |
| | | `cache_control` | Ignored |
| | | `citations` | Ignored |
| | array, type="image" | | Not Supported |
| | array, type="document" | | Not Supported |
| | array, type="search_result" | | Not Supported |
| | array, type="thinking" | | Supported |
| | array, type="redacted_thinking" | | Not Supported |
| | array, type="tool_use" | `id` | Fully Supported |
| | | `input` | Fully Supported |
| | | `name` | Fully Supported |
| | | `cache_control` | Ignored |
| | array, type="tool_result" | `tool_use_id` | Fully Supported |
| | | `content` | Fully Supported |
| | | `cache_control` | Ignored |
| | | `is_error` | Ignored |
| | array, type="server_tool_use" | | Supported |
| | array, type="web_search_tool_result" | | Supported |
| | array, type="code_execution_tool_result" | | Not Supported |
| | array, type="mcp_tool_use" | | Not Supported |
| | array, type="mcp_tool_result" | | Not Supported |
| | array, type="container_upload" | | Not Supported |
