# Cycle 1 — 修复 quant.js 初始化竞态条件

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复直接访问 `#/quant` 时，`view:changed` 事件在 quant.js 监听器绑定前触发导致的数据加载失败问题。

**问题根因:** 执行顺序竞态条件

---

## 竞态条件分析

### 执行时间线

```
t=0ms   bundle.js IIFE 执行:
          App.init() → router.start() → _handleRoute() → _activateView()
          → window.dispatchEvent('viewchange', {view:'quant'})
          ⚠ 此时 _bindViewChanges() 尚未调用，viewchange 事件无人监听
          → window.__app = app

t=0ms   quant.js IIFE 执行:
          window.__app 已就绪 → initPanel()
          → renderShell() + bindEvents()
          → app.on('view:changed', ...) 注册监听器 ✓
          但 view:changed 事件从未被触发（因为 _bindViewChanges 未就绪）

t=???ms _checkTokenAndWelcome() 的 API 调用返回:
          → _afterWelcomeInit() → _bindViewChanges()
          此时才建立 window 'viewchange' → app 'view:changed' 的桥接
          但初始路由事件已经丢失
```

### 关键代码路径

1. **bundle.js line 2130:** `app.init()` 调用 `router.start()`
2. **bundle.js line 349:** `router.start()` 对已有 hash 调用 `_handleRoute()`
3. **bundle.js line 390:** `_handleRoute()` 调用 `_activateView()`
4. **bundle.js line 417-419:** `_activateView()` 派发 `window 'viewchange'` 事件
5. **bundle.js line 2106-2111:** `_bindViewChanges()` 建立桥接（尚未调用！）
6. **quant.js line 31-38:** `app.on('view:Changed', ...)` 注册监听器

### 结果

直接导航到 `#/quant` 时，quant 面板显示为空——无股票池、无因子、无模拟交易数据。

---

## Task 1: 在 quant.js initPanel() 中添加路由检查

**文件:** `frontend/js/quant.js`
**位置:** `initPanel()` 函数内，`app.on('view:changed', ...)` 监听器注册之后（第 38 行之后）

**变更:** 添加 4 行代码，在监听器注册完成后立即检查当前路由，如果已在 quant 视图则手动触发数据加载。

**具体插入位置:** 在第 38 行 `});` 之后，第 40 行 `// ==================== Render ====================` 之前

**插入代码:**
```javascript
    // Check if we're already on the quant view (handles direct URL navigation)
    // This fixes the race condition where view:changed fires before this listener is bound
    if (window.location.hash === '#/quant' || window.location.hash === '#quant') {
      loadPools();
      loadFactors();
      loadPaperPortfolio();
      loadPaperLedger();
    }
```

**为什么需要检查两种 hash 格式:**
- `#/quant` — Router 标准格式（`Router._handleRoute` 使用 `hash.slice(1)` 去掉 `#`）
- `#quant` — 防御性检查，用户可能手动输入不带斜杠的 hash

**为什么直接调用 load 函数是安全的:**
- `loadPools()`, `loadFactors()`, `loadPaperPortfolio()`, `loadPaperLedger()` 都是独立的 fetch 调用
- 它们不依赖任何状态，只操作 DOM 容器
- 如果 API 返回错误，每个函数内部都有 `.catch()` 处理
- `renderShell()` 已经在前面调用，DOM 容器已就绪

**验证步骤:**
1. 启动应用后直接在浏览器地址栏输入 `http://localhost:PORT/#/quant`
2. 确认股票池下拉框有选项（非空）
3. 确认因子权重面板有内容（非 "因子加载失败"）
4. 确认模拟交易区域有初始化按钮响应
5. 打开浏览器控制台，确认无 JavaScript 错误
6. 确认从其他视图切换到 quant 视图仍然正常工作（不重复加载）

---

## 执行顺序

```text
Task 1 — 单一文件修改，无依赖
```

仅需修改一个文件的一处位置。这是一个小而精确的修复。

---

## 测试要点

- **直接访问 `#/quant`:** 数据应自动加载（股票池、因子、模拟交易）
- **从其他视图导航到 quant:** 应通过 `view:changed` 事件正常加载（不重复）
- **访问 `#/quant` 后刷新页面:** 应正常加载
- **访问 `#/dashboard` 然后切换到 quant:** 应正常加载
- **quant.js 加载失败时:** 不应影响其他视图
- **API 不可用时:** 应显示错误 toast，不应崩溃
