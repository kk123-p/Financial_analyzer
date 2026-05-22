# AI 分析模块简化 — 设计说明

## 背景

当前 AI 问答模块自动将财务数据、角色定义、分析框架和输出格式注入 LLM 的 system prompt，导致 LLM 对任何问题都试图用全套数据做结构化分析，循环输出同质化内容。同时顶部数据导出按钮分散（Excel/CSV/JSON 三个按钮），第一阶段的各项分析结果无法方便复制。

## 目标

1. **AI 问答化繁为简** — 移除后端自动注入逻辑，LLM 纯粹回答用户输入的内容
2. **分析结果复制按钮** — 第一阶段每个分析模块标题栏增加复制按钮
3. **数据导出合并** — 顶部三个导出按钮合并为弹窗统一导出

---

## 模块 1：AI 问答简化

### 改动

**orchestrator.py：**
- 删除 `_build_system_context()` 方法
- `_stream_quick` / `_stream_deep` / `_stream_followup` 合并为单一 `_stream_chat` 方法
- 调用 `_llm.generate_deep_analysis_stream(message, callback=on_chunk)` — 不传 `system_prompt`，使用客户端默认
- `/deep` 和 `/debate` 命令保留，但 deep 模式与 quick 模式行为一致（纯问答）

**prompt_framework.py：**
- `PromptBuilder` 类保留不动（为 Prompt Lab 模板编辑功能服务）
- `OUTPUT_FORMAT_STRUCTURED` 常量保留（模板编辑时会引用）
- 移除 orchestrator 对 `PromptBuilder.build()` 的调用

**前端（base.html + app.js）：**
- Prompt Lab 工具栏保留：模板选择器、编辑 Prompt、财务数据报告、预览 Prompt
- 模板选择不影响实际 prompt 注入（LLM 只接收用户输入）
- 模板功能降级为"参考模板"：用户可编辑、导出供自己参考

### 行为变化

```
改动前：
  用户输入"PE是多少"
  → orchestrator 构建 system_context (角色 + 完整财务数据 + 格式)
  → LLM 收到：system=5000字上下文, user="PE是多少"
  → LLM 混乱，循环输出

改动后：
  用户输入"PE是多少" (或粘贴了数据的完整消息)
  → LLM 收到：user="PE是多少"
  → LLM 直接回答
```

### 无影响的部分

- **AI 辩论**（`/ai/debate`）— 独立路径，不受影响
- **Prompt Lab** — 编辑和存储功能保留，但不自动注入
- **财务数据报告 API**（`/ai/report`）— 保留

---

## 模块 2：分析结果复制按钮

### 实现

在每个分析结果区域的标题栏右侧添加 HTML 复制按钮：

```html
<button class="copy-btn" onclick="copyResult(this)">📋 复制</button>
```

JavaScript 复制逻辑：
```js
function copyResult(btn) {
    const container = btn.closest('.result-section');
    const text = container.innerText;
    navigator.clipboard.writeText(text).then(() => {
        // 短暂显示"已复制"
        btn.textContent = '✓ 已复制';
        setTimeout(() => btn.textContent = '📋 复制', 1500);
    });
}
```

后端实现：在 `result_formatter.py` 的每个 section 渲染时，标题栏追加复制按钮。

---

## 模块 3：数据导出合并

### 按钮

顶栏三个按钮（Excel / CSV / JSON）合并为一个：

```html
<button class="btn" onclick="openExportModal()">数据导出</button>
```

### 弹窗

```
┌──────────────────────────────────────┐
│ 导出数据                         [×] │
│                                      │
│ 导出内容：                           │
│ ☑ 利润表     ☑ 资产负债表            │
│ ☑ 现金流量表  ☑ 行情数据(日线)       │
│ ☐ 财务指标   ☐ 杜邦分析             │
│                                      │
│ 导出格式：                           │
│ ○ Excel (.xlsx)                      │
│ ○ CSV (.csv)                         │
│ ○ JSON (.json)                       │
│                                      │
│              [取消]  [导出]          │
└──────────────────────────────────────┘
```

- 导出内容列表动态生成 — 根据当前 session 已获取的 Tushare 数据类别显示勾选项
- 至少显示：利润表、资产负债表、现金流量表、行情数据
- 如果 session 中有财务指标等衍生数据，也列出来
- 导出格式三选一

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **修改** | `financial_analyzer/ai/orchestrator.py` | 删除 `_build_system_context`，简化流式方法 |
| **修改** | `financial_analyzer/web/templates/base.html` | 顶栏按钮合并 + 导出弹窗 HTML |
| **修改** | `financial_analyzer/web/static/js/app.js` | 导出弹窗逻辑 + 复制按钮逻辑 |
| **修改** | `financial_analyzer/web/services/result_formatter.py` | 分析结果标题栏加复制按钮 |
| **修改** | `financial_analyzer/web/routes/export_api.py` | 支持按选中类别导出 |
| **修改** | `tests/test_orchestrator.py` | 更新测试匹配新行为 |

---

## 风险控制

- **向后兼容** — `/deep` 和 `/debate` 命令路径保留，只是行为统一
- **辩论独立** — 辩论引擎不修改，不受影响
- **Prompt Lab 保留** — 模板存储和编辑功能不删除，用户可继续使用
- **渐进** — 三步独立，每步可单独验证
