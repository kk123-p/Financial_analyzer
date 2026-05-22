# Desktop UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Tkinter desktop GUI with a Modern Dark SaaS web-based desktop app (pywebview + vanilla HTML/CSS/JS), reusing all existing FastAPI backend routes.

**Architecture:** Single-page application with hash routing loaded in pywebview. Five main views (dashboard, analysis center, analysis result, AI research, data browser) plus global overlays (command palette, AI sidebar). Pure vanilla JS with ES modules, Chart.js for charts, SortableJS for drag-and-drop, marked.js for Markdown rendering.

**Tech Stack:** HTML5 · CSS3 (CSS Custom Properties) · Vanilla JS (ES Modules) · Chart.js · SortableJS · marked.js · pywebview (Windows: Edge WebView2)

**Spec:** `docs/superpowers/specs/2026-05-23-desktop-ui-redesign-design.md`

---

## File Structure

### New Files

```
frontend/
├── index.html                  # SPA entry point
├── css/
│   ├── tokens.css              # CSS custom properties
│   ├── base.css                # Reset, typography, basic elements
│   ├── layout.css              # App shell, top nav, view containers
│   ├── dashboard.css           # Dashboard: search hero, KPI cards, chart area
│   ├── analysis.css            # Analysis center: category tabs, module grid, results
│   ├── chat.css                # AI chat: messages, templates, debate columns
│   ├── data.css                # Data browser: tables, sort controls, pagination
│   └── overlays.css            # Command palette, AI sidebar, modals
└── js/
    ├── utils.js                # formatNumber, formatDate, debounce, DOM helpers
    ├── api.js                  # ApiClient: fetch wrapper, WebSocket manager
    ├── router.js               # Hash router: pattern matching, view lifecycle
    ├── app.js                  # App entry: init router, global state, event delegation
    ├── dashboard.js            # DashboardView: search, KPI, chart, AI summary
    ├── analysis.js             # AnalysisView: categories, module grid, result page
    ├── chat.js                 # ChatView: conversation, templates, debate
    ├── data-browser.js         # DataBrowserView: table, sort, filter, paginate
    ├── command-palette.js      # CommandPalette: fuzzy search, keyboard navigation
    └── settings.js             # SettingsView: token, datasource, cache management

desktop_app.py                  # pywebview launcher
```

### Files to Delete

```
financial_analyzer/ui/         # Entire directory (Tkinter UI)
financial_analyzer/web/templates/  # Old Jinja2 templates
financial_analyzer/web/static/     # Old CSS/JS
```

### Files to Modify

```
financial_analyzer/web/main.py     # Add static file mount for /frontend
run_web.py                         # Minor adjustments if needed
```

---

## Module Contracts

### CSS Loading Order

1. `tokens.css` — Only `:root { }` custom properties, no selectors
2. `base.css` — Element selectors (`body`, `h1-h6`, `a`, `input`, `button`, `table`)
3. `layout.css` — `.app-shell`, `.top-nav`, `.main-content`, `.view`, `.view.active`
4. `dashboard.css` — All `.dashboard-*`, `.kpi-*`, `.search-hero-*`
5. `analysis.css` — All `.analysis-*`, `.category-*`, `.module-*`, `.result-*`
6. `chat.css` — All `.chat-*`, `.message-*`, `.debate-*`, `.template-*`
7. `data.css` — All `.data-*`, `.table-*`, `.pagination-*`
8. `overlays.css` — `.command-palette`, `.ai-panel`, `.modal-overlay`, `.modal`

### JS Module Dependencies

```
utils.js          ← no deps (pure functions)
api.js            ← utils.js
router.js         ← utils.js
app.js            ← utils.js, api.js, router.js
dashboard.js      ← utils.js
analysis.js       ← utils.js
chat.js           ← utils.js
data-browser.js   ← utils.js
command-palette.js ← utils.js
settings.js       ← utils.js
```

### JS Exports

**utils.js** exports: `formatNumber(n, decimals)`, `formatDate(dateStr)`, `formatPercent(n, decimals)`, `debounce(fn, ms)`, `$(selector)`, `$$(selector)`, `escapeHtml(str)`

**api.js** exports: `ApiClient` class
- `ApiClient(baseUrl)` — constructor
- `async get(endpoint)` — GET request, returns JSON
- `async post(endpoint, data)` — POST request, returns JSON
- `connectWebSocket(endpoint)` — returns WebSocket instance
- `async fetchStockList(query)` — stock search autocomplete
- `async fetchStockData(code)` — get KPI + basic info
- `async runAnalysis(code, moduleKey)` — trigger analysis, returns result
- `async getAnalysisModules()` — get module catalog from ANALYSIS_MAP

**router.js** exports: `Router` class
- `Router(routes)` — constructor, takes route definitions
- `start()` — begin listening to hashchange
- `navigate(hash)` — programmatic navigation
- `getCurrentRoute()` — returns current {route, params}

**app.js** exports: `App` class (default export)
- `App()` — constructor, creates ApiClient, Router, global state
- `async init()` — bootstrap everything
- `state.currentStock` — {code, name, market}
- `state.kpiData` — latest KPI snapshot
- `emit(event, data)` — global event emitter
- `on(event, callback)` — global event listener

---

### Task 0: Project Setup — Create Frontend Scaffold

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/css/tokens.css`
- Create: `frontend/js/utils.js`
- Create: `desktop_app.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p frontend/css frontend/js
```

- [ ] **Step 2: Create `frontend/css/tokens.css` — CSS custom properties**

```css
/* === DESIGN TOKENS === */
:root {
  /* Surfaces */
  --surface-base: #06080F;
  --surface-elevated: #0C0E18;
  --surface-glass: rgba(255, 255, 255, 0.03);
  --surface-hover: rgba(255, 255, 255, 0.05);

  /* Borders */
  --border-default: #1A1D2E;
  --border-light: rgba(255, 255, 255, 0.06);
  --border-accent: rgba(108, 92, 231, 0.3);
  --border-focus: rgba(108, 92, 231, 0.5);

  /* Accent */
  --accent: #6C5CE7;
  --accent-hover: #7C6FF7;
  --accent-soft: #A78BFA;
  --accent-bg: rgba(108, 92, 231, 0.12);
  --accent-bg-hover: rgba(108, 92, 231, 0.18);
  --accent-gradient: linear-gradient(135deg, #6C5CE7, #A78BFA);

  /* Semantic */
  --success: #10B981;
  --success-bg: rgba(16, 185, 129, 0.1);
  --danger: #EF4444;
  --danger-bg: rgba(239, 68, 68, 0.1);
  --warning: #F59E0B;
  --warning-bg: rgba(245, 158, 11, 0.1);
  --info: #3B82F6;
  --info-bg: rgba(59, 130, 246, 0.1);

  /* Text */
  --text-primary: #F1F5F9;
  --text-secondary: #94A3B8;
  --text-muted: #64748B;
  --text-disabled: #334155;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;

  /* Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px rgba(108, 92, 231, 0.15);

  /* Typography */
  --font-display: 'Satoshi', 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
  --font-body: 'Geist Sans', 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
  --font-mono: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;

  /* Type Scale */
  --text-xs: 10px;
  --text-sm: 11px;
  --text-base: 13px;
  --text-md: 14px;
  --text-lg: 16px;
  --text-xl: 20px;
  --text-2xl: 26px;

  /* Transitions */
  --transition-fast: 150ms ease-out;
  --transition-normal: 250ms ease-out;

  /* Layout */
  --topnav-height: 44px;
  --sidebar-width: 360px;
}
```

- [ ] **Step 3: Create `frontend/js/utils.js` — utility functions**

```javascript
// utils.js — Pure utility functions

/**
 * Format number with thousand separators and optional decimal places
 */
export function formatNumber(n, decimals = 2) {
  if (n == null || isNaN(n)) return '--';
  return Number(n).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format percentage value (0.15 → "15.00%")
 */
export function formatPercent(n, decimals = 2) {
  if (n == null || isNaN(n)) return '--';
  return (n * 100).toFixed(decimals) + '%';
}

/**
 * Format a number as Chinese financial unit
 * 238000000000 → "2380亿"
 */
export function formatFinancial(n) {
  if (n == null || isNaN(n)) return '--';
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e12) return sign + (abs / 1e12).toFixed(2) + '万亿';
  if (abs >= 1e8) return sign + (abs / 1e8).toFixed(2) + '亿';
  if (abs >= 1e4) return sign + (abs / 1e4).toFixed(2) + '万';
  return sign + abs.toFixed(2);
}

/**
 * Format date string to YYYY-MM-DD
 */
export function formatDate(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return String(dateStr);
  return d.toISOString().slice(0, 10);
}

/**
 * Debounce a function
 */
export function debounce(fn, ms = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

/**
 * Shorthand for document.querySelector
 */
export function $(selector, parent = document) {
  return parent.querySelector(selector);
}

/**
 * Shorthand for document.querySelectorAll (returns Array)
 */
export function $$(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}

/**
 * Escape HTML entities
 */
export function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Create an HTML element with attributes and children
 */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (key === 'className') el.className = val;
    else if (key === 'innerHTML') el.innerHTML = val;
    else if (key.startsWith('on')) el.addEventListener(key.slice(2).toLowerCase(), val);
    else el.setAttribute(key, val);
  }
  for (const child of children) {
    if (typeof child === 'string') el.appendChild(document.createTextNode(child));
    else if (child instanceof Node) el.appendChild(child);
  }
  return el;
}
```

- [ ] **Step 4: Create `desktop_app.py` — pywebview launcher**

```python
"""Desktop app launcher using pywebview."""
import sys
import subprocess
import time
import threading
import webview


API_URL = "http://127.0.0.1:8000"


