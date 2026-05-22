# AI 分析模块简化 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify AI Q&A by removing auto-injected context, add copy buttons to analysis results, merge 3 export buttons into 1 modal.

**Architecture:** Remove `_build_system_context()` from orchestrator, unify quick/deep/followup into a single `_stream_chat` that passes user message directly to LLM. Add `📋 复制` buttons in result_formatter. Replace top-bar export buttons with single modal supporting format + data-type selection.

**Tech Stack:** Python 3.11+, FastAPI, vanilla JS, Precision Glass CSS

---

## 文件结构

```
financial_analyzer/ai/
└── orchestrator.py          # MODIFY: 删除 _build_system_context, 合并流式方法

financial_analyzer/web/
├── services/result_formatter.py  # MODIFY: h2/h3 标题栏加复制按钮
├── routes/export_api.py          # MODIFY: 支持 categories 参数
├── templates/base.html           # MODIFY: 顶栏按钮合并 + 导出弹窗 HTML
└── static/js/app.js              # MODIFY: 导出弹窗 JS + 复制按钮 JS

tests/
└── test_orchestrator.py          # MODIFY: 更新测试
```

---

## Task 1: AI 问答简化 — orchestrator 移除自动注入

**Files:**
- Modify: `financial_analyzer/ai/orchestrator.py:38-240`
- Modify: `tests/test_orchestrator.py:75-112`

- [ ] **Step 1: 更新测试文件，移除 _build_system_context 测试**

在 `tests/test_orchestrator.py` 中，找到 `TestAnalysisOrchestratorBuildPrompt` 类，删除其中的两个测试方法（因为 `_build_system_context` 将被移除）：

```python
# 删除 TestAnalysisOrchestratorBuildPrompt 整个类
# 原来的 test_build_system_context_quick_mode 和 
# test_build_system_context_deep_mode_includes_frameworks 不再适用
```

将类替换为空的或删除：

```python
# TestAnalysisOrchestratorBuildPrompt 已移除 — orchestrator 不再构建 system context
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_orchestrator.py -v
```
Expected: errors (测试引用了不存在的方法)

- [ ] **Step 3: 实现 orchestrator 简化**

在 `orchestrator.py` 中，将 `analyze()` 方法的内容替换为：

```python
def analyze(
    self,
    user_message: str,
    conversation: ConversationManager,
    data: dict,
    stock_code: str,
    company_name: str = "",
    callback: Callable | None = None,
):
    """统一分析入口 — 所有模式行为一致，LLM 纯问答"""
    conversation.add_message(Message(role="user", content=user_message, msg_type="text"))

    intent = self._identify_intent(user_message, conversation)

    if callback:
        callback("meta", f"intent:{intent}", None)

    if intent == "debate" and self._debate_factory:
        self._stream_debate(data, stock_code, company_name, conversation, callback)
    else:
        self._stream_chat(user_message, conversation, callback)
```

删除 `_build_system_context()` 方法，将 `_stream_quick` / `_stream_deep` / `_stream_followup` 替换为单一的 `_stream_chat`：

```python
def _stream_chat(self, message, conversation, callback):
    """纯问答模式 — 用户消息直接发给 LLM，无自动注入"""
    parser = OutputParser()

    def on_chunk(chunk: str, done: bool):
        if chunk:
            for event in parser.feed(chunk):
                if callback:
                    cb_type = event.get("type", "chunk")
                    callback(cb_type, event.get("content", ""), None)
        if done:
            result = parser.finalize()
            if result and callback:
                callback("chunk", result.raw_text, None)
                callback("structured", result.raw_text, {
                    "confidence": result.confidence,
                    "signal_tags": result.signal_tags,
                })
                conversation.add_message(Message(
                    role="assistant", content=result.raw_text,
                    msg_type="structured",
                    metadata={"confidence": result.confidence, "signal_tags": result.signal_tags},
                ))
            if callback:
                callback("done", "", None)

    result = self._llm.generate_deep_analysis_stream(message, callback=on_chunk)
    if not result.success:
        if callback:
            callback("error", result.error or "AI 分析失败", None)
            callback("done", "", None)
```

