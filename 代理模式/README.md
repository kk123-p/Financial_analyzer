# Agent Teams 多模型代理（实验性）

让 Claude Code Agent Teams 的不同 agent 走不同的后端模型。

## 工作原理

```
Claude Code
    │  ANTHROPIC_BASE_URL=http://localhost:4002
    ▼
routing_proxy.py (:4002)
    │
    ├── model: opus   ──► DeepSeek V4 Pro  (顶层设计)
    ├── model: sonnet ──► DeepSeek V4 Pro  (主对话)
    └── model: haiku  ──► Mimo V2.5 Pro   (代码执行)
```

## 使用方法

### 启动代理

双击 `start_proxy.bat`，窗口保持打开即可。

### 切换到代理模式

双击 `proxy_on.bat` → 重启 Claude Code

### 切回直连模式

双击 `proxy_off.bat` → 重启 Claude Code

## 已知问题

- Mimo 的 Anthropic 端点兼容性有限，部分请求返回格式异常
- 流式响应的模型名改写未完全处理
- VS Code 环境变量与 settings.local.json 可能冲突，导致切换失败（当前版本不可用）

## 文件说明

| 文件 | 用途 |
|------|------|
| `routing_proxy.py` | 路由代理核心（Python） |
| `start_proxy.bat` | 一键启动代理 |
| `proxy_on.bat` | 写入 settings 切换到代理模式 |
| `proxy_off.bat` | 删除 settings 切回直连 |
| `proxy_config.yaml` | LiteLLM 配置（已弃用，仅供参考） |

## 依赖

- Python 3.13+（项目 .venv）
- aiohttp
