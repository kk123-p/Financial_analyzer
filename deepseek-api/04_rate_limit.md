# DeepSeek API - 限速与隔离

> 来源: https://api-docs.deepseek.com/zh-cn/quick_start/

# 限速与隔离

## 并发限速​

对每个账号，DeepSeek API 不同模型的并发限制如下表所示。

若您有更高的并发需求，可提交[账号扩容申请工单](https://trtgsjkv6r.feishu.cn/share/base/form/shrcnda9jNKvhyYr8xb843xLEzc)，我们将根据您实际的业务需求匹配合适的并发量，扩容并不增加额外的费用。

|  | deepseek-v4-pro | deepseek-v4-flash |
|---|---|---|
| 并发限制 | 500 | 2500 |

- 一个请求从发出后，到模型响应完成之前记为一个并发
- 并发限制以账号粒度计，与 API Key 无关
- 对于一个账号，在并发限度内，您的 API 请求都会得到响应；超过并发限度时，您会收到 HTTP 429 错误码

---

## user_id 隔离​

用户可以向 API 传递 `user_id` 参数，来实现同一账号下，对您业务侧不同用户的细粒度管理。`user_id` 的具体功能如下：

- **内容安全隔离：**`user_id` 用于我们区分您业务侧的用户身份，以进行内容安全状况处理
- **KVCache 隔离：**`user_id` 用于我们对您业务侧用户进行 KVCache 隔离，以进行隐私管理
- **调度隔离：**`user_id` 用于我们对您业务侧用户进行调度隔离 

- 对于普通 API 用户，所有 `user_id` 合并计算并发限速
- 对于提升了并发配额的 API 用户，我们会限制您账号下的总并发，同时我们会对每个您传入的 `user_id` 进行并发限制（空 id 为一个特殊的 `user_id`）。对每个 `user_id`，deepseek-v4-pro 并发限制为 500，deepseek-v4-flash 并发限制为 2500。若某个 `user_id` 超过了该限制，则您账号下设置了该 `user_id` 的请求将会收到 HTTP 429 错误码

### user_id 设置方法​

`user_id` 参数需为满足正则表达式 `[a-zA-Z0-9\-_]+` 的字符串，最大长度为 512。请不要在 `user_id` 中包含用户隐私信息。

您可以通过以下方式，设置 `user_id` 参数：

#### OpenAI Chat Completions 接口​

HTTP 请求体：

```
{    "model": "deepseek-v4-pro",    "messages": {"role": "user", "content": "Hello!"},    "user_id": "your_user_id"}
```

如果您使用的是 OpenAI SDK，您需要将 `user_id` 参数放入 `extra_body` 参数下面：

```
response = client.chat.completions.create(    model="deepseek-v4-pro",    messages=[{"role": "user", "content": "Hello!"}],    extra_body={"user_id": "your_user_id"})
```

#### Anthropic 接口​

HTTP 请求体：

```
{    "model": "deepseek-v4-pro",    "messages": {"role": "user", "content": "Hello!"},    "metadata": {"user_id": "your_user_id"},    "max_tokens": 1024}
```

如果您使用的是 Anthropic SDK，调用方式如下：

```
message = client.messages.create(    model="deepseek-v4-pro",    messages=[{"role": "user", "type": "text", "content": "Hello!"}],    metadata={"user_id": "your_user_id"},    max_tokens=1024)
```

---

## 请求保活机制​

您的请求发出后，有时需要等待一段时间才能获取服务器的响应。在这段时间里，您的 HTTP 请求会保持连接，并持续收到如下格式的返回内容：

- 非流式请求：持续返回空行
- 流式请求：持续返回 SSE keep-alive 注释（`: keep-alive`）

这些内容不影响对响应的 JSON body 的解析。如果您在自己解析 HTTP 响应，请注意处理这些空行或注释。

如果 10 分钟后，请求仍未开始推理，服务器将关闭连接。