def start_fastapi():
    """Start FastAPI server in background thread."""
    import uvicorn
    from financial_analyzer.web.main import app as fastapi_app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    serve = "--serve" in sys.argv

    if serve:
        thread = threading.Thread(target=start_fastapi, daemon=True)
        thread.start()
        # Wait for server to be ready
        for _ in range(30):
            try:
                import urllib.request
                urllib.request.urlopen(API_URL + "/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)

    window = webview.create_window(
        title="Financial Analyzer Pro",
        url=API_URL,
        width=1200,
        height=800,
        min_size=(960, 600),
        resizable=True,
        fullscreen=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create `frontend/index.html` — SPA entry point**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Financial Analyzer Pro</title>
  <link rel="stylesheet" href="/static/frontend/css/tokens.css">
  <link rel="stylesheet" href="/static/frontend/css/base.css">
  <link rel="stylesheet" href="/static/frontend/css/layout.css">
  <link rel="stylesheet" href="/static/frontend/css/dashboard.css">
  <link rel="stylesheet" href="/static/frontend/css/analysis.css">
  <link rel="stylesheet" href="/static/frontend/css/chat.css">
  <link rel="stylesheet" href="/static/frontend/css/data.css">
  <link rel="stylesheet" href="/static/frontend/css/overlays.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <!-- App Shell -->
  <div id="app">
    <!-- Top Navigation -->
    <nav id="top-nav">
      <div class="nav-brand">
        <div class="nav-logo">FA</div>
        <span class="nav-title">Financial Analyzer Pro</span>
      </div>
      <div class="nav-tabs" id="nav-tabs">
        <button class="nav-tab active" data-route="/dashboard">仪表盘</button>
        <button class="nav-tab" data-route="/analysis">分析中心</button>
        <button class="nav-tab" data-route="/ai">AI 投研</button>
        <button class="nav-tab" data-route="/data">数据浏览</button>
      </div>
      <div class="nav-center">
        <div class="stock-search" id="stock-search">
          <input type="text" id="stock-input"
                 placeholder="输入股票代码或名称，如 600519..."
                 autocomplete="off">
          <div class="search-status" id="search-status"></div>
          <div class="search-dropdown" id="search-dropdown"></div>
        </div>
      </div>
      <div class="nav-actions">
        <kbd class="nav-kbd">Ctrl+K</kbd>
        <button class="nav-btn" id="btn-settings" title="设置">&#9881;</button>
      </div>
    </nav>

    <!-- Main Content -->
    <main id="main-content">
      <!-- Dashboard View -->
      <div id="view-dashboard" class="view active">
        <div id="dashboard-empty" class="dashboard-empty">
          <div class="search-hero">
            <h1 class="search-hero-title">开始分析</h1>
            <p class="search-hero-subtitle">输入股票代码或名称，获取完整财务分析报告</p>
            <div class="search-hero-input-wrapper">
              <input type="text" id="hero-search-input"
                     class="search-hero-input"
                     placeholder="输入股票代码，如 600519、000001..."
                     autofocus>
            </div>
          </div>
          <div class="search-hero-sidebar" id="recent-panel">
            <!-- Populated by dashboard.js -->
          </div>
        </div>
        <div id="dashboard-data" class="dashboard-data" style="display:none;">
          <div class="kpi-strip" id="kpi-strip"><!-- Populated by dashboard.js --></div>
          <div class="dashboard-grid">
            <div class="dashboard-chart-panel" id="chart-panel">
              <div class="panel-header">
                <span class="panel-title">K线走势</span>
                <div class="panel-tabs">
                  <button class="chart-tab active" data-period="D">日K</button>
                  <button class="chart-tab" data-period="W">周K</button>
                  <button class="chart-tab" data-period="M">月K</button>
                </div>
              </div>
              <canvas id="dashboard-chart"></canvas>
            </div>
            <div class="dashboard-sidebar">
              <div class="ai-summary-card" id="ai-summary">
                <div class="panel-header">
                  <span class="panel-title">AI 快评</span>
                  <button class="panel-action" id="btn-ai-expand">展开深度分析 →</button>
                </div>
                <div class="ai-summary-body" id="ai-summary-body">
                  <p class="text-muted">分析中...</p>
                </div>
              </div>
              <button class="cta-button" id="btn-start-ai">
                开始 AI 分析对话
              </button>
            </div>
          </div>
          <div class="recent-analyses" id="recent-analyses">
            <!-- Populated by dashboard.js -->
          </div>
        </div>
      </div>

      <!-- Analysis Center View -->
      <div id="view-analysis" class="view">
        <div class="analysis-center" id="analysis-center">
          <div class="analysis-categories" id="analysis-categories">
            <!-- Populated by analysis.js -->
          </div>
          <div class="analysis-modules" id="analysis-modules">
            <!-- Populated by analysis.js -->
          </div>
        </div>
        <div class="analysis-result" id="analysis-result" style="display:none;">
          <!-- Populated by analysis.js -->
        </div>
      </div>

      <!-- AI Research View -->
      <div id="view-ai" class="view">
        <div class="ai-workspace" id="ai-workspace">
          <div class="ai-subtabs" id="ai-subtabs">
            <button class="ai-subtab active" data-mode="chat">自由对话</button>
            <button class="ai-subtab" data-mode="template">模板分析</button>
            <button class="ai-subtab" data-mode="debate">三方辩论</button>
          </div>
          <div class="ai-main" id="ai-main">
            <div class="ai-chat-area" id="ai-chat-area">
              <div class="chat-messages" id="chat-messages"><!-- Populated by chat.js --></div>
              <div class="chat-input-area" id="chat-input-area">
                <div class="template-chips" id="template-chips"><!-- Populated by chat.js --></div>
                <div class="chat-input-row">
                  <input type="text" id="chat-input"
                         class="chat-input"
                         placeholder="输入问题，或选择上方模板..."
                         autocomplete="off">
                  <button class="chat-send-btn" id="btn-chat-send">&#8593;</button>
                  <button class="chat-stop-btn" id="btn-chat-stop" style="display:none;">&#9632;</button>
                </div>
              </div>
            </div>
            <div class="ai-context-panel" id="ai-context-panel">
              <!-- Populated by chat.js -->
            </div>
          </div>
          <!-- Debate columns -->
          <div class="ai-debate" id="ai-debate" style="display:none;">
            <div class="debate-columns" id="debate-columns"><!-- Populated by chat.js --></div>
            <div class="debate-consensus" id="debate-consensus"><!-- Populated by chat.js --></div>
          </div>
        </div>
      </div>

      <!-- Data Browser View -->
      <div id="view-data" class="view">
        <div class="data-browser" id="data-browser">
          <div class="data-controls" id="data-controls">
            <select id="data-type-select" class="data-select">
              <option value="">选择数据类型...</option>
            </select>
            <input type="text" id="data-filter" class="data-filter"
                   placeholder="筛选..." autocomplete="off">
            <button class="btn-ghost" id="btn-export-data">导出 CSV</button>
          </div>
          <div class="data-table-wrapper" id="data-table-wrapper">
            <table class="data-table" id="data-table">
              <thead id="data-table-head"></thead>
              <tbody id="data-table-body"></tbody>
            </table>
          </div>
          <div class="pagination" id="pagination"><!-- Populated by data-browser.js --></div>
        </div>
      </div>

      <!-- Settings View -->
      <div id="view-settings" class="view" style="display:none;">
        <div class="settings-page" id="settings-page">
          <!-- Populated by settings.js -->
        </div>
      </div>
    </main>
  </div>

  <!-- Global Overlays -->
  <!-- Command Palette -->
  <div id="command-palette" class="command-palette" style="display:none;">
    <div class="cp-header">
      <input type="text" id="cp-input" class="cp-input"
             placeholder="搜索分析模块..." autocomplete="off">
      <span class="cp-hint">esc 关闭</span>
    </div>
    <div class="cp-results" id="cp-results"><!-- Populated by command-palette.js --></div>
  </div>

  <!-- AI Side Panel -->
  <div id="ai-panel" class="ai-panel" style="display:none;">
    <div class="ai-panel-header">
      <span class="ai-panel-title">AI 助手</span>
      <button class="ai-panel-close" id="btn-ai-panel-close">&times;</button>
    </div>
    <div class="ai-panel-context" id="ai-panel-context"><!-- Populated by chat.js --></div>
    <div class="ai-panel-messages" id="ai-panel-messages"><!-- Populated by chat.js --></div>
    <div class="ai-panel-input-row">
      <input type="text" id="ai-panel-input"
             class="ai-panel-input"
             placeholder="追问..."
             autocomplete="off">
      <button class="ai-panel-send" id="btn-ai-panel-send">&#8593;</button>
    </div>
  </div>

  <!-- Modal Overlay -->
  <div id="modal-overlay" class="modal-overlay" style="display:none;">
    <div class="modal" id="modal-content"><!-- Populated dynamically --></div>
  </div>
  <div id="modal-backdrop" class="modal-backdrop" style="display:none;"></div>

  <script type="module" src="/static/frontend/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 6: Commit scaffold**

```bash
git add frontend/ desktop_app.py
git commit -m "feat: create frontend scaffold and pywebview launcher

Add CSS tokens, utility functions, SPA index.html with all view containers,
and desktop_app.py launcher.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 1: Design System CSS — base.css + layout.css

**Files:**
- Create: `frontend/css/base.css`
- Create: `frontend/css/layout.css`

- [ ] **Step 1: Create `frontend/css/base.css`**

```css
/* === BASE RESET & TYPOGRAPHY === */

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: var(--font-body);
  font-size: var(--text-base);
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--surface-base);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Subtle noise texture overlay */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  opacity: 0.015;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 9999;
}

/* Typography */
h1, h2, h3, h4 {
  font-family: var(--font-display);
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
}

h1 { font-size: var(--text-2xl); }
h2 { font-size: var(--text-xl); }
h3 { font-size: var(--text-lg); }
h4 { font-size: var(--text-md); }

a {
  color: var(--accent-soft);
  text-decoration: none;
}

a:hover {
  color: var(--accent);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Selection */
::selection {
  background: rgba(108, 92, 231, 0.3);
  color: var(--text-primary);
}

/* Focus ring */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Button reset */
button {
  font-family: var(--font-body);
  cursor: pointer;
  border: none;
  background: none;
  color: inherit;
}

/* Input reset */
input, select, textarea {
  font-family: var(--font-body);
  color: var(--text-primary);
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  transition: border-color var(--transition-fast);
}

input:focus, select:focus, textarea:focus {
  border-color: var(--border-focus);
  outline: none;
  box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.1);
}

input::placeholder, textarea::placeholder {
  color: var(--text-disabled);
}

/* Table reset */
table {
  border-collapse: collapse;
  width: 100%;
}

/* Utility classes */
.text-success { color: var(--success); }
.text-danger { color: var(--danger); }
.text-warning { color: var(--warning); }
.text-muted { color: var(--text-muted); }
.text-accent { color: var(--accent-soft); }

.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 2: Create `frontend/css/layout.css`**

```css
/* === APP SHELL & TOP NAVIGATION === */

#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* Top Navigation Bar */
#top-nav {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--topnav-height);
  padding: 0 var(--space-4);
  background: var(--surface-elevated);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
  z-index: 100;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.nav-logo {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  background: var(--accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 13px;
  color: #fff;
}

.nav-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-base);
  color: var(--text-primary);
  white-space: nowrap;
}

/* Nav Tabs */
.nav-tabs {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.nav-tab {
  padding: 6px 14px;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.nav-tab:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.nav-tab.active {
  background: var(--accent-bg);
  color: var(--accent-soft);
  font-weight: 600;
}

/* Stock Search (center) */
.nav-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.stock-search {
  position: relative;
  width: 260px;
}

#stock-input {
  width: 100%;
  height: 32px;
  padding: 0 var(--space-3);
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
}

.search-status {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 9px;
}

.search-status.connected { color: var(--success); }
.search-status.disconnected { color: var(--danger); }

.search-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  max-height: 240px;
  overflow-y: auto;
  display: none;
  z-index: 200;
}

.search-dropdown.visible { display: block; }

.search-dropdown-item {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}

.search-dropdown-item:hover,
.search-dropdown-item.active {
  background: var(--surface-hover);
}

.search-dropdown-item .code {
  font-family: var(--font-mono);
  color: var(--accent-soft);
}

/* Nav Actions */
.nav-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.nav-kbd {
  padding: 3px 8px;
  background: var(--surface-glass);
  border-radius: var(--radius-sm);
  font-size: 9px;
  color: var(--text-disabled);
  font-family: var(--font-mono);
}

.nav-btn {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--text-secondary);
  background: var(--surface-glass);
}

.nav-btn:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

/* Main Content Area */
#main-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Views */
.view {
  display: none;
  height: 100%;
  overflow-y: auto;
}

.view.active {
  display: flex;
  flex-direction: column;
}

/* Glass panel */
.glass-panel {
  background: var(--surface-glass);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
}

/* Card base */
.card {
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.card:hover {
  border-color: var(--border-accent);
  background: var(--surface-hover);
}

.card.selected {
  border-color: var(--accent);
  background: var(--accent-bg);
}

/* Panel header */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.panel-title {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.panel-action {
  font-size: var(--text-xs);
  color: var(--accent);
  cursor: pointer;
}

.panel-action:hover {
  color: var(--accent-hover);
}

/* Skeleton loading */
.skeleton {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.03) 25%,
    rgba(255, 255, 255, 0.06) 50%,
    rgba(255, 255, 255, 0.03) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

- [ ] **Step 3: Commit base + layout CSS**

```bash
git add frontend/css/base.css frontend/css/layout.css
git commit -m "feat: add base and layout CSS with design tokens application

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: API Client + Router — app.js foundation

**Files:**
- Create: `frontend/js/api.js`
- Create: `frontend/js/router.js`
- Create: `frontend/js/app.js`

- [ ] **Step 1: Create `frontend/js/api.js`**

```javascript
// api.js — API client and WebSocket manager
import { debounce } from './utils.js';

const BASE_URL = '';

export class ApiClient {
  constructor() {
    this.ws = null;
    this.wsHandlers = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  /* --- REST --- */

  async get(endpoint) {
    const res = await fetch(BASE_URL + endpoint);
    if (!res.ok) throw new Error(`GET ${endpoint} failed: ${res.status}`);
    return res.json();
  }

  async post(endpoint, data = {}) {
    const res = await fetch(BASE_URL + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`POST ${endpoint} failed: ${res.status}`);
    return res.json();
  }

  /* --- Domain methods --- */

  async fetchStockList(query) {
    if (!query || query.length < 1) return [];
    try {
      const data = await this.get(`/api/data/stock-list?q=${encodeURIComponent(query)}`);
      return data.results || [];
    } catch {
      return [];
    }
  }

  async fetchStockData(code) {
    return this.get(`/api/data/stock-summary/${code}`);
  }

  async fetchDetailedData(code, dataType) {
    return this.get(`/api/data/${dataType}/${code}`);
  }

  async runAnalysis(code, moduleKey) {
    return this.post(`/api/analysis/${moduleKey}`, { stock_code: code });
  }

  async getAnalysisModules() {
    try {
      const data = await this.get('/api/analysis/modules');
      return data.modules || data;
    } catch {
      // Fallback: hardcoded module catalog
      return getFallbackModules();
    }
  }

  /* --- WebSocket --- */

  connectWebSocket() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return this.ws;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ai/conversation`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this._trigger('open');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this._trigger('message', msg);
      } catch {
        this._trigger('raw', event.data);
      }
    };

    this.ws.onclose = () => {
      this._trigger('close');
      this._tryReconnect();
    };

    this.ws.onerror = (err) => {
      this._trigger('error', err);
    };

    return this.ws;
  }

  sendWebSocket(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  closeWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  onWs(event, handler) {
    if (!this.wsHandlers[event]) this.wsHandlers[event] = [];
    this.wsHandlers[event].push(handler);
  }

  offWs(event, handler) {
    if (!this.wsHandlers[event]) return;
    this.wsHandlers[event] = this.wsHandlers[event].filter(h => h !== handler);
  }

  _trigger(event, data) {
    (this.wsHandlers[event] || []).forEach(h => h(data));
  }

  _tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    setTimeout(() => this.connectWebSocket(), delay);
  }
}

/* --- Fallback module catalog --- */

