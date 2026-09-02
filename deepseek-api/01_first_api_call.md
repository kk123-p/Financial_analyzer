# DeepSeek API 首次调用指南

## 概述

DeepSeek API 使用与 OpenAI/Anthropic 兼容的 API 格式，通过修改配置，您可以使用 OpenAI/Anthropic SDK 来访问 DeepSeek API。

## 基本配置

| 参数 | 值 |
|------|-----|
| base_url (OpenAI) | `https://api.deepseek.com` |
| base_url (Anthropic) | `https://api.deepseek.com/anthropic` |
| api_key | [申请 API Key](https://platform.deepseek.com/api_keys) |
| model | `deepseek-v4-flash`, `deepseek-v4-pro` |

> **注意**: `deepseek-chat` 与 `deepseek-reasoner` 两个模型名将于 2026/07/24 弃用，分别对应 `deepseek-v4-flash` 的非思考与思考模式。

## 调用示例

### curl 示例

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
  -d '{
        "model": "deepseek-v4-pro",
        "messages": [
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user", "content": "Hello!"}
        ],
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "stream": false
      }'
```

### Python 示例

```python
# pip3 install openai
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

print(response.choices[0].message.content)
```

### Node.js 示例

```javascript
// npm install openai
import OpenAI from "openai";

const openai = new OpenAI({
    baseURL: 'https://api.deepseek.com',
    apiKey: process.env.DEEPSEEK_API_KEY,
});

async function main() {
    const completion = await openai.chat.completions.create({
        messages: [{ role: "system", content: "You are a helpful assistant." }],
        model: "deepseek-v4-pro",
        thinking: {"type": "enabled"},
        reasoning_effort: "high",
        stream: false,
    });

    console.log(completion.choices[0].message.content);
}

main();
```

## Agent 工具接入

DeepSeek API 已接入多种主流 AI Agent 与编程助手工具：
- Claude Code
- GitHub Copilot
- OpenCode

可以直接将 DeepSeek 作为后端模型，无需编写代码即可开始使用。