删除以下四个方法：
- `_build_system_context()`
- `_stream_quick()`
- `_stream_deep()`
- `_stream_followup()`

保留：
- `_identify_intent()` — 保留（用于识别 `/debate` 命令）
- `_stream_debate()` — 保留（辩论引擎）
- `analyze()` — 修改

同时删除 orchestrator.py 头部不再需要的 import：
```python
# 删除
from .prompt_framework import PromptBuilder
from .signal_detector import SignalDetector
from .report_builder import ReportBuilder
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_orchestrator.py -v
```
Expected: all remaining tests PASS

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -q --ignore=tests/test_adapter.py
```
Expected: 274 passed, 1 pre-existing failure (test_us_market_adjustment)

- [ ] **Step 6: 提交**

```bash
git add financial_analyzer/ai/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: simplify AI Q&A — remove auto-injected context, pure chat mode

Deleted _build_system_context, _stream_quick, _stream_deep, _stream_followup.
Replaced with single _stream_chat() that sends user message directly to LLM
without system_prompt injection. Debate path unchanged. Prompt Lab preserved.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: 分析结果复制按钮

**Files:**
- Modify: `financial_analyzer/web/services/result_formatter.py`
- Modify: `financial_analyzer/web/static/js/app.js`

- [ ] **Step 1: 在 result_formatter.py 的 h2/h3 标题后追加复制按钮**

查找 `result_formatter.py` 中渲染 h2 和 h3 标题的代码，在每个标题后追加复制按钮 HTML。

当前代码（约第 122-131 行）：
```python
elif kind == 'section':
    result.append(f'<h2 class="r-section">{escape(g["text"])}</h2>')
...
result.append(f'<h3 class="r-subheading">{escape(m.group(1))}</h3>')
```

修改为在标题后追加复制按钮：
```python
elif kind == 'section':
    title = escape(g["text"])
    result.append(f'<div class="r-section-header"><h2 class="r-section">{title}</h2><button class="copy-btn" onclick="copyResult(this)" title="复制到剪贴板">📋</button></div>')
```

对 h3 子标题同样处理：
```python
result.append(f'<div class="r-subheading-header"><h3 class="r-subheading">{escape(m.group(1))}</h3><button class="copy-btn" onclick="copyResult(this)" title="复制到剪贴板">📋</button></div>')
```

同时处理 h1 标题：
```python
result.append(f'<div class="r-title-header"><h1 class="r-title">{escape(g["text"])}</h1><button class="copy-btn" onclick="copyResult(this)" title="复制到剪贴板">📋</button></div>')
```

- [ ] **Step 2: 在 app.js 末尾追加复制按钮逻辑**

```js
// ============================================================================
// 分析结果复制按钮
// ============================================================================

function copyResult(btn) {
    // 找到最近的父级 section 容器
    const header = btn.closest('.r-section-header, .r-subheading-header, .r-title-header');
    const container = header ? header.parentElement : btn.closest('.result-container, #result-content');
    if (!container) return;
    const text = container.innerText.trim();
    if (!text) return;
    navigator.clipboard.writeText(text).then(function() {
        const orig = btn.textContent;
        btn.textContent = '✓';
        setTimeout(function() { btn.textContent = orig; }, 1500);
    }).catch(function() {
        // fallback: 旧浏览器
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btn.textContent = '✓';
        setTimeout(function() { btn.textContent = '📋'; }, 1500);
    });
}
```

- [ ] **Step 3: 在 chat.css 或 terminal.css 追加复制按钮样式**

在 `chat.css` 末尾追加：

```css
/* 复制按钮 */
.copy-btn {
  background: none;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 4px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-xs);
  padding: 2px 6px;
  margin-left: 8px;
  transition: all var(--duration-fast) var(--ease-out-expo);
  flex-shrink: 0;
}
.copy-btn:hover {
  background: rgba(59, 130, 246, 0.10);
  border-color: rgba(59, 130, 246, 0.25);
  color: var(--accent-primary);
}
.r-section-header, .r-subheading-header, .r-title-header {
  display: flex;
  align-items: center;
}
```

- [ ] **Step 4: 运行测试并提交**