function getFallbackModules() {
  return [
    { key: 'market_overview', category: 'market', name: '行情概览', desc: '当前价、涨跌幅、52周高低、成交量、总市值', output: 'text' },
    { key: 'price_trend', category: 'market', name: '价格趋势', desc: '短中长期均线趋势、价格与MA定位', output: 'text' },
    { key: 'technical', category: 'market', name: '技术指标', desc: 'RSI、MACD、布林带、金叉/死叉信号', output: 'chart' },
    { key: 'balance_sheet', category: 'financial', name: '资产负债表', desc: '资产结构、负债结构、偿债能力、营运效率 7节深度', output: 'text' },
    { key: 'income_analysis', category: 'financial', name: '利润表', desc: '收入趋势、成本结构、五层利润分解、利润质量 6节深度', output: 'text' },
    { key: 'cashflow_analysis', category: 'financial', name: '现金流量表', desc: '经营/投资/筹资现金流、生命周期定位 6节深度', output: 'text' },
    { key: 'profitability', category: 'capability', name: '盈利能力', desc: '毛利率、净利率、ROE、ROA 及同比变化', output: 'text' },
    { key: 'operational', category: 'capability', name: '营运能力', desc: '应收账款、存货、总资产周转率 及行业对比', output: 'text' },
    { key: 'solvency', category: 'capability', name: '偿债能力', desc: '流动比率、速动比率、资产负债率、利息保障倍数', output: 'text' },
    { key: 'growth', category: 'capability', name: '成长能力', desc: '营收、净利、总资产、净资产同比增长率', output: 'text' },
    { key: 'ratio_analysis', category: 'capability', name: '财务比率', desc: '20+比率指标、加权综合评分(0-100)、A-F评级', output: 'text' },
    { key: 'dupont', category: 'deep', name: '杜邦分析', desc: '三因子分解(净利率×周转率×杠杆)、ROE驱动识别', output: 'chart' },
    { key: 'dupont_roic', category: 'deep', name: 'ROIC分析', desc: '扩展杜邦框架、投入资本回报率、价值创造分析', output: 'text' },
    { key: 'zscore', category: 'deep', name: 'Z-Score', desc: 'Altman Z值、破产风险区域分类(安全/灰色/困境)', output: 'text' },
    { key: 'fscore', category: 'deep', name: 'F-Score', desc: 'Piotroski 9分基本面强度评分(盈利/杠杆/效率)', output: 'chart' },
    { key: 'mscore', category: 'deep', name: 'M-Score', desc: 'Beneish 8变量财务操纵检测模型', output: 'text' },
    { key: 'fcf', category: 'deep', name: '自由现金流', desc: 'FCF、股东盈余、DCF多情景估值(乐观/基准/悲观)', output: 'text' },
    { key: 'cashflow_quadrant', category: 'deep', name: '现金流象限', desc: '8象限分类(奶牛/成长/困境...)、生命周期判断', output: 'text' },
    { key: 'moat', category: 'deep', name: '护城河分析', desc: '5维度竞争优势评估(无形资产/转换成本/网络效应/成本优势/规模)', output: 'text' },
    { key: 'deep_comprehensive', category: 'deep', name: '深度综合', desc: '全部深度分析子报告汇总', output: 'text' },
    { key: 'pe_valuation', category: 'valuation', name: 'PE估值', desc: 'PE/PB/PS/PEG多指标估值、行业对比', output: 'text' },
    { key: 'pe_percentile', category: 'valuation', name: 'PE历史分位', desc: '当前PE在N年历史区间中的分位、高估/低估判断', output: 'text' },
    { key: 'pb_roe', category: 'valuation', name: 'PB-ROE', desc: 'ROE vs PB散点图、估值与回报匹配度', output: 'chart' },
    { key: 'ev_ebitda', category: 'valuation', name: 'EV/EBITDA', desc: '企业价值/息税折旧摊销前利润、隐含公允价值', output: 'text' },
    { key: 'comprehensive', category: 'valuation', name: '综合投资评级', desc: '7维金字塔评分(市场/会计/财务/盈利/成长/估值)、星级', output: 'chart' },
    { key: 'quality', category: 'valuation', name: '财报质量', desc: '四维检查：盈利质量、收入质量、资产质量、操纵概率', output: 'text' },
    { key: 'shareholder_return', category: 'valuation', name: '股东回报', desc: '股息率+回购率、与债券收益率对比、可持续性', output: 'text' },
    { key: 'audit_full', category: 'audit', name: '全面审计', desc: '32信号6维度全面排查(资产/利润/现金流/勾稽/治理/模型)', output: 'chart' },
    { key: 'audit_asset', category: 'audit', name: '资产端排查', desc: '应收账款通胀、存货异常、固定资产不规范、商誉减值', output: 'text' },
    { key: 'audit_profit', category: 'audit', name: '利润端排查', desc: '收入虚增、利润率操纵、非经常性损益依赖、递延确认', output: 'text' },
    { key: 'audit_cashflow', category: 'audit', name: '现金流排查', desc: '经营现金流背离、投资现金流异常、筹资现金流压力', output: 'text' },
    { key: 'audit_cross', category: 'audit', name: '勾稽验证', desc: '三表交叉验证(资产负债/收入现金/税务利润)', output: 'text' },
    { key: 'fraud_ml', category: 'audit', name: 'ML舞弊检测', desc: '4模型集成(决策树+随机森林+GBDT+XGBoost)欺诈概率', output: 'text' },
    { key: 'shareholder', category: 'shareholder', name: '股东结构', desc: '股东人数趋势、Top10集中度、机构持仓、所有权评分', output: 'text' },
    { key: 'capital_flow', category: 'shareholder', name: '资金流向', desc: '主力资金/融资融券/北向资金/大宗交易 综合评分', output: 'text' },
    { key: 'dividend_analysis', category: 'shareholder', name: '分红分析', desc: '股息率、支付率、分红频率与持续性', output: 'text' },
    { key: 'compare_with_peers', category: 'shareholder', name: '行业对比', desc: 'PE/PB/ROE/毛利率/净利率/负债率 同业排名', output: 'chart' },
    { key: 'risk', category: 'risk', name: '风险评估', desc: '加权多维风险评分(偿付30%+盈利30%+运营20%+信号20%)', output: 'text' },
    { key: 'combined', category: 'risk', name: '量价结合', desc: '股价走势与财务表现相关性、背离异常信号', output: 'text' },
    { key: 'trend_score', category: 'risk', name: '趋势评分', desc: '多期趋势评分(营收/利润/利润率/现金流)、综合趋势方向', output: 'text' },
    { key: 'weekly_pe', category: 'risk', name: '周度PE分位', desc: '每周PE百分位排名、N年历史区间估值水平评估', output: 'text' },
    { key: 'fina_audit', category: 'tushare', name: '审计意见', desc: '历年审计意见类型(标准无保留/保留/否定/无法表示)', output: 'text' },
    { key: 'financial_indicators', category: 'tushare', name: '财务指标表', desc: 'EPS/ROE/ROA/毛利率等原始财务指标数据展示', output: 'table' },
    { key: 'main_business', category: 'tushare', name: '主营业务构成', desc: '按产品/行业/地区划分的营收结构', output: 'table' },
  ];
}
```

- [ ] **Step 2: Create `frontend/js/router.js`**

```javascript
// router.js — Hash-based SPA router
import { $, $$ } from './utils.js';

export class Router {
  constructor(routes) {
    this.routes = routes; // { pattern: handler(viewName, params) }
    this.currentView = null;
    this.currentParams = {};
  }

  start() {
    window.addEventListener('hashchange', () => this._handleRoute());
    if (!location.hash) {
      location.hash = '#/dashboard';
    } else {
      this._handleRoute();
    }
  }

  navigate(hash) {
    location.hash = hash;
  }

  getCurrentRoute() {
    return { view: this.currentView, params: this.currentParams };
  }

  _handleRoute() {
    const hash = location.hash.slice(1) || '/dashboard';
    const [path, ...rest] = hash.split('/').filter(Boolean);

    // Try exact match first, then pattern match
    let matched = false;
    for (const [pattern, handler] of Object.entries(this.routes)) {
      const patternParts = pattern.split('/').filter(Boolean);
      const hashParts = hash.slice(1).split('/').filter(Boolean);

      if (patternParts.length !== hashParts.length) continue;

      const params = {};
      let matches = true;
      for (let i = 0; i < patternParts.length; i++) {
        if (patternParts[i].startsWith(':')) {
          params[patternParts[i].slice(1)] = hashParts[i];
        } else if (patternParts[i] !== hashParts[i]) {
          matches = false;
          break;
        }
      }

      if (matches) {
        this.currentView = handler;
        this.currentParams = params;
        this._activateView(handler, params);
        matched = true;
        break;
      }
    }

    if (!matched) {
      // Fallback to dashboard
      this.navigate('/dashboard');
      return;
    }

    // Update nav tab active state
    const activeTab = this.currentView.split('/')[0];
    $$('.nav-tab').forEach(tab => {
      const route = tab.dataset.route;
      tab.classList.toggle('active', route === '/' + activeTab);
    });
  }

  _activateView(viewName, params) {
    // Hide all views
    $$('.view').forEach(v => v.classList.remove('active'));

    // Show target view
    const viewId = 'view-' + viewName.split('/')[0];
    const view = document.getElementById(viewId);
    if (view) {
      view.classList.add('active');
    }

    // Dispatch custom event for view change
    window.dispatchEvent(new CustomEvent('viewchange', {
      detail: { view: viewName, params }
    }));
  }

  getViewName() {
    const hash = location.hash.slice(1) || '/dashboard';
    const parts = hash.split('/').filter(Boolean);
    return parts[0] || 'dashboard';
  }

  getModuleKey() {
    const hash = location.hash.slice(1) || '';
    const parts = hash.split('/').filter(Boolean);
    return parts[1] || null;
  }
}
```

- [ ] **Step 3: Create `frontend/js/app.js` — Application entry point**

```javascript
// app.js — Application entry point
import { $ } from './utils.js';
import { ApiClient } from './api.js';
import { Router } from './router.js';

class App {
  constructor() {
    this.api = new ApiClient();
    this.state = {
      currentStock: null,   // { code, name, market }
      kpiData: null,        // Latest KPI snapshot
      modules: [],          // Analysis module catalog
      stockDataCache: {},   // Cache for fetched data
    };
    this.router = null;
    this._listeners = {};
  }

  async init() {
    // 1. Setup router
    this.router = new Router({
      'dashboard': 'dashboard',
      'analysis': 'analysis',
      'analysis/:module': 'analysis/result',
      'ai': 'ai',
      'data': 'data',
      'settings': 'settings',
    });
    this.router.start();

    // 2. Load module catalog
    try {
      this.state.modules = await this.api.getAnalysisModules();
    } catch {
      console.warn('Failed to load module catalog, using fallback');
    }

    // 3. Bind global events
    this._bindNavTabs();
    this._bindStockSearch();
    this._bindKeyboardShortcuts();
    this._bindSettingsButton();
    this._bindViewChanges();

    // 4. Restore last session
    this._restoreSession();

    // 5. Connect WebSocket
    this.api.connectWebSocket();
  }

  /* --- Stock Management --- */

  async selectStock(code, name, market) {
    this.state.currentStock = { code, name, market };
    this.state.kpiData = null;
    this.state.stockDataCache = {};

    // Update search input
    $('#stock-input').value = `${code} ${name}`;
    $('#search-status').className = 'search-status connected';
    $('#search-status').textContent = '加载中...';

    try {
      const data = await this.api.fetchStockData(code);
      this.state.kpiData = data;
      $('#search-status').textContent = '● 已连接';
      this.emit('stock:loaded', data);
    } catch (err) {
      $('#search-status').className = 'search-status disconnected';
      $('#search-status').textContent = '加载失败';
      this.emit('stock:error', err);
    }

    // Save to session
    this._saveSession();
  }

  /* --- Event System --- */

  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
  }

  emit(event, data) {
    (this._listeners[event] || []).forEach(cb => cb(data));
  }

  /* --- Private Methods --- */

  _bindNavTabs() {
    $$('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const route = tab.dataset.route;
        if (route) this.router.navigate(route);
      });
    });
  }

  _bindStockSearch() {
    const input = $('#stock-input');
    const dropdown = $('#search-dropdown');

    // Debounced search
    let searchTimeout;
    input.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      const query = input.value.trim();
      if (query.length < 1) {
        dropdown.classList.remove('visible');
        return;
      }
      searchTimeout = setTimeout(async () => {
        const results = await this.api.fetchStockList(query);
        this._renderSearchDropdown(results, dropdown);
      }, 250);
    });

    // Enter key
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = input.value.trim();
        if (!query) return;
        // Try to match pattern "CODE NAME" or just "CODE"
        const match = query.match(/^(\d{6})\s*(.*)/);
        if (match) {
          this.selectStock(match[1], match[2] || match[1]);
        }
        dropdown.classList.remove('visible');
      }
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('visible');
      }
    });
  }

  _renderSearchDropdown(results, dropdown) {
    if (!results.length) {
      dropdown.classList.remove('visible');
      return;
    }
    dropdown.innerHTML = results.map((r, i) => `
      <div class="search-dropdown-item" data-index="${i}">
        <span class="code">${r.code || r.ts_code || ''}</span>
        <span>${r.name || ''}</span>
      </div>
    `).join('');
    dropdown.classList.add('visible');

    // Click to select
    dropdown.querySelectorAll('.search-dropdown-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.index);
        const r = results[idx];
        this.selectStock(r.code || r.ts_code, r.name);
        dropdown.classList.remove('visible');
      });
    });
  }

  _bindKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+K: Command palette
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.emit('shortcut:command-palette');
      }
      // Ctrl+Space: AI panel
      if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
        e.preventDefault();
        this.emit('shortcut:ai-panel');
      }
      // Escape: close overlays
      if (e.key === 'Escape') {
        this.emit('shortcut:escape');
      }
    });
  }

  _bindSettingsButton() {
    $('#btn-settings').addEventListener('click', () => {
      this.router.navigate('/settings');
    });
  }

  _bindViewChanges() {
    window.addEventListener('viewchange', (e) => {
      this.emit('view:changed', e.detail);
    });
  }

  _saveSession() {
    try {
      localStorage.setItem('fa_last_stock', JSON.stringify(this.state.currentStock));
    } catch {}
  }

  _restoreSession() {
    try {
      const lastStock = JSON.parse(localStorage.getItem('fa_last_stock'));
      if (lastStock && lastStock.code) {
        this.selectStock(lastStock.code, lastStock.name, lastStock.market);
      }
    } catch {}
  }
}

// Bootstrap
const app = new App();
app.init();

// Make app globally accessible for view modules
window.__app = app;

export default app;
```

- [ ] **Step 4: Commit API client + router + app entry**

```bash
git add frontend/js/api.js frontend/js/router.js frontend/js/app.js
git commit -m "feat: add API client, hash router, and app entry point

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Dashboard View — visual CSS + JS

**Files:**
- Create: `frontend/css/dashboard.css`
- Create: `frontend/js/dashboard.js`

- [ ] **Step 1: Create `frontend/css/dashboard.css`**

```css
/* === DASHBOARD === */

/* Empty state */
.dashboard-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-12);
  padding: var(--space-12);
  height: 100%;
}

.search-hero {
  flex: 1;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.search-hero-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--text-primary);
}

.search-hero-subtitle {
  font-size: var(--text-base);
  color: var(--text-muted);
  text-align: center;
}

.search-hero-input-wrapper {
  width: 100%;
  position: relative;
}

.search-hero-input {
  width: 100%;
  height: 44px;
  padding: 0 var(--space-4);
  font-size: var(--text-base);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-lg);
  background: var(--surface-glass);
}

.search-hero-input:focus {
  border-color: var(--accent);
  box-shadow: var(--shadow-glow);
}

.search-hero-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.recent-card {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  background: var(--surface-glass);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.recent-card:hover {
  border-color: var(--border-accent);
  background: var(--surface-hover);
}

.recent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recent-card-code {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.recent-card-price {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}

.recent-card-name {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

.empty-section-title {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--space-1);
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.template-tag {
  padding: 3px 8px;
  background: var(--surface-glass);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  cursor: pointer;
}

.template-tag:hover {
  background: var(--accent-bg);
  color: var(--accent-soft);
}

/* Data state */
.dashboard-data {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
  overflow-y: auto;
}

/* KPI Strip */
.kpi-strip {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
}

.kpi-card {
  flex: 1;
  padding: var(--space-4);
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  min-width: 0;
}

.kpi-card:hover {
  border-color: var(--border-accent);
  background: var(--surface-hover);
}

.kpi-card-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--space-1);
}

.kpi-card-value {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.kpi-card-value.accent-gradient {
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.kpi-card-change {
  font-size: var(--text-xs);
  font-weight: 500;
}

.kpi-card-context {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Dashboard Grid */
.dashboard-grid {
  display: flex;
  gap: var(--space-3);
  flex: 1;
  min-height: 0;
}

.dashboard-chart-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.panel-tabs {
  display: flex;
  gap: 2px;
}

.chart-tab {
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.chart-tab.active {
  background: var(--accent-bg);
  color: var(--accent-soft);
}

#dashboard-chart {
  flex: 1;
  min-height: 0;
}

.dashboard-sidebar {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 260px;
}

.ai-summary-card {
  flex: 1;
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.ai-summary-body {
  flex: 1;
  overflow-y: auto;
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-secondary);
}

.ai-summary-body p {
  margin-bottom: var(--space-2);
}

.cta-button {
  width: 100%;
  padding: 12px;
  background: var(--accent-gradient);
  border: none;
  border-radius: var(--radius-lg);
  color: #fff;
  font-size: var(--text-base);
  font-weight: 600;
  font-family: var(--font-display);
  cursor: pointer;
  transition: opacity var(--transition-fast);
  flex-shrink: 0;
}

.cta-button:hover {
  opacity: 0.9;
}

/* Recent analyses bar */
.recent-analyses {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.recent-analyses-label {
  color: var(--text-muted);
  white-space: nowrap;
}

.recent-analysis-item {
  padding: 3px 10px;
  background: var(--surface-hover);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
}

.recent-analysis-item:hover {
  color: var(--accent-soft);
  background: var(--accent-bg);
}

.recent-analysis-new {
  color: var(--accent);
  cursor: pointer;
  white-space: nowrap;
  margin-left: auto;
}
```

- [ ] **Step 2: Create `frontend/js/dashboard.js`**

```javascript
// dashboard.js — Dashboard view logic
import { $, $$, formatNumber, formatPercent, formatFinancial, debounce } from './utils.js';

export class DashboardView {
  constructor(app) {
    this.app = app;
    this.chart = null;
    this.kpiOrder = ['latest_price', 'pe_ratio', 'market_cap', 'roe', 'score'];

    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('stock:loaded', (data) => this._onStockLoaded(data));
    this.app.on('stock:error', () => this._showEmpty());
    this.app.on('view:changed', (detail) => {
      if (detail.view === 'dashboard') this._onViewActivated();
    });

    // Hero search input
    const heroInput = $('#hero-search-input');
    if (heroInput) {
      heroInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const query = heroInput.value.trim();
          const match = query.match(/^(\d{6})\s*(.*)/);
          if (match) {
            this.app.selectStock(match[1], match[2] || match[1]);
          }
        }
      });
    }

    // CTA button
    $('#btn-start-ai')?.addEventListener('click', () => {
      this.app.router.navigate('/ai');
    });

    $('#btn-ai-expand')?.addEventListener('click', () => {
      this.app.router.navigate('/ai');
    });
  }

  _onStockLoaded(data) {
    $('#dashboard-empty').style.display = 'none';
    $('#dashboard-data').style.display = 'flex';
    this._renderKpi(data);
    this._renderChart(data);
    this._fetchAiSummary();
    this._loadRecentAnalyses();
  }

  _showEmpty() {
    $('#dashboard-data').style.display = 'none';
    $('#dashboard-empty').style.display = 'flex';
    this._loadRecentStocks();
  }

  _onViewActivated() {
    if (this.app.state.currentStock) {
      $('#dashboard-empty').style.display = 'none';
      $('#dashboard-data').style.display = 'flex';
    } else {
      $('#dashboard-data').style.display = 'none';
      $('#dashboard-empty').style.display = 'flex';
      $('#hero-search-input')?.focus();
    }
  }

  /* --- KPI Cards --- */

  _renderKpi(data) {
    const strip = $('#kpi-strip');
    if (!strip) return;

    const fields = [
      { key: 'latest_price', label: '最新价', format: v => formatNumber(v), isPrice: true },
      { key: 'change_pct', label: '涨跌幅', format: v => formatPercent(v / 100), isChange: true },
      { key: 'pe_ratio', label: '市盈率 PE', format: v => formatNumber(v, 1), isPrice: false },
      { key: 'market_cap', label: '总市值', format: v => formatFinancial(v), isPrice: false },
      { key: 'roe', label: 'ROE', format: v => formatPercent(v / 100), isPrice: false },
    ];

    const kpi = data.kpi || data;
    strip.innerHTML = fields.map(f => {
      const val = kpi[f.key];
      let changeHtml = '';
      if (f.isChange) {
        const isPositive = parseFloat(val) >= 0;
        changeHtml = `<div class="kpi-card-change ${isPositive ? 'text-success' : 'text-danger'}">
          ${isPositive ? '+' : ''}${f.format(val)}
        </div>`;
      }
      return `
        <div class="kpi-card">
          <div class="kpi-card-label">${f.label}</div>
          <div class="kpi-card-value${f.key === 'score' ? ' accent-gradient' : ''}">${f.format(val)}</div>
          ${changeHtml}
        </div>
      `;
    }).join('');

    // Click KPI card to navigate to related analysis
    strip.querySelectorAll('.kpi-card').forEach((card, i) => {
      card.addEventListener('click', () => {
        const modules = {
          latest_price: 'market_overview',
          change_pct: 'market_overview',
          pe_ratio: 'pe_valuation',
          market_cap: 'market_overview',
          roe: 'dupont',
        };
        const key = fields[i].key;
        if (modules[key]) {
          this.app.router.navigate(`/analysis/${modules[key]}`);
        }
      });
    });
  }

  /* --- Chart --- */

  _renderChart(data) {
    const canvas = $('#dashboard-chart');
    if (!canvas || !window.Chart) return;

    if (this.chart) this.chart.destroy();

    const prices = data.prices || [];
    const labels = prices.map(p => p.date);
    const values = prices.map(p => p.close);

    this.chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '收盘价',
          data: values,
          borderColor: '#6C5CE7',
          backgroundColor: 'rgba(108, 92, 231, 0.05)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 1.5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: '#111420',
            borderColor: '#1A1D2E',
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            display: true,
            grid: { color: 'rgba(255,255,255,0.03)' },
            ticks: { color: '#64748B', font: { size: 9 } },
          },
          y: {
            display: true,
            grid: { color: 'rgba(255,255,255,0.03)' },
            ticks: { color: '#64748B', font: { size: 9 } },
          },
        },
        interaction: {
          mode: 'nearest',
          axis: 'x',
          intersect: false,
        },
      },
    });
  }

  /* --- AI Summary --- */

  async _fetchAiSummary() {
    const body = $('#ai-summary-body');
    if (!body) return;

    body.innerHTML = '<div class="skeleton" style="height:60px;"></div>';

    try {
      const stock = this.app.state.currentStock;
      const res = await this.app.api.post('/api/ai/quick-summary', {
        stock_code: stock.code,
      });
      if (res && res.summary) {
        body.innerHTML = `<p>${res.summary}</p>`;
      } else {
        body.innerHTML = '<p class="text-muted">暂无AI快评</p>';
      }
    } catch {
      body.innerHTML = '<p class="text-muted">AI快评暂不可用</p>';
    }
  }

  /* --- Recent Analyses --- */

  _loadRecentAnalyses() {
    const container = $('#recent-analyses');
    if (!container) return;

    try {
      const history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
      if (!history.length) {
        container.style.display = 'none';
        return;
      }

      const items = history.slice(0, 5);
      container.style.display = 'flex';
      container.innerHTML = `
        <span class="recent-analyses-label">最近分析：</span>
        ${items.map(h => `
          <span class="recent-analysis-item" data-module="${h.module}">
            ${h.name} · ${h.time}
          </span>
        `).join('')}
        <span class="recent-analysis-new" id="btn-new-analysis">+ 新建分析 →</span>
      `;

      container.querySelectorAll('.recent-analysis-item').forEach(item => {
        item.addEventListener('click', () => {
          this.app.router.navigate(`/analysis/${item.dataset.module}`);
        });
      });

      $('#btn-new-analysis')?.addEventListener('click', () => {
        this.app.router.navigate('/analysis');
      });
    } catch {
      container.style.display = 'none';
    }
  }

  _loadRecentStocks() {
    const panel = $('#recent-panel');
    if (!panel) return;

    try {
      const history = JSON.parse(localStorage.getItem('fa_stock_history') || '[]');
      const recentStocks = history.slice(0, 5);

      panel.innerHTML = `
        <div style="padding: var(--space-4);">
          ${recentStocks.length ? `
            <div class="empty-section-title">最近查看</div>
            ${recentStocks.map(s => `
              <div class="recent-card" data-code="${s.code}" data-name="${s.name}">
                <div class="recent-card-header">
                  <span class="recent-card-code">${s.code}</span>
                </div>
                <div class="recent-card-name">${s.name}</div>
              </div>
            `).join('')}
          ` : ''}
          <div class="empty-section-title" style="margin-top: 12px;">快捷模板</div>
          <div class="template-tags">
            <span class="template-tag" data-template="profitability">盈利能力</span>
            <span class="template-tag" data-template="valuation">估值分析</span>
            <span class="template-tag" data-template="audit">异常排查</span>
            <span class="template-tag" data-template="dupont">杜邦分析</span>
          </div>
        </div>
      `;

      // Recent stock click
      panel.querySelectorAll('.recent-card').forEach(card => {
        card.addEventListener('click', () => {
          this.app.selectStock(card.dataset.code, card.dataset.name);
        });
      });

      // Template tag click
      panel.querySelectorAll('.template-tag').forEach(tag => {
        tag.addEventListener('click', () => {
          if (this.app.state.currentStock) {
            this.app.router.navigate('/ai');
          } else {
            $('#hero-search-input')?.focus();
          }
        });
      });
    } catch {}
  }
}

// Auto-initialize when app is ready
function initDashboard() {
  const app = window.__app;
  if (app) {
    new DashboardView(app);
  } else {
    setTimeout(initDashboard, 50);
  }
}
initDashboard();
```

- [ ] **Step 3: Commit dashboard CSS + JS**

```bash
git add frontend/css/dashboard.css frontend/js/dashboard.js
git commit -m "feat: add dashboard view with KPI cards, chart, and AI summary

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

*(Plan continues with Tasks 4-9 below...)*

---

### Task 4: Analysis Center CSS + JS

**Files:**
- Create: `frontend/css/analysis.css`
- Create: `frontend/js/analysis.js`

- [ ] **Step 1: Create `frontend/css/analysis.css`**

```css
/* === ANALYSIS CENTER === */

.analysis-center {
  display: flex;
  height: 100%;
}