```bash
python -m pytest tests/ -q --ignore=tests/test_adapter.py
git add financial_analyzer/web/services/result_formatter.py financial_analyzer/web/static/js/app.js financial_analyzer/web/static/css/chat.css
git commit -m "feat: add copy button to analysis result section headers

Each h1/h2/h3 heading in analysis results now has a copy button that
copies the parent section text to clipboard with visual feedback.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: 数据导出合并

**Files:**
- Modify: `financial_analyzer/web/templates/base.html` (top-bar export buttons + modal HTML)
- Modify: `financial_analyzer/web/static/js/app.js` (export modal logic)
- Modify: `financial_analyzer/web/routes/export_api.py` (support categories parameter)

- [ ] **Step 1: 替换顶栏导出按钮**

在 `base.html` 的 `top-bar` 中，找到三个导出按钮（约第 96-98 行）：
```html
<button type="button" class="btn" onclick="exportData('xlsx')" title="导出 Excel">Excel</button>
<button type="button" class="btn" onclick="exportData('csv')" title="导出 CSV">CSV</button>
<button type="button" class="btn" onclick="exportData('json')" title="导出 JSON">JSON</button>
```

替换为：
```html
<button type="button" class="btn" onclick="openExportModal()">数据导出</button>
```

- [ ] **Step 2: 在 base.html 末尾追加导出弹窗 HTML**

在 `base.html` 的 `</body>` 前，追加导出弹窗：

```html
<!-- 数据导出弹窗 -->
<div class="viewer-overlay" id="export-modal-overlay">
    <div class="viewer-modal" style="width:min(480px,95vw);">
        <div class="viewer-header">
            <h3>导出数据</h3>
            <button class="prompt-editor-close" onclick="closeExportModal()">&times;</button>
        </div>
        <div class="viewer-body">
            <div class="viewer-section">
                <h4>导出内容</h4>
                <div id="export-categories"></div>
            </div>
            <div class="viewer-section">
                <h4>导出格式</h4>
                <div style="display:flex;gap:16px;padding:8px 0;">
                    <label style="color:var(--text-primary);cursor:pointer;">
                        <input type="radio" name="export-fmt" value="xlsx" checked> Excel (.xlsx)
                    </label>
                    <label style="color:var(--text-primary);cursor:pointer;">
                        <input type="radio" name="export-fmt" value="csv"> CSV (.csv)
                    </label>
                    <label style="color:var(--text-primary);cursor:pointer;">
                        <input type="radio" name="export-fmt" value="json"> JSON (.json)
                    </label>
                </div>
            </div>
        </div>
        <div class="viewer-footer">
            <button class="pe-btn-cancel" onclick="closeExportModal()">取消</button>
            <button class="pe-btn-save" onclick="doExport()">导出</button>
        </div>
    </div>
</div>
```

- [ ] **Step 3: 在 app.js 末尾追加导出弹窗 JS**

```js
// ============================================================================
// 数据导出弹窗
// ============================================================================

function openExportModal() {
    // 动态生成导出内容勾选项
    const container = document.getElementById('export-categories');
    container.innerHTML = '';

    // 从 session 获取可用数据类型（通过页面上的数据指示器或预设）
    var categories = [
        { key: 'income', label: '利润表' },
        { key: 'balance', label: '资产负债表' },
        { key: 'cashflow', label: '现金流量表' },
        { key: 'basic', label: '行情数据(日线)' },
    ];

    // 检查页面上哪些数据已加载
    var finStatus = document.getElementById('fin-status');
    if (finStatus && finStatus.dataset) {
        // 动态调整
    }

    categories.forEach(function(cat) {
        var label = document.createElement('label');
        label.style.cssText = 'display:flex;align-items:center;gap:8px;padding:4px 0;color:var(--text-primary);cursor:pointer;';
        label.innerHTML = '<input type="checkbox" name="export-cat" value="' + cat.key + '" checked> ' + cat.label;
        container.appendChild(label);
    });

    document.getElementById('export-modal-overlay').style.display = 'flex';
    requestAnimationFrame(function() {
        document.getElementById('export-modal-overlay').classList.add('modal--visible');
    });
}