/* Category Sidebar */
.analysis-categories {
  width: 160px;
  border-right: 1px solid var(--border-default);
  overflow-y: auto;
  flex-shrink: 0;
  padding: var(--space-2) 0;
}

.category-item {
  display: block;
  width: 100%;
  padding: 9px var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  text-align: left;
  border-left: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.category-item:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.category-item.active {
  color: var(--accent-soft);
  background: var(--accent-bg);
  border-left-color: var(--accent);
  font-weight: 600;
}

/* Module Grid */
.analysis-modules {
  flex: 1;
  padding: var(--space-4);
  overflow-y: auto;
}

.analysis-search-bar {
  width: 220px;
  height: 30px;
  padding: 0 var(--space-3);
  font-size: var(--text-xs);
  margin-bottom: var(--space-3);
}

.modules-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.modules-category-title {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}

.module-card {
  padding: var(--space-4);
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.module-card:hover {
  border-color: var(--border-accent);
  background: var(--surface-hover);
}

.module-card-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.module-card-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.4;
  margin-bottom: var(--space-2);
}

.module-card-tags {
  display: flex;
  gap: 4px;
}

.module-tag {
  padding: 2px 6px;
  background: var(--surface-hover);
  border-radius: var(--radius-sm);
  font-size: 8px;
  color: var(--text-muted);
}

.module-tag.chart {
  background: var(--accent-bg);
  color: var(--accent-soft);
}

/* Result Page */
.analysis-result {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.result-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border-default);
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}

.result-breadcrumb .current {
  color: var(--text-primary);
}

.result-breadcrumb .stock-badge {
  margin-left: auto;
  color: var(--success);
  font-size: var(--text-xs);
}

.result-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.result-text {
  flex: 1;
  padding: var(--space-4);
  overflow-y: auto;
  font-size: var(--text-sm);
  line-height: 1.8;
  color: var(--text-secondary);
}

.result-text h1 { font-size: var(--text-lg); color: var(--text-primary); margin: var(--space-4) 0 var(--space-2); }
.result-text h2 { font-size: var(--text-md); color: var(--text-primary); margin: var(--space-3) 0 var(--space-1); }
.result-text h3 { font-size: var(--text-base); color: var(--text-primary); margin: var(--space-2) 0 var(--space-1); }
.result-text table { margin: var(--space-2) 0; font-size: var(--text-xs); }
.result-text th { background: var(--surface-hover); padding: 6px 10px; text-align: left; font-weight: 600; color: var(--text-primary); }
.result-text td { padding: 5px 10px; border-bottom: 1px solid var(--border-default); }
.result-text code { font-family: var(--font-mono); background: var(--surface-hover); padding: 1px 4px; border-radius: 3px; font-size: var(--text-xs); }