function closeExportModal() {
    var overlay = document.getElementById('export-modal-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

function doExport() {
    var cats = [];
    document.querySelectorAll('input[name="export-cat"]:checked').forEach(function(cb) {
        cats.push(cb.value);
    });
    var fmt = document.querySelector('input[name="export-fmt"]:checked');
    var format = fmt ? fmt.value : 'xlsx';
    var stockCode = document.querySelector('input[name="stock_code"]')?.value || '';

    var url = '/export/' + format + '?stock_code=' + encodeURIComponent(stockCode);
    if (cats.length > 0) {
        url += '&categories=' + cats.join(',');
    }
    window.open(url, '_blank');
    closeExportModal();
}
```

- [ ] **Step 4: 修改 export_api.py 支持 categories 参数**

在 `export_data` 函数中，添加 `categories` 参数支持：

```python
@router.get("/{format}")
async def export_data(
    request: Request,
    format: str,
    stock_code: str = Query(""),
    categories: str = Query(""),
):
    session = _get_session(request)
    data_raw = session.get("data", {})
    sc = stock_code or session.get("stock_code", "")

    if not data_raw or not sc:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<p>无可导出数据</p>", status_code=400)

    # 如果指定了 categories，只导出选中的类别
    if categories:
        selected = [c.strip() for c in categories.split(",") if c.strip()]
        data_raw = {k: v for k, v in data_raw.items() if k in selected}

    if not data_raw:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<p>未选择导出内容</p>", status_code=400)

    data = {k: pd.DataFrame(v) for k, v in data_raw.items()}

    # ... 后续代码不变 ...
```

- [ ] **Step 5: 运行测试并提交**

```bash
python -m pytest tests/ -q --ignore=tests/test_adapter.py
git add financial_analyzer/web/templates/base.html financial_analyzer/web/static/js/app.js financial_analyzer/web/routes/export_api.py
git commit -m "feat: merge export buttons into single modal with data type selection

Replaced 3 export buttons (Excel/CSV/JSON) with one '数据导出' button.
Modal allows selecting data types (income/balance/cashflow/basic) and
export format. export_api now supports categories query parameter.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: 集成验证

**Files:** (none new — validation only)

- [ ] **Step 1: 运行全部测试确保无回归**

```bash
cd "C:/Users/LK/Desktop/FA/10.6"
python -m pytest tests/ -q --ignore=tests/test_adapter.py
```
Expected: 274 passed, 1 pre-existing failure

- [ ] **Step 2: 验证模块导入链路**

```bash
python -c "
from financial_analyzer.ai.orchestrator import AnalysisOrchestrator
from financial_analyzer.web.main import create_app
app = create_app()
print('All imports OK')
print('App created successfully')
"
```

- [ ] **Step 3: 验证简化后的 prompt 不注入额外内容**

```bash
python -c "
from financial_analyzer.ai.orchestrator import AnalysisOrchestrator

class FakeLLM:
    def __init__(self):
        self.last_prompt = None
        self.last_system = None
    def generate_deep_analysis_stream(self, prompt, system_prompt=None, callback=None):
        self.last_prompt = prompt
        self.last_system = system_prompt
        from financial_analyzer.deepseek.client import AnalysisReport
        r = AnalysisReport(); r.success = True; r.content = 'OK'; return r

fake = FakeLLM()
orchestrator = AnalysisOrchestrator(llm_client=fake)

# 模拟 quick 模式
orchestrator._stream_chat('PE是多少？', None, lambda *a: None)
assert fake.last_prompt == 'PE是多少？'
assert fake.last_system is None  # 无 system_prompt 注入
print('Quick mode: LLM receives only user message - PASS')

# 模拟 deep 模式（行为与 quick 一致）
orchestrator._stream_chat('深度分析盈利能力', None, lambda *a: None)
assert fake.last_prompt == '深度分析盈利能力'
assert fake.last_system is None
print('Deep mode: LLM receives only user message - PASS')
print('All simplification checks passed')
"
```

- [ ] **Step 4: 提交**

```bash
git commit --allow-empty -m "verify: AI simplification integration tests pass"
```