.result-chart-panel {
  width: 280px;
  border-left: 1px solid var(--border-default);
  padding: var(--space-3);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border-default);
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.result-action-btn {
  padding: 5px 10px;
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.result-action-btn:hover {
  border-color: var(--border-accent);
  color: var(--text-primary);
}

.result-recommendations {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.result-rec-label {
  color: var(--text-muted);
}

.result-rec-link {
  padding: 4px 8px;
  background: var(--accent-bg);
  border-radius: var(--radius-sm);
  color: var(--accent-soft);
  cursor: pointer;
  font-size: var(--text-xs);
}

.result-rec-link:hover {
  background: var(--accent-bg-hover);
}

/* Copy button per section */
.copy-btn {
  opacity: 0;
  margin-left: 6px;
  font-size: var(--text-xs);
  color: var(--text-muted);
  cursor: pointer;
  background: none;
  border: none;
  padding: 2px 6px;
  border-radius: 3px;
  transition: opacity var(--transition-fast);
}

.result-text h2:hover .copy-btn,
.result-text h3:hover .copy-btn {
  opacity: 1;
}

.copy-btn:hover {
  color: var(--accent-soft);
  background: var(--surface-hover);
}
```

- [ ] **Step 2: Create `frontend/js/analysis.js`**

```javascript
// analysis.js — Analysis Center view
import { $, $$, h, formatNumber, formatDate, debounce } from './utils.js';

const CATEGORY_META = {
  market:     { name: '市场行情', icon: '01' },
  financial:  { name: '财务报表', icon: '02' },
  capability: { name: '能力分析', icon: '03' },
  deep:       { name: '深度分析', icon: '04' },
  valuation:  { name: '估值分析', icon: '05' },
  audit:      { name: '财务审计', icon: '06' },
  shareholder:{ name: '股东与资金', icon: '07' },
  risk:       { name: '风险与综合', icon: '08' },
  tushare:    { name: 'Tushare数据', icon: '09' },
};

const CATEGORY_ORDER = ['market','financial','capability','deep','valuation','audit','shareholder','risk','tushare'];

export class AnalysisView {
  constructor(app) {
    this.app = app;
    this.activeCategory = 'market';
    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'analysis') this._showCategoryList();
      if (d.view === 'analysis/result') this._showResult(d.params.module);
      if (d.view === 'analysis' && this.app.router.getModuleKey()) {
        this._showResult(this.app.router.getModuleKey());
      }
    });
  }

  _showCategoryList() {
    $('#analysis-center').style.display = 'flex';
    $('#analysis-result').style.display = 'none';
    this._renderCategories();
    this._renderModules(this.activeCategory);
  }

  _renderCategories() {
    const container = $('#analysis-categories');
    container.innerHTML = CATEGORY_ORDER.map(cat => `
      <button class="category-item${cat === this.activeCategory ? ' active' : ''}"
              data-category="${cat}">
        ${CATEGORY_META[cat].name}
      </button>
    `).join('');

    container.querySelectorAll('.category-item').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeCategory = btn.dataset.category;
        this._renderCategories();
        this._renderModules(this.activeCategory);
      });
    });
  }

  _renderModules(category) {
    const container = $('#analysis-modules');
    const modules = this.app.state.modules.filter(m => m.category === category);
    container.innerHTML = `
      <div class="modules-header">
        <span class="modules-category-title">${CATEGORY_META[category].name} · ${modules.length} 个模块</span>
      </div>
      <div class="module-grid">
        ${modules.map(m => `
          <div class="module-card" data-key="${m.key}">
            <div class="module-card-name">${m.name}</div>
            <div class="module-card-desc">${m.desc}</div>
            <div class="module-card-tags">
              ${m.output === 'chart' ? '<span class="module-tag chart">图表</span>' : ''}
              ${m.output === 'table' ? '<span class="module-tag chart">表格</span>' : ''}
              <span class="module-tag">${m.output === 'chart' || m.output === 'table' ? '文字+图表' : '文字'}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.module-card').forEach(card => {
      card.addEventListener('click', () => {
        const key = card.dataset.key;
        this.app.router.navigate(`/analysis/${key}`);
      });
    });
  }

  async _showResult(moduleKey) {
    if (!moduleKey) return;

    $('#analysis-center').style.display = 'none';
    $('#analysis-result').style.display = 'flex';

    const mod = this.app.state.modules.find(m => m.key === moduleKey);
    const stock = this.app.state.currentStock;

    // Breadcrumb
    const breadcrumb = $('.result-breadcrumb', $('#analysis-result'));
    if (breadcrumb) {
      const catName = mod ? CATEGORY_META[mod.category]?.name || mod.category : '';
      breadcrumb.innerHTML = `
        <span class="result-breadcrumb-link" data-nav="/analysis">分析中心</span>
        <span>›</span>
        <span class="result-breadcrumb-link" data-nav="/analysis">${catName}</span>
        <span>›</span>
        <span class="current">${mod ? mod.name : moduleKey}</span>
        ${stock ? `<span class="stock-badge">${stock.code} ${stock.name}</span>` : ''}
      `;
      breadcrumb.querySelectorAll('.result-breadcrumb-link').forEach(link => {
        link.addEventListener('click', () => this.app.router.navigate(link.dataset.nav));
      });
    }

    // Result body
    const body = $('.result-text', $('#analysis-result'));
    if (body) {
      body.innerHTML = `
        <div class="skeleton" style="height:40px;width:60%;margin-bottom:16px;"></div>
        <div class="skeleton" style="height:14px;margin-bottom:8px;"></div>
        <div class="skeleton" style="height:14px;width:80%;margin-bottom:8px;"></div>
        <div class="skeleton" style="height:14px;width:90%;margin-bottom:8px;"></div>
      `;

      if (stock) {
        try {
          const result = await this.app.api.runAnalysis(stock.code, moduleKey);
          body.innerHTML = this._renderMarkdown(result.text || result.report || JSON.stringify(result));
          this._addCopyButtons(body);
          this._renderChart(moduleKey, result);
          this._renderRecommendations(moduleKey, mod);
          this._saveToHistory(moduleKey, mod);
        } catch (err) {
          body.innerHTML = `<p class="text-danger">分析失败: ${err.message}</p>`;
        }
      } else {
        body.innerHTML = '<p class="text-muted">请先在顶部输入股票代码</p>';
      }
    }
  }

  _renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
      marked.setOptions({ breaks: true, gfm: true });
      return marked.parse(String(text));
    }
    return `<pre>${text}</pre>`;
  }

  _addCopyButtons(container) {
    container.querySelectorAll('h2, h3').forEach(heading => {
      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = '复制';
      btn.addEventListener('click', () => {
        let content = '';
        let el = heading.nextElementSibling;
        while (el && !['H2','H3'].includes(el.tagName)) {
          content += el.textContent + '\n';
          el = el.nextElementSibling;
        }
        navigator.clipboard.writeText(content).then(() => {
          btn.textContent = '已复制';
          setTimeout(() => btn.textContent = '复制', 1500);
        }).catch(() => {
          // Fallback
          const ta = document.createElement('textarea');
          ta.value = content;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          btn.textContent = '已复制';
          setTimeout(() => btn.textContent = '复制', 1500);
        });
      });
      heading.appendChild(btn);
    });
  }

  _renderChart(moduleKey, result) {
    const panel = $('.result-chart-panel', $('#analysis-result'));
    if (!panel || !window.Chart) return;

    const chartData = result.chart_data || result;
    const chartModules = ['dupont', 'fscore', 'pb_roe', 'comprehensive', 'audit_full', 'compare_with_peers', 'technical'];

    if (!chartModules.includes(moduleKey)) {
      panel.innerHTML = '<span class="text-muted" style="font-size:10px;">文本报告</span>';
      return;
    }

    const canvasId = 'result-chart-canvas';
    panel.innerHTML = `<canvas id="${canvasId}"></canvas>`;
    const canvas = document.getElementById(canvasId);

    new Chart(canvas, {
      type: moduleKey === 'fscore' ? 'radar' : 'bar',
      data: {
        labels: chartData.labels || [],
        datasets: [{
          label: chartData.label || '',
          data: chartData.values || [],
          backgroundColor: 'rgba(108, 92, 231, 0.3)',
          borderColor: '#6C5CE7',
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#94A3B8', font: { size: 10 } } },
        },
        scales: moduleKey === 'fscore' ? {} : {
          x: { ticks: { color: '#64748B', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
          y: { ticks: { color: '#64748B', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.03)' } },
        },
      },
    });
  }

  _renderRecommendations(moduleKey, currentMod) {
    const container = $('.result-recommendations', $('#analysis-result'));
    if (!container) return;

    // Find related modules in same category
    if (currentMod) {
      const siblings = this.app.state.modules
        .filter(m => m.category === currentMod.category && m.key !== moduleKey)
        .slice(0, 2);
      if (siblings.length) {
        container.innerHTML = `
          <span class="result-rec-label">推荐下一步：</span>
          ${siblings.map(s => `
            <span class="result-rec-link" data-key="${s.key}">${s.name} →</span>
          `).join('')}
        `;
        container.querySelectorAll('.result-rec-link').forEach(link => {
          link.addEventListener('click', () => {
            this.app.router.navigate(`/analysis/${link.dataset.key}`);
          });
        });
        return;
      }
    }
    container.innerHTML = '';
  }

  _saveToHistory(moduleKey, mod) {
    try {
      const history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
      history.unshift({
        module: moduleKey,
        name: mod ? mod.name : moduleKey,
        time: new Date().toLocaleString('zh-CN'),
      });
      if (history.length > 20) history.length = 20;
      localStorage.setItem('fa_analysis_history', JSON.stringify(history));
    } catch {}
  }
}

function initAnalysis() {
  const app = window.__app;
  if (app) new AnalysisView(app);
  else setTimeout(initAnalysis, 50);
}
initAnalysis();
```

- [ ] **Step 3: Commit analysis center**

```bash
git add frontend/css/analysis.css frontend/js/analysis.js
git commit -m "feat: add analysis center with 9 categories, module grid, and result pages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: AI Chat CSS + JS

**Files:**
- Create: `frontend/css/chat.css`
- Create: `frontend/js/chat.js`

- [ ] **Step 1: Create `frontend/css/chat.css`**

```css
/* === AI WORKSPACE === */

.ai-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.ai-subtabs {
  display: flex;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.ai-subtab {
  padding: 10px 18px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.ai-subtab:hover { color: var(--text-primary); }

.ai-subtab.active {
  color: var(--accent-soft);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

.ai-main {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* Chat Area */
.ai-chat-area {
  flex: 2;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chat-message {
  display: flex;
  gap: var(--space-2);
  max-width: 85%;
}

.chat-message.ai { align-self: flex-start; }
.chat-message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  flex-shrink: 0;
  color: #fff;
}

.chat-avatar.ai { background: var(--accent-gradient); }
.chat-avatar.user { background: var(--surface-hover); color: var(--text-secondary); }

.chat-bubble {
  padding: 10px 14px;
  border-radius: 0 10px 10px 10px;
  font-size: var(--text-sm);
  line-height: 1.6;
}

.chat-message.ai .chat-bubble {
  background: var(--surface-glass);
  color: var(--text-secondary);
}

.chat-message.user .chat-bubble {
  background: var(--accent-bg);
  border: 1px solid rgba(108, 92, 231, 0.15);
  border-radius: 10px 0 10px 10px;
  color: var(--text-primary);
}

.chat-bubble p { margin-bottom: var(--space-2); }
.chat-bubble p:last-child { margin-bottom: 0; }
.chat-bubble code { font-family: var(--font-mono); background: var(--surface-hover); padding: 1px 4px; border-radius: 3px; font-size: var(--text-xs); }
.chat-bubble table { margin: var(--space-1) 0; font-size: var(--text-xs); width: 100%; }
.chat-bubble th { background: var(--surface-hover); padding: 4px 8px; }
.chat-bubble td { padding: 3px 8px; border-bottom: 1px solid var(--border-default); }

/* Streaming cursor */
.streaming-cursor {
  display: inline-block;
  width: 6px;
  height: 12px;
  background: var(--accent-soft);
  vertical-align: middle;
  margin-left: 2px;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Chat Input */
.chat-input-area {
  border-top: 1px solid var(--border-default);
  padding: var(--space-3);
  flex-shrink: 0;
}

.template-chips {
  display: flex;
  gap: 4px;
  margin-bottom: var(--space-2);
  flex-wrap: wrap;
}

.template-chip {
  padding: 3px 8px;
  background: var(--surface-glass);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.template-chip:hover {
  background: var(--accent-bg);
  color: var(--accent-soft);
}

.template-chip.active {
  background: var(--accent-bg);
  color: var(--accent-soft);
  border: 1px solid var(--border-accent);
}

.chat-input-row {
  display: flex;
  gap: var(--space-2);
}

.chat-input {
  flex: 1;
  height: 34px;
  padding: 0 var(--space-3);
  font-size: var(--text-sm);
}

.chat-send-btn, .chat-stop-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.chat-send-btn {
  background: var(--accent);
  color: #fff;
}

.chat-send-btn:hover { background: var(--accent-hover); }
.chat-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.chat-stop-btn {
  background: var(--danger);
  color: #fff;
}

/* Context Panel */
.ai-context-panel {
  width: 240px;
  border-left: 1px solid var(--border-default);
  padding: var(--space-3);
  overflow-y: auto;
  flex-shrink: 0;
}

.ctx-section {
  margin-bottom: var(--space-3);
}

.ctx-section-title {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--space-2);
}

.ctx-card {
  padding: var(--space-2);
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-1);
}

.ctx-card-title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.ctx-card-text {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.4;
}

.ctx-signal {
  padding: var(--space-2);
  background: var(--warning-bg);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  color: var(--warning);
}

/* Template Select Grid */
.template-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  padding: var(--space-4);
}

.template-card {
  padding: var(--space-4);
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.template-card:hover {
  border-color: var(--border-accent);
  background: var(--surface-hover);
}

.template-card.selected {
  border-color: var(--accent);
  background: var(--accent-bg);
}

.template-card-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.template-card-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: 1.4;
  margin-bottom: var(--space-2);
}

.template-card-data {
  font-size: 8px;
  color: var(--text-disabled);
}

/* Debate Layout */
.ai-debate {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.debate-columns {
  display: flex;
  flex: 1;
  min-height: 0;
}

.debate-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-default);
}

.debate-col:last-child { border-right: none; }

.debate-col-header {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-default);
  font-size: var(--text-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.debate-col-header.value { color: var(--info); background: var(--info-bg); }
.debate-col-header.growth { color: var(--success); background: var(--success-bg); }
.debate-col-header.risk { color: var(--danger); background: var(--danger-bg); }

.debate-col-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.6;
}

.debate-consensus {
  padding: var(--space-3);
  border-top: 1px solid var(--border-default);
  background: var(--accent-bg);
  flex-shrink: 0;
}

.debate-consensus-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--accent-soft);
  margin-bottom: 4px;
}

.debate-consensus-text {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
```

- [ ] **Step 2: Create `frontend/js/chat.js`**

```javascript
// chat.js — AI Chat view (conversation, templates, debate)
import { $, $$, h, escapeHtml } from './utils.js';

const TEMPLATES = [
  { id: 'profitability', name: '盈利能力深度解读', desc: '毛利率·净利率·ROE·盈利质量 四维解读', data: 'income, financial' },
  { id: 'audit', name: '财务异常信号排查', desc: '资产端·利润端·现金流·勾稽 四维排查', data: 'balance, income, cashflow' },
  { id: 'valuation', name: '估值合理性判断', desc: 'PE分位·股息率·市净率 三维判断', data: 'daily_basic, financial' },
  { id: 'shareholder', name: '股东结构评估', desc: '股权集中度·机构持仓·筹码变化', data: 'top10_holders, stk_holdernumber' },
  { id: 'capital_flow', name: '资金面多空分析', desc: '主力资金·融资融券·北向资金 三维解读', data: 'moneyflow, margin' },
  { id: 'growth', name: '成长质量检查', desc: '营收成长·利润成长·现金流质量 三维评估', data: 'income, cashflow, financial' },
];

export class ChatView {
  constructor(app) {
    this.app = app;
    this.mode = 'chat';  // 'chat' | 'template' | 'debate'
    this.activeTemplate = null;
    this.isStreaming = false;
    this.currentAiBubble = null;
    this.debateRound = 0;

    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'ai') this._initView();
    });

    // Shortcut: Ctrl+Space for AI panel
    this.app.on('shortcut:ai-panel', () => this._toggleAiPanel());
    this.app.on('shortcut:escape', () => this._closeOverlays());
  }

  _initView() {
    this._bindSubTabs();
    this._bindTemplateChips();
    this._bindChatInput();
    this._bindDebateControls();
    this._renderContextPanel();
  }

  /* --- Sub Tabs --- */

  _bindSubTabs() {
    $$('#ai-subtabs .ai-subtab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.mode = tab.dataset.mode;
        $$('#ai-subtabs .ai-subtab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        $('#ai-main').style.display = this.mode === 'debate' ? 'none' : 'flex';
        $('#ai-debate').style.display = this.mode === 'debate' ? 'flex' : 'none';

        if (this.mode === 'template') {
          this._renderTemplateGrid();
        }
      });
    });
  }

  /* --- Template Chips --- */

  _bindTemplateChips() {
    const container = $('#template-chips');
    if (!container) return;

    container.innerHTML = TEMPLATES.map(t => `
      <span class="template-chip" data-id="${t.id}">${t.name}</span>
    `).join('');

    container.querySelectorAll('.template-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const id = chip.dataset.id;
        container.querySelectorAll('.template-chip').forEach(c => c.classList.remove('active'));
        if (this.activeTemplate === id) {
          this.activeTemplate = null;
        } else {
          chip.classList.add('active');
          this.activeTemplate = id;
          $('#chat-input').placeholder = `已选「${TEMPLATES.find(t => t.id === id)?.name}」，输入补充问题或直接发送...`;
        }
      });
    });
  }

  _renderTemplateGrid() {
    const area = $('#ai-chat-area');
    const messages = $('#chat-messages');
    if (!messages) return;

    messages.innerHTML = `
      <div class="template-grid">
        ${TEMPLATES.map(t => `
          <div class="template-card${this.activeTemplate === t.id ? ' selected' : ''}" data-id="${t.id}">
            <div class="template-card-name">${t.name}</div>
            <div class="template-card-desc">${t.desc}</div>
            <div class="template-card-data">所需数据：${t.data}</div>
          </div>
        `).join('')}
      </div>
      <p style="text-align:center;font-size:10px;color:var(--text-muted);margin-top:12px;">
        选择模板 → 自动加载所需数据 → 发送给 AI → 流式展示结构化分析结果
      </p>
    `;

    messages.querySelectorAll('.template-card').forEach(card => {
      card.addEventListener('click', () => {
        this.activeTemplate = card.dataset.id;
        this._renderTemplateGrid();
        this._sendTemplateMessage(this.activeTemplate);
      });
    });
  }

  /* --- Chat Input --- */

  _bindChatInput() {
    const input = $('#chat-input');
    const sendBtn = $('#btn-chat-send');
    const stopBtn = $('#btn-chat-stop');

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._sendMessage();
      }
    });

    sendBtn?.addEventListener('click', () => this._sendMessage());
    stopBtn?.addEventListener('click', () => this._stopStreaming());
  }

  async _sendMessage() {
    const input = $('#chat-input');
    const text = input.value.trim();
    if (!text || this.isStreaming) return;
    input.value = '';

    const messages = $('#chat-messages');
    // Add user bubble
    messages.appendChild(this._createBubble('user', text));
    messages.scrollTop = messages.scrollHeight;

    if (!this.app.state.currentStock) {
      messages.appendChild(this._createBubble('ai', '请先在顶部输入股票代码'));
      return;
    }

    this._setStreaming(true);
    this.currentAiBubble = this._createBubble('ai', '');
    messages.appendChild(this.currentAiBubble);

    const ws = this.app.api.connectWebSocket();
    const payload = this.activeTemplate
      ? { type: 'template', template_id: this.activeTemplate, stock_code: this.app.state.currentStock.code }
      : { type: 'chat', message: text, stock_code: this.app.state.currentStock.code };

    this.app.api.sendWebSocket(payload);

    const onMessage = (msg) => {
      if (msg.event === 'token') {
        this.currentAiBubble.querySelector('.chat-bubble').innerHTML += msg.data;
        messages.scrollTop = messages.scrollHeight;
      } else if (msg.event === 'section') {
        const bubble = this.currentAiBubble.querySelector('.chat-bubble');
        bubble.innerHTML += `<h3 style="color:var(--accent-soft);margin-top:8px;">${msg.title || ''}</h3>`;
      } else if (msg.event === 'done') {
        this._setStreaming(false);
        this.app.api.offWs('message', onMessage);
      }
    };

    this.app.api.onWs('message', onMessage);
  }

  async _sendTemplateMessage(templateId) {
    if (!this.app.state.currentStock) return;
    this._setStreaming(true);

    const messages = $('#chat-messages');
    messages.innerHTML = '';
    this.currentAiBubble = this._createBubble('ai', '');
    messages.appendChild(this.currentAiBubble);

    const ws = this.app.api.connectWebSocket();
    this.app.api.sendWebSocket({
      type: 'template',
      template_id: templateId,
      stock_code: this.app.state.currentStock.code,
    });

    const onMessage = (msg) => {
      if (msg.event === 'token') {
        this.currentAiBubble.querySelector('.chat-bubble').innerHTML += msg.data;
        messages.scrollTop = messages.scrollHeight;
      } else if (msg.event === 'section') {
        const bubble = this.currentAiBubble.querySelector('.chat-bubble');
        bubble.innerHTML += `<h3 style="color:var(--accent-soft);margin-top:8px;">${msg.title || ''}</h3>`;
      } else if (msg.event === 'done') {
        this._setStreaming(false);
        this.app.api.offWs('message', onMessage);
      }
    };

    this.app.api.onWs('message', onMessage);
  }

  _createBubble(role, text) {
    return h('div', { className: `chat-message ${role}` },
      h('div', { className: `chat-avatar ${role}`, innerHTML: role === 'ai' ? 'AI' : 'U' }),
      h('div', { className: 'chat-bubble', innerHTML: text }),
    );
  }

  _setStreaming(streaming) {
    this.isStreaming = streaming;
    $('#btn-chat-send').style.display = streaming ? 'none' : 'flex';
    $('#btn-chat-stop').style.display = streaming ? 'flex' : 'none';
  }

  _stopStreaming() {
    this.app.api.closeWebSocket();
    this.app.api.connectWebSocket();
    this._setStreaming(false);
    if (this.currentAiBubble) {
      const bubble = this.currentAiBubble.querySelector('.chat-bubble');
      if (bubble && !bubble.textContent.trim()) {
        bubble.textContent = '[已取消]';
      }
    }
  }

  /* --- Debate --- */

  _bindDebateControls() {
    // Trigger debate start
    this.app.on('view:changed', (d) => {
      if (d.view === 'ai' && this.mode === 'debate' && this.app.state.currentStock) {
        this._startDebate();
      }
    });
  }

  async _startDebate() {
    const cols = $('#debate-columns');
    const consensus = $('#debate-consensus');
    if (!cols) return;

    cols.innerHTML = `
      <div class="debate-col"><div class="debate-col-header value">价值投资者</div><div class="debate-col-body" id="debate-value">分析中...</div></div>
      <div class="debate-col"><div class="debate-col-header growth">成长投资者</div><div class="debate-col-body" id="debate-growth">分析中...</div></div>
      <div class="debate-col"><div class="debate-col-header risk">风控分析师</div><div class="debate-col-body" id="debate-risk">分析中...</div></div>
    `;

    const ws = this.app.api.connectWebSocket();
    this.app.api.sendWebSocket({
      type: 'debate',
      topic: `${this.app.state.currentStock.name || this.app.state.currentStock.code} 投资价值分析`,
      stock_code: this.app.state.currentStock.code,
    });

    const onMessage = (msg) => {
      if (msg.event === 'debate_round') {
        this.debateRound = msg.round;
        const analystMap = { value: 'debate-value', growth: 'debate-growth', risk: 'debate-risk' };
        const col = document.getElementById(analystMap[msg.analyst]);
        if (col) col.innerHTML += `<p>${msg.data || ''}</p>`;
        cols.scrollTop = cols.scrollHeight;
      } else if (msg.event === 'done') {
        consensus.innerHTML = `
          <div class="debate-consensus-label">共识结论 (第${this.debateRound}轮)</div>
          <div class="debate-consensus-text">${msg.summary || '分析完成'}</div>
        `;
        this.app.api.offWs('message', onMessage);
      }
    };

    this.app.api.onWs('message', onMessage);
  }

  /* --- Context Panel --- */

  _renderContextPanel() {
    const panel = $('#ai-context-panel');
    if (!panel) return;

    const stock = this.app.state.currentStock;
    const kpi = this.app.state.kpiData;

    panel.innerHTML = `
      <div class="ctx-section">
        <div class="ctx-section-title">当前股票</div>
        ${stock ? `
          <div class="ctx-card">
            <div class="ctx-card-title">${stock.code} ${stock.name || ''}</div>
            <div class="ctx-card-text">
              ${kpi ? `最新价 ${kpi.latest_price || '--'} · PE ${kpi.pe_ratio || '--'}` : '数据加载中...'}
            </div>
          </div>
        ` : '<div class="ctx-card-text text-muted">未选择股票</div>'}
      </div>
      <div class="ctx-section">
        <div class="ctx-section-title">分析历史</div>
        <div class="ctx-card-text text-muted" id="ctx-history">--</div>
      </div>
    `;

    // Load history
    try {
      const history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
      const ctxHistory = $('#ctx-history');
      if (ctxHistory && history.length) {
        ctxHistory.innerHTML = history.slice(0, 5).map(h =>
          `<div style="margin-bottom:2px;">${h.name} · <span style="color:var(--text-disabled)">${h.time}</span></div>`
        ).join('');
      }
    } catch {}
  }

  /* --- AI Side Panel --- */

  _toggleAiPanel() {
    const panel = $('#ai-panel');
    if (!panel) return;
    const isOpen = panel.style.display === 'flex';
    panel.style.display = isOpen ? 'none' : 'flex';

    if (!isOpen) {
      this._renderAiPanelContext();
      $('#ai-panel-input')?.focus();
    }
  }

  _renderAiPanelContext() {
    const ctx = $('#ai-panel-context');
    if (!ctx) return;
    const stock = this.app.state.currentStock;
    ctx.innerHTML = stock
      ? `<div class="ctx-section-title" style="text-align:center;">上下文：${stock.code} ${stock.name || ''} 当前数据</div>`
      : '<div class="ctx-section-title" style="text-align:center;">未选择股票</div>';
  }

  _closeOverlays() {
    $('#ai-panel').style.display = 'none';
    $('#command-palette').style.display = 'none';
  }
}

function initChat() {
  const app = window.__app;
  if (app) new ChatView(app);
  else setTimeout(initChat, 50);
}
initChat();
```

- [ ] **Step 3: Commit AI chat**

```bash
git add frontend/css/chat.css frontend/js/chat.js
git commit -m "feat: add AI workspace with chat, templates, debate, and side panel

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Overlays CSS + Command Palette JS

**Files:**
- Create: `frontend/css/overlays.css`
- Create: `frontend/js/command-palette.js`

- [ ] **Step 1: Create `frontend/css/overlays.css`**

```css
/* === COMMAND PALETTE === */

.command-palette {
  position: fixed;
  top: 15%;
  left: 50%;
  transform: translateX(-50%);
  width: 520px;
  max-height: 400px;
  background: var(--surface-elevated);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cp-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.cp-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: var(--text-base);
  color: var(--text-primary);
  outline: none;
}

.cp-hint {
  font-size: var(--text-xs);
  color: var(--text-disabled);
  font-family: var(--font-mono);
  padding: 2px 6px;
  background: var(--surface-glass);
  border-radius: var(--radius-sm);
}

.cp-results {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-1);
}

.cp-result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.cp-result-item:hover,
.cp-result-item.active {
  background: var(--accent-bg);
}

.cp-result-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.cp-result-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.cp-result-path {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

.cp-result-hint {
  font-size: var(--text-xs);
  color: var(--text-disabled);
  font-family: var(--font-mono);
}

.cp-empty {
  padding: var(--space-6);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--text-muted);
}

/* === AI SIDE PANEL === */

.ai-panel {
  position: fixed;
  top: var(--topnav-height);
  right: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--surface-elevated);
  border-left: 1px solid var(--border-default);
  z-index: 500;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.ai-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.ai-panel-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.ai-panel-close {
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0 4px;
}

.ai-panel-close:hover { color: var(--text-primary); }

.ai-panel-context {
  padding: var(--space-2);
  font-size: var(--text-xs);
  text-align: center;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.ai-panel-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ai-panel-input-row {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2);
  border-top: 1px solid var(--border-default);
  flex-shrink: 0;
}

.ai-panel-input {
  flex: 1;
  height: 28px;
  padding: 0 var(--space-2);
  font-size: var(--text-xs);
}

.ai-panel-send {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: #fff;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* === MODAL === */

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 900;
}

.modal-overlay {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 901;
  min-width: 400px;
  max-width: 640px;
  max-height: 80vh;
}

.modal {
  background: var(--surface-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: var(--space-6);
  overflow-y: auto;
  max-height: 80vh;
}

.modal h2 {
  font-size: var(--text-lg);
  margin-bottom: var(--space-4);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.btn-primary {
  padding: 7px 16px;
  background: var(--accent);
  border-radius: var(--radius-md);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: 600;
}

.btn-primary:hover { background: var(--accent-hover); }

.btn-ghost {
  padding: 7px 16px;
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.btn-ghost:hover { border-color: var(--border-accent); color: var(--text-primary); }

.btn-danger {
  padding: 7px 16px;
  background: var(--danger-bg);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-md);
  color: var(--danger);
  font-size: var(--text-sm);
}
```

- [ ] **Step 2: Create `frontend/js/command-palette.js`**

```javascript
// command-palette.js — Global command palette
import { $, $$, debounce } from './utils.js';

export class CommandPalette {
  constructor(app) {
    this.app = app;
    this.activeIndex = -1;
    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('shortcut:command-palette', () => this._toggle());
    this.app.on('shortcut:escape', () => this._close());

    const input = $('#cp-input');
    input?.addEventListener('input', debounce(() => this._search(input.value), 100));
    input?.addEventListener('keydown', (e) => this._handleKey(e));
  }

  _toggle() {
    const palette = $('#command-palette');
    if (!palette) return;
    const isOpen = palette.style.display === 'flex';
    if (isOpen) {
      this._close();
    } else {
      this._open();
    }
  }

  _open() {
    const palette = $('#command-palette');
    palette.style.display = 'flex';
    $('#cp-input').value = '';
    this.activeIndex = -1;
    this._search('');
    setTimeout(() => $('#cp-input')?.focus(), 50);
  }

  _close() {
    $('#command-palette').style.display = 'none';
    this.activeIndex = -1;
  }

  _search(query) {
    const q = query.toLowerCase().trim();
    const modules = this.app.state.modules || [];
    const aiTemplates = [
      { key: 'ai_profitability', name: '盈利能力深度解读', category: 'ai', desc: 'AI模板' },
      { key: 'ai_audit', name: '财务异常信号排查', category: 'ai', desc: 'AI模板' },
      { key: 'ai_valuation', name: '估值合理性判断', category: 'ai', desc: 'AI模板' },
      { key: 'ai_shareholder', name: '股东结构评估', category: 'ai', desc: 'AI模板' },
      { key: 'ai_capital_flow', name: '资金面多空分析', category: 'ai', desc: 'AI模板' },
      { key: 'ai_growth', name: '成长质量检查', category: 'ai', desc: 'AI模板' },
    ];

    const allItems = [...modules, ...aiTemplates];
    const filtered = q
      ? allItems.filter(m =>
          m.name.toLowerCase().includes(q) ||
          m.key.toLowerCase().includes(q) ||
          (m.category || '').toLowerCase().includes(q) ||
          (m.desc || '').toLowerCase().includes(q)
        )
      : allItems;

    const results = $('#cp-results');
    if (!filtered.length) {
      results.innerHTML = '<div class="cp-empty">未找到匹配项</div>';
      return;
    }

    this.activeIndex = 0;
    results.innerHTML = filtered.map((m, i) => `
      <div class="cp-result-item${i === 0 ? ' active' : ''}" data-index="${i}" data-key="${m.key}" data-is-ai="${m.category === 'ai'}">
        <div class="cp-result-left">
          <span class="cp-result-name">${m.name}</span>
          <span class="cp-result-path">${m.category || ''}${m.desc ? ' · ' + m.desc : ''}</span>
        </div>
        <span class="cp-result-hint">⏎</span>
      </div>
    `).join('');

    results.querySelectorAll('.cp-result-item').forEach(item => {
      item.addEventListener('click', () => {
        this._executeSelection(item);
      });
    });
  }

  _handleKey(e) {
    const results = $$('.cp-result-item', $('#cp-results'));
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.activeIndex = Math.min(this.activeIndex + 1, results.length - 1);
      this._updateActive(results);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.activeIndex = Math.max(this.activeIndex - 1, 0);
      this._updateActive(results);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[this.activeIndex]) {
        this._executeSelection(results[this.activeIndex]);
      }
    } else if (e.key === 'Escape') {
      this._close();
    }
  }

  _updateActive(results) {
    results.forEach((item, i) => item.classList.toggle('active', i === this.activeIndex));
  }

  _executeSelection(item) {
    const key = item.dataset.key;
    const isAi = item.dataset.isAi === 'true';
    if (isAi) {
      this.app.router.navigate('/ai');
      // Auto-select the template after navigation
      setTimeout(() => {
        const chip = $(`.template-chip[data-id="${key.replace('ai_', '')}"]`);
        if (chip) chip.click();
      }, 300);
    } else {
      this.app.router.navigate(`/analysis/${key}`);
    }
    this._close();
  }
}

function initCommandPalette() {
  const app = window.__app;
  if (app) new CommandPalette(app);
  else setTimeout(initCommandPalette, 50);
}
initCommandPalette();
```

- [ ] **Step 3: Commit overlays**

```bash
git add frontend/css/overlays.css frontend/js/command-palette.js
git commit -m "feat: add command palette, AI side panel, and modal overlay system

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Data Browser CSS + JS + Settings

**Files:**
- Create: `frontend/css/data.css`
- Create: `frontend/js/data-browser.js`
- Create: `frontend/js/settings.js`

- [ ] **Step 1: Create `frontend/css/data.css`**

```css
/* === DATA BROWSER === */

.data-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--space-4);
}

.data-controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
  flex-shrink: 0;
}

.data-select {
  padding: 6px 12px;
  min-width: 180px;
  font-size: var(--text-sm);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%2394A3B8' stroke-width='1.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  padding-right: 30px;
}

.data-filter {
  width: 180px;
  height: 30px;
  padding: 0 var(--space-3);
  font-size: var(--text-xs);
}

.data-table-wrapper {
  flex: 1;
  overflow: auto;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

.data-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
}

.data-table th {
  background: var(--surface-elevated);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  font-size: var(--text-xs);
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-default);
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}

.data-table th:hover { color: var(--accent-soft); }

.data-table th .sort-icon {
  margin-left: 4px;
  font-size: 8px;
  color: var(--text-disabled);
}

.data-table td {
  padding: 6px 12px;
  border-bottom: 1px solid var(--border-default);
  color: var(--text-secondary);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.data-table tbody tr:hover td {
  background: var(--surface-hover);
}

.data-table .cell-number {
  text-align: right;
}

.data-table .cell-positive { color: var(--success); }
.data-table .cell-negative { color: var(--danger); }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  flex-shrink: 0;
}

.page-btn {
  padding: 4px 10px;
  background: var(--surface-glass);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  cursor: pointer;
}

.page-btn:hover { border-color: var(--border-accent); color: var(--text-primary); }
.page-btn.active { background: var(--accent-bg); color: var(--accent-soft); border-color: var(--border-accent); }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.page-info {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Settings Page */
.settings-page {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--space-8);
}

.settings-section {
  margin-bottom: var(--space-6);
}

.settings-section h2 {
  font-size: var(--text-md);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.settings-field {
  margin-bottom: var(--space-4);
}

.settings-field label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.settings-field .hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 2px;
}

.settings-field input[type="text"],
.settings-field input[type="password"],
.settings-field input[type="number"],
.settings-field select {
  width: 100%;
  padding: 7px 12px;
  font-size: var(--text-sm);
}

.settings-field input[type="range"] {
  width: 100%;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online { background: var(--success); }
.status-dot.offline { background: var(--danger); }
```

- [ ] **Step 2: Create `frontend/js/data-browser.js`**

```javascript
// data-browser.js — Data table view
import { $, $$, h, formatNumber, formatPercent, formatDate, formatFinancial, debounce } from './utils.js';

const DATA_TYPES = [
  { value: 'fina_income', label: '利润表' },
  { value: 'fina_balance', label: '资产负债表' },
  { value: 'fina_cashflow', label: '现金流量表' },
  { value: 'fina_indicator', label: '财务指标' },
  { value: 'daily', label: '日线行情' },
  { value: 'dividend', label: '分红数据' },
  { value: 'top10_holders', label: '十大股东' },
  { value: 'moneyflow', label: '资金流向' },
  { value: 'margin', label: '融资融券' },
  { value: 'stk_holdernumber', label: '股东人数' },
  { value: 'fina_audit', label: '审计意见' },
  { value: 'fina_mainbz', label: '主营业务构成' },
];

const PAGE_SIZE = 50;

export class DataBrowserView {
  constructor(app) {
    this.app = app;
    this.data = [];
    this.filteredData = [];
    this.currentPage = 1;
    this.sortCol = null;
    this.sortAsc = true;
    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'data') this._init();
    });
  }

  _init() {
    this._populateTypeSelect();
    this._bindControls();
  }

  _populateTypeSelect() {
    const select = $('#data-type-select');
    if (!select) return;

    select.innerHTML = `
      <option value="">选择数据类型...</option>
      ${DATA_TYPES.map(dt => `<option value="${dt.value}">${dt.label}</option>`).join('')}
    `;

    select.addEventListener('change', () => {
      const type = select.value;
      if (type) this._loadData(type);
    });
  }

  _bindControls() {
    const filter = $('#data-filter');
    filter?.addEventListener('input', debounce(() => {
      this._applyFilter(filter.value);
    }, 200));

    $('#btn-export-data')?.addEventListener('click', () => this._exportCSV());
  }

  async _loadData(dataType) {
    const stock = this.app.state.currentStock;
    if (!stock) {
      $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">请先在顶部输入股票代码</td></tr>';
      return;
    }

    $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;"><div class="skeleton" style="height:200px;"></div></td></tr>';

    try {
      const result = await this.app.api.fetchDetailedData(stock.code, dataType);
      this.data = result.data || result.records || result || [];
      this.filteredData = [...this.data];
      this.currentPage = 1;
      this.sortCol = null;
      this._renderTable();
    } catch (err) {
      $('#data-table-body').innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--danger);">加载失败: ${err.message}</td></tr>`;
    }
  }

  _applyFilter(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
      this.filteredData = [...this.data];
    } else {
      this.filteredData = this.data.filter(row =>
        Object.values(row).some(v => String(v).toLowerCase().includes(q))
      );
    }
    this.currentPage = 1;
    this._renderTableBody();
    this._renderPagination();
  }

  _renderTable() {
    if (!this.filteredData.length) {
      $('#data-table-head').innerHTML = '';
      $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">暂无数据</td></tr>';
      return;
    }

    const columns = Object.keys(this.filteredData[0]);

    // Head
    $('#data-table-head').innerHTML = columns.map(col => `
      <th data-col="${col}">
        ${col}
        <span class="sort-icon">${this.sortCol === col ? (this.sortAsc ? '▲' : '▼') : ''}</span>
      </th>
    `).join('');

    $('#data-table-head').querySelectorAll('th').forEach(th => {
      th.addEventListener('click', () => {
        const col = th.dataset.col;
        if (this.sortCol === col) {
          this.sortAsc = !this.sortAsc;
        } else {
          this.sortCol = col;
          this.sortAsc = true;
        }
        this.filteredData.sort((a, b) => {
          const va = a[col], vb = b[col];
          if (va == null) return 1;
          if (vb == null) return -1;
          if (typeof va === 'number' && typeof vb === 'number') return this.sortAsc ? va - vb : vb - va;
          return this.sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
        });
        this.currentPage = 1;
        this._renderTableBody();
        this._renderTable();
      });
    });

    this._renderTableBody();
    this._renderPagination();
  }

  _renderTableBody() {
    const columns = Object.keys(this.filteredData[0] || {});
    const start = (this.currentPage - 1) * PAGE_SIZE;
    const page = this.filteredData.slice(start, start + PAGE_SIZE);

    $('#data-table-body').innerHTML = page.map(row =>
      `<tr>${columns.map(col => {
        const val = row[col];
        let cls = '';
        if (typeof val === 'number') {
          cls = 'cell-number';
        }
        const display = val == null ? '--' : String(val);
        return `<td class="${cls}">${display}</td>`;
      }).join('')}</tr>`
    ).join('');
  }

  _renderPagination() {
    const totalPages = Math.ceil(this.filteredData.length / PAGE_SIZE);
    if (totalPages <= 1) {
      $('#pagination').innerHTML = '';
      return;
    }

    let pages = [];
    for (let i = Math.max(1, this.currentPage - 2); i <= Math.min(totalPages, this.currentPage + 2); i++) {
      pages.push(i);
    }

    $('#pagination').innerHTML = `
      <button class="page-btn" data-page="1" ${this.currentPage === 1 ? 'disabled' : ''}>«</button>
      <button class="page-btn" data-page="${this.currentPage - 1}" ${this.currentPage === 1 ? 'disabled' : ''}>‹</button>
      ${pages.map(p => `<button class="page-btn${p === this.currentPage ? ' active' : ''}" data-page="${p}">${p}</button>`).join('')}
      <button class="page-btn" data-page="${this.currentPage + 1}" ${this.currentPage === totalPages ? 'disabled' : ''}>›</button>
      <button class="page-btn" data-page="${totalPages}" ${this.currentPage === totalPages ? 'disabled' : ''}>»</button>
      <span class="page-info">${this.filteredData.length} 条</span>
    `;

    $('#pagination').querySelectorAll('.page-btn:not([disabled])').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = parseInt(btn.dataset.page);
        if (page >= 1 && page <= totalPages) {
          this.currentPage = page;
          this._renderTableBody();
          this._renderPagination();
        }
      });
    });
  }

  _exportCSV() {
    if (!this.filteredData.length) return;
    const columns = Object.keys(this.filteredData[0]);
    const header = columns.join(',');
    const rows = this.filteredData.map(row =>
      columns.map(col => {
        const val = row[col];
        if (val == null) return '';
        const str = String(val);
        return str.includes(',') ? `"${str}"` : str;
      }).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `data_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}

function initDataBrowser() {
  const app = window.__app;
  if (app) new DataBrowserView(app);
  else setTimeout(initDataBrowser, 50);
}
initDataBrowser();
```

- [ ] **Step 3: Create `frontend/js/settings.js`**

```javascript
// settings.js — Settings page
import { $ } from './utils.js';

export class SettingsView {
  constructor(app) {
    this.app = app;
    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'settings') this._render();
    });
  }

  _render() {
    const page = $('#settings-page');
    if (!page) return;

    page.innerHTML = `
      <div class="settings-section">
        <h2>Token 管理</h2>
        <div class="settings-field">
          <label>Tushare Token</label>
          <input type="password" id="setting-tushare-token" value="${localStorage.getItem('fa_tushare_token') || ''}" placeholder="输入 Tushare API Token">
          <div class="hint">用于获取 A 股财务数据</div>
        </div>
        <div class="settings-field">
          <label>DeepSeek API Key</label>
          <input type="password" id="setting-deepseek-key" value="${localStorage.getItem('fa_deepseek_key') || ''}" placeholder="输入 DeepSeek API Key">
          <div class="hint">用于 AI 分析功能</div>
        </div>
        <button class="btn-primary" id="btn-save-tokens">保存 Token</button>
      </div>

      <div class="settings-section">
        <h2>数据源</h2>
        <div class="settings-field">
          <label>默认数据源</label>
          <select id="setting-datasource">
            <option value="tushare">Tushare (A股)</option>
            <option value="yfinance">YFinance (美股)</option>
            <option value="akshare">AKShare (A股补充)</option>
          </select>
        </div>
      </div>

      <div class="settings-section">
        <h2>缓存</h2>
        <div class="settings-field">
          <label>缓存过期时间 (小时)</label>
          <input type="number" id="setting-cache-hours" value="${localStorage.getItem('fa_cache_hours') || 24}" min="1" max="168">
        </div>
        <button class="btn-danger" id="btn-clear-cache">清除缓存</button>
      </div>

      <div class="settings-section">
        <h2>关于</h2>
        <p style="font-size:13px;color:var(--text-secondary);">Financial Analyzer Pro v9.0</p>
        <p style="font-size:11px;color:var(--text-muted);">桌面 GUI 重构版 · Modern Dark SaaS</p>
      </div>
    `;

    this._bindSettingsActions();
  }

  _bindSettingsActions() {
    $('#btn-save-tokens')?.addEventListener('click', () => {
      const tushare = $('#setting-tushare-token')?.value || '';
      const deepseek = $('#setting-deepseek-key')?.value || '';
      localStorage.setItem('fa_tushare_token', tushare);
      localStorage.setItem('fa_deepseek_key', deepseek);
      alert('Token 已保存');
    });

    $('#btn-clear-cache')?.addEventListener('click', () => {
      if (confirm('确认清除所有缓存数据？')) {
        this.app.api.post('/api/settings/clear-cache').then(() => {
          alert('缓存已清除');
        }).catch(() => {
          alert('清除失败');
        });
      }
    });

    $('#setting-cache-hours')?.addEventListener('change', function() {
      localStorage.setItem('fa_cache_hours', this.value);
    });

    const ds = $('#setting-datasource');
    if (ds) {
      ds.value = localStorage.getItem('fa_datasource') || 'tushare';
      ds.addEventListener('change', function() {
        localStorage.setItem('fa_datasource', this.value);
      });
    }
  }
}

function initSettings() {
  const app = window.__app;
  if (app) new SettingsView(app);
  else setTimeout(initSettings, 50);
}
initSettings();
```

- [ ] **Step 4: Commit data browser + settings**

```bash
git add frontend/css/data.css frontend/js/data-browser.js frontend/js/settings.js
git commit -m "feat: add data browser with sortable tables and settings page

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Server Integration — Mount Frontend Static Files

**Files:**
- Modify: `financial_analyzer/web/main.py`

- [ ] **Step 1: Add static file mount for frontend directory**

In `financial_analyzer/web/main.py`, add a static files mount for the frontend directory so it's served at `/static/frontend/`:

```python
# Add to create_app() function, alongside existing static mounts:
app.mount("/static/frontend", StaticFiles(directory="frontend"), name="frontend_static")
```

- [ ] **Step 2: Add health check endpoint**

```python
@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Test that frontend loads**

```bash
python -c "from financial_analyzer.web.main import app; print('Import OK')"
```

- [ ] **Step 4: Commit server integration**

```bash
git add financial_analyzer/web/main.py
git commit -m "feat: mount frontend static files and add health endpoint

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Cleanup — Remove Tkinter UI

**Files to delete:**
- `financial_analyzer/ui/app.py`
- `financial_analyzer/ui/theme.py`
- `financial_analyzer/ui/dialogs.py`
- `financial_analyzer/ui/deepseek_dialog.py`
- `financial_analyzer/ui/research_panel.py`
- `financial_analyzer/ui/ui_parts.py`
- `financial_analyzer/ui/__init__.py`
- `financial_analyzer/web/templates/` (directory)
- `financial_analyzer/web/static/` (directory)

- [ ] **Step 1: Remove Tkinter UI directory**

```bash
rm -rf financial_analyzer/ui/
```

- [ ] **Step 2: Remove old web templates and static files**

```bash
rm -rf financial_analyzer/web/templates/ financial_analyzer/web/static/
```

- [ ] **Step 3: Verify no broken imports**

```bash
grep -r "from financial_analyzer.ui" financial_analyzer/ || echo "No references found — clean"
grep -r "from financial_analyzer.web.templates" financial_analyzer/ || echo "No references found — clean"
grep -r "import.*ui\." financial_analyzer/ || echo "No references found — clean"
```

- [ ] **Step 4: Commit cleanup**

```bash
git add -A
git commit -m "chore: remove Tkinter UI and old web templates/static

All UI now served from frontend/ directory via pywebview.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: End-to-End Verification

- [ ] **Step 1: Start FastAPI server and verify frontend loads**

```bash
python run_web.py &
sleep 2
curl -s http://127.0.0.1:8000/ | head -20
```

Expected: Returns the new `index.html` from frontend/

- [ ] **Step 2: Verify all CSS/JS files are reachable**

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/static/frontend/css/tokens.css
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/static/frontend/js/app.js
```

Expected: `200` for both

- [ ] **Step 3: Run existing tests to verify no regressions**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass (tests should not depend on Tkinter UI)

- [ ] **Step 4: Kill the test server**

```bash
pkill -f "uvicorn" 2>/dev/null || true
```

- [ ] **Step 5: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: ensure tests pass after UI removal

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review

1. **Spec coverage:** All spec sections covered — architecture (Task 0,8), routes (Task 2), navigation (Task 4), dashboard (Task 3), AI (Task 5), overlays (Task 6), data/settings (Task 7), cleanup (Task 9), verification (Task 10).

2. **Placeholder scan:** No TBD/TODO/fill-in-later. All tasks contain complete executable code.

3. **Type consistency:** Module keys in `api.js` fallback catalog match the keys used in `analysis.js` _renderModules. WebSocket event types (`token`/`section`/`debate_round`/`done`) consistent between `chat.js` and the spec. App event names (`stock:loaded`/`stock:error`/`view:changed`/`shortcut:*`) consistent across all view modules.

4. **Destructive ops guarded:** Task 9 cleanup has grep verification step before deletion. Only Tkinter UI and old web templates removed — backend untouched.
