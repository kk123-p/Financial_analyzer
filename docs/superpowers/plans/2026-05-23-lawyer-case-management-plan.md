# 律师案件流程管理系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建独立的 Electron + React 桌面应用，管理律师诉讼案件（11阶段流程）和非诉项目，包含日历视图、文档管理和截止日期提醒。

**Architecture:** Electron 主进程管理 SQLite 数据库和系统通知，React 渲染进程提供 UI。IPC 通过 contextBridge 安全暴露 API。Vite 负责前端构建，Tailwind CSS 处理样式。

**Tech Stack:** Electron 28+, React 18, Vite 5, Tailwind CSS 3, better-sqlite3, react-router-dom v6, node-cron, electron-builder, xlsx, jspdf

**项目根目录:** `C:/Users/LK/Desktop/日程管理`

---

## 文件结构

```
日程管理/
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html                         # Vite 入口 HTML
├── electron/
│   ├── main.js                        # Electron 主进程入口
│   ├── preload.js                     # contextBridge IPC 暴露
│   └── database/
│       ├── connection.js              # SQLite 连接 + 初始化
│       ├── migrations.js              # 建表迁移
│       ├── cases.js                   # 案件 CRUD
│       ├── stages.js                  # 阶段 CRUD
│       ├── projects.js                # 非诉项目 CRUD
│       ├── tasks.js                   # 项目任务 CRUD
│       ├── templates.js               # 模板 CRUD + 预设数据
│       ├── documents.js               # 文档记录 CRUD
│       └── reminders.js               # 提醒 CRUD + 调度扫描
├── src/
│   ├── main.jsx                       # React 入口
│   ├── App.jsx                        # 路由 + 布局
│   ├── index.css                      # Tailwind 指令 + 自定义样式
│   ├── pages/
│   │   ├── Dashboard.jsx              # 仪表盘首页
│   │   ├── CaseList.jsx               # 案件列表
│   │   ├── CaseDetail.jsx             # 案件详情 (时间线)
│   │   ├── CalendarView.jsx           # 月历 + 日程
│   │   ├── ProjectList.jsx            # 非诉项目列表
│   │   ├── ProjectDetail.jsx          # 项目详情 (任务)
│   │   ├── TemplateManager.jsx        # 模板管理
│   │   └── Settings.jsx               # 设置页
│   └── components/
│       ├── Sidebar.jsx                # 侧边栏导航
│       ├── StatsCard.jsx              # 统计卡片
│       ├── StageTimeline.jsx          # 垂直时间线
│       ├── MonthCalendar.jsx          # 月历组件
│       ├── TaskList.jsx               # 可勾选任务列表
│       ├── DocumentList.jsx           # 文档列表
│       ├── CaseFormModal.jsx          # 新建/编辑案件弹窗
│       ├── ProjectFormModal.jsx       # 新建/编辑项目弹窗
│       └── ConfirmDialog.jsx          # 确认删除对话框
└── assets/
    └── icon.png                       # 应用图标 (占位)
```

---

### Task 1: 项目脚手架 — package.json + 构建配置

**Files:**
- Create: `C:/Users/LK/Desktop/日程管理/package.json`
- Create: `C:/Users/LK/Desktop/日程管理/vite.config.js`
- Create: `C:/Users/LK/Desktop/日程管理/tailwind.config.js`
- Create: `C:/Users/LK/Desktop/日程管理/postcss.config.js`
- Create: `C:/Users/LK/Desktop/日程管理/index.html`

- [ ] **Step 1: 创建项目目录**

Run: `mkdir "C:/Users/LK/Desktop/日程管理"`

- [ ] **Step 2: 编写 package.json**

```json
{
  "name": "lawyer-cms",
  "version": "1.0.0",
  "description": "律师案件流程管理系统",
  "main": "electron/main.js",
  "scripts": {
    "dev": "concurrently \"vite\" \"wait-on http://localhost:5173 && electron .\"",
    "build": "vite build && electron-builder",
    "vite:dev": "vite",
    "electron:dev": "electron ."
  },
  "dependencies": {
    "better-sqlite3": "^11.0.0",
    "node-cron": "^3.0.3",
    "xlsx": "^0.18.5",
    "jspdf": "^2.5.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "concurrently": "^8.2.2",
    "electron": "^28.2.0",
    "electron-builder": "^24.9.1",
    "postcss": "^8.4.33",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.3",
    "tailwindcss": "^3.4.1",
    "vite": "^5.0.12",
    "wait-on": "^7.2.0"
  },
  "build": {
    "appId": "com.lawyer.cms",
    "productName": "律师工作台",
    "directories": {
      "output": "dist-electron"
    },
    "files": [
      "dist/**/*",
      "electron/**/*",
      "assets/**/*"
    ],
    "win": {
      "target": "nsis",
      "icon": "assets/icon.png"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "language": "2052"
    }
  }
}
```

- [ ] **Step 3: 编写 vite.config.js**

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
  },
});
```

- [ ] **Step 4: 编写 tailwind.config.js**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: { DEFAULT: '#1e293b', hover: '#334155', active: '#0f172a' },
        primary: '#2563eb',
        danger: '#dc2626',
        warning: '#f59e0b',
        success: '#16a34a',
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 5: 编写 postcss.config.js**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: 编写 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>律师工作台</title>
  </head>
  <body class="bg-gray-50 text-gray-900 antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 7: 安装依赖**

Run: `cd "C:/Users/LK/Desktop/日程管理" && npm install`

- [ ] **Step 8: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git init && git add -A && git commit -m "chore: project scaffold with Electron + React + Vite + Tailwind"
```

---

### Task 2: Electron 主进程 + SQLite 数据库初始化

**Files:**
- Create: `C:/Users/LK/Desktop/日程管理/electron/main.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/preload.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/connection.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/migrations.js`

- [ ] **Step 1: 编写 connection.js**

```js
const path = require('path');
const { app } = require('electron');

let db = null;

function getDbPath() {
  const userDataPath = app.getPath('userData');
  return path.join(userDataPath, 'lawyer-cms.db');
}

function getDb() {
  if (db) return db;
  const Database = require('better-sqlite3');
  const dbPath = getDbPath();
  db = new Database(dbPath);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  return db;
}

function closeDb() {
  if (db) {
    db.close();
    db = null;
  }
}

module.exports = { getDb, getDbPath, closeDb };
```

- [ ] **Step 2: 编写 migrations.js**

```js
const { getDb } = require('./connection');

function runMigrations() {
  const db = getDb();

  db.exec(`
    CREATE TABLE IF NOT EXISTS templates (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      category TEXT NOT NULL DEFAULT '诉讼',
      case_type TEXT DEFAULT '',
      project_type TEXT DEFAULT '',
      is_default INTEGER DEFAULT 0,
      description TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now', 'localtime')),
      updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS template_stages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      template_id INTEGER NOT NULL,
      stage_name TEXT NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0,
      is_critical INTEGER DEFAULT 0,
      FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS cases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      case_number TEXT DEFAULT '',
      title TEXT NOT NULL,
      case_type TEXT DEFAULT '民事',
      court TEXT DEFAULT '',
      judge TEXT DEFAULT '',
      plaintiff TEXT DEFAULT '',
      defendant TEXT DEFAULT '',
      filing_date TEXT DEFAULT '',
      closing_date TEXT DEFAULT '',
      status TEXT DEFAULT '进行中',
      notes TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now', 'localtime')),
      updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS case_stages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      case_id INTEGER NOT NULL,
      stage_name TEXT NOT NULL,
      sort_order INTEGER NOT NULL DEFAULT 0,
      planned_start TEXT DEFAULT '',
      planned_end TEXT DEFAULT '',
      actual_start TEXT DEFAULT '',
      actual_end TEXT DEFAULT '',
      status TEXT DEFAULT '待开始',
      notes TEXT DEFAULT '',
      FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      project_type TEXT DEFAULT '法律顾问',
      client TEXT DEFAULT '',
      status TEXT DEFAULT '进行中',
      start_date TEXT DEFAULT '',
      expected_end_date TEXT DEFAULT '',
      actual_end_date TEXT DEFAULT '',
      description TEXT DEFAULT '',
      notes TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now', 'localtime')),
      updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS project_tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      project_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      description TEXT DEFAULT '',
      deadline TEXT DEFAULT '',
      completed_at TEXT DEFAULT '',
      priority TEXT DEFAULT '中',
      status TEXT DEFAULT '待办',
      sort_order INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      case_id INTEGER,
      project_id INTEGER,
      name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      category TEXT DEFAULT '其他',
      file_size INTEGER DEFAULT 0,
      file_type TEXT DEFAULT '',
      upload_date TEXT DEFAULT (datetime('now', 'localtime')),
      notes TEXT DEFAULT '',
      FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS reminders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      target_type TEXT NOT NULL,
      target_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      remind_at TEXT NOT NULL,
      is_dismissed INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE INDEX IF NOT EXISTS idx_case_stages_case ON case_stages(case_id);
    CREATE INDEX IF NOT EXISTS idx_project_tasks_project ON project_tasks(project_id);
    CREATE INDEX IF NOT EXISTS idx_documents_case ON documents(case_id);
    CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
    CREATE INDEX IF NOT EXISTS idx_reminders_target ON reminders(target_type, target_id);
    CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(remind_at, is_dismissed);
  `);
}

module.exports = { runMigrations };
```

- [ ] **Step 3: 编写 preload.js**

```js
const { contextBridge, ipcRenderer, shell } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Cases
  getCases: (filters) => ipcRenderer.invoke('db:cases:list', filters),
  getCase: (id) => ipcRenderer.invoke('db:cases:get', id),
  createCase: (data) => ipcRenderer.invoke('db:cases:create', data),
  updateCase: (id, data) => ipcRenderer.invoke('db:cases:update', id, data),
  deleteCase: (id) => ipcRenderer.invoke('db:cases:delete', id),

  // Stages
  getStages: (caseId) => ipcRenderer.invoke('db:stages:list', caseId),
  updateStage: (id, data) => ipcRenderer.invoke('db:stages:update', id, data),
  reorderStages: (caseId, stageIds) => ipcRenderer.invoke('db:stages:reorder', caseId, stageIds),

  // Projects
  getProjects: (filters) => ipcRenderer.invoke('db:projects:list', filters),
  getProject: (id) => ipcRenderer.invoke('db:projects:get', id),
  createProject: (data) => ipcRenderer.invoke('db:projects:create', data),
  updateProject: (id, data) => ipcRenderer.invoke('db:projects:update', id, data),
  deleteProject: (id) => ipcRenderer.invoke('db:projects:delete', id),

  // Tasks
  getTasks: (projectId) => ipcRenderer.invoke('db:tasks:list', projectId),
  updateTask: (id, data) => ipcRenderer.invoke('db:tasks:update', id, data),
  createTask: (projectId, data) => ipcRenderer.invoke('db:tasks:create', projectId, data),
  deleteTask: (id) => ipcRenderer.invoke('db:tasks:delete', id),
  reorderTasks: (projectId, taskIds) => ipcRenderer.invoke('db:tasks:reorder', projectId, taskIds),

  // Templates
  getTemplates: (category) => ipcRenderer.invoke('db:templates:list', category),
  getTemplateStages: (templateId) => ipcRenderer.invoke('db:templates:stages', templateId),
  createTemplate: (data, stages) => ipcRenderer.invoke('db:templates:create', data, stages),
  updateTemplate: (id, data, stages) => ipcRenderer.invoke('db:templates:update', id, data, stages),
  deleteTemplate: (id) => ipcRenderer.invoke('db:templates:delete', id),

  // Documents
  getDocuments: (caseId, projectId) => ipcRenderer.invoke('db:documents:list', caseId, projectId),
  addDocument: (caseId, projectId) => ipcRenderer.invoke('db:documents:add', caseId, projectId),
  deleteDocument: (id) => ipcRenderer.invoke('db:documents:delete', id),
  openDocument: (filePath) => ipcRenderer.invoke('file:open', filePath),

  // Reminders
  getReminders: (filters) => ipcRenderer.invoke('db:reminders:list', filters),
  dismissReminder: (id) => ipcRenderer.invoke('db:reminders:dismiss', id),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  saveSettings: (data) => ipcRenderer.invoke('settings:save', data),

  // Export
  exportExcel: (data) => ipcRenderer.invoke('export:excel', data),
  exportPdf: (data) => ipcRenderer.invoke('export:pdf', data),

  // Shell
  openExternal: (url) => shell.openExternal(url),
});
```

- [ ] **Step 4: 编写 main.js**

```js
const { app, BrowserWindow, ipcMain, Notification, shell, dialog } = require('electron');
const path = require('path');
const { getDb, closeDb } = require('./database/connection');
const { runMigrations } = require('./database/migrations');
const { registerCaseHandlers } = require('./database/cases');
const { registerStageHandlers } = require('./database/stages');
const { registerProjectHandlers } = require('./database/projects');
const { registerTaskHandlers } = require('./database/tasks');
const { registerTemplateHandlers } = require('./database/templates');
const { registerDocumentHandlers } = require('./database/documents');
const { registerReminderHandlers, startReminderScheduler } = require('./database/reminders');

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    title: '律师工作台',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (process.env.NODE_ENV === 'development' || process.argv.includes('--dev')) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }
}

app.whenReady().then(() => {
  runMigrations();
  registerCaseHandlers(ipcMain);
  registerStageHandlers(ipcMain);
  registerProjectHandlers(ipcMain);
  registerTaskHandlers(ipcMain);
  registerTemplateHandlers(ipcMain);
  registerDocumentHandlers(ipcMain);
  registerReminderHandlers(ipcMain);
  startReminderScheduler();

  // Settings store (simple JSON file in userData)
  ipcMain.handle('settings:get', async () => {
    const fs = require('fs');
    const settingsPath = path.join(app.getPath('userData'), 'settings.json');
    try {
      const raw = fs.readFileSync(settingsPath, 'utf-8');
      return JSON.parse(raw);
    } catch {
      return { reminderDays: [1, 3, 7] };
    }
  });

  ipcMain.handle('settings:save', async (_e, data) => {
    const fs = require('fs');
    const settingsPath = path.join(app.getPath('userData'), 'settings.json');
    fs.writeFileSync(settingsPath, JSON.stringify(data, null, 2));
    return true;
  });

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  closeDb();
  if (process.platform !== 'darwin') app.quit();
});
```

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: Electron main process with SQLite migrations and IPC bridge"
```

---

### Task 3: 数据库 CRUD — cases + stages

**Files:**
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/cases.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/stages.js`

- [ ] **Step 1: 编写 cases.js**

```js
const { getDb } = require('./connection');

function registerCaseHandlers(ipcMain) {
  ipcMain.handle('db:cases:list', (_e, filters = {}) => {
    const db = getDb();
    let sql = 'SELECT * FROM cases WHERE 1=1';
    const params = [];

    if (filters.status) {
      sql += ' AND status = ?';
      params.push(filters.status);
    }
    if (filters.case_type) {
      sql += ' AND case_type = ?';
      params.push(filters.case_type);
    }
    if (filters.search) {
      sql += ' AND (title LIKE ? OR case_number LIKE ? OR plaintiff LIKE ? OR defendant LIKE ?)';
      const q = `%${filters.search}%`;
      params.push(q, q, q, q);
    }

    sql += ' ORDER BY updated_at DESC';
    return db.prepare(sql).all(...params);
  });

  ipcMain.handle('db:cases:get', (_e, id) => {
    const db = getDb();
    return db.prepare('SELECT * FROM cases WHERE id = ?').get(id);
  });

  ipcMain.handle('db:cases:create', async (_e, data) => {
    const db = getDb();
    const result = db.prepare(`
      INSERT INTO cases (case_number, title, case_type, court, judge, plaintiff, defendant, filing_date, status, notes)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      data.case_number || '', data.title, data.case_type || '民事',
      data.court || '', data.judge || '', data.plaintiff || '',
      data.defendant || '', data.filing_date || '', '进行中', data.notes || ''
    );

    // 如果指定了模板，套用模板阶段
    if (data.template_id) {
      const stages = db.prepare(
        'SELECT * FROM template_stages WHERE template_id = ? ORDER BY sort_order'
      ).all(data.template_id);
      const insertStage = db.prepare(
        'INSERT INTO case_stages (case_id, stage_name, sort_order, status) VALUES (?, ?, ?, ?)'
      );
      for (const s of stages) {
        insertStage.run(result.lastInsertRowid, s.stage_name, s.sort_order, '待开始');
      }
      // 为关键节点创建提醒
      if (data.reminder_days) {
        // handled by frontend creating reminders explicitly
      }
    }

    return result.lastInsertRowid;
  });

  ipcMain.handle('db:cases:update', (_e, id, data) => {
    const db = getDb();
    db.prepare(`
      UPDATE cases SET case_number=?, title=?, case_type=?, court=?, judge=?,
      plaintiff=?, defendant=?, filing_date=?, closing_date=?, status=?, notes=?,
      updated_at=datetime('now','localtime')
      WHERE id=?
    `).run(
      data.case_number, data.title, data.case_type, data.court, data.judge,
      data.plaintiff, data.defendant, data.filing_date, data.closing_date || '',
      data.status, data.notes, id
    );
    return true;
  });

  ipcMain.handle('db:cases:delete', (_e, id) => {
    const db = getDb();
    db.prepare('DELETE FROM cases WHERE id = ?').run(id);
    return true;
  });
}

module.exports = { registerCaseHandlers };
```

- [ ] **Step 2: 编写 stages.js**

```js
const { getDb } = require('./connection');

function registerStageHandlers(ipcMain) {
  ipcMain.handle('db:stages:list', (_e, caseId) => {
    const db = getDb();
    return db.prepare(
      'SELECT * FROM case_stages WHERE case_id = ? ORDER BY sort_order'
    ).all(caseId);
  });

  ipcMain.handle('db:stages:update', (_e, id, data) => {
    const db = getDb();
    db.prepare(`
      UPDATE case_stages SET stage_name=?, planned_start=?, planned_end=?,
      actual_start=?, actual_end=?, status=?, notes=?, sort_order=?
      WHERE id=?
    `).run(
      data.stage_name, data.planned_start, data.planned_end,
      data.actual_start, data.actual_end, data.status, data.notes,
      data.sort_order, id
    );

    // 如果阶段状态变为已完成，检查是否所有阶段完成，自动更新案件状态
    if (data.status === '已完成') {
      const stage = db.prepare('SELECT case_id FROM case_stages WHERE id = ?').get(id);
      const pending = db.prepare(
        "SELECT COUNT(*) as cnt FROM case_stages WHERE case_id = ? AND status != '已完成'"
      ).get(stage.case_id);
      if (pending.cnt === 0) {
        db.prepare(
          "UPDATE cases SET status = '已结案', closing_date = date('now','localtime'), updated_at = datetime('now','localtime') WHERE id = ?"
        ).run(stage.case_id);
      }
    }

    return true;
  });

  ipcMain.handle('db:stages:reorder', (_e, caseId, stageIds) => {
    const db = getDb();
    const stmt = db.prepare('UPDATE case_stages SET sort_order = ? WHERE id = ? AND case_id = ?');
    const tx = db.transaction(() => {
      stageIds.forEach((id, index) => stmt.run(index, id, caseId));
    });
    tx();
    return true;
  });
}

module.exports = { registerStageHandlers };
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: add cases and stages CRUD handlers"
```

---

### Task 4: 数据库 CRUD — projects + tasks

**Files:**
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/projects.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/tasks.js`

- [ ] **Step 1: 编写 projects.js**

```js
const { getDb } = require('./connection');

function registerProjectHandlers(ipcMain) {
  ipcMain.handle('db:projects:list', (_e, filters = {}) => {
    const db = getDb();
    let sql = 'SELECT * FROM projects WHERE 1=1';
    const params = [];
    if (filters.status) { sql += ' AND status = ?'; params.push(filters.status); }
    if (filters.project_type) { sql += ' AND project_type = ?'; params.push(filters.project_type); }
    if (filters.search) {
      sql += ' AND (name LIKE ? OR client LIKE ?)';
      const q = `%${filters.search}%`;
      params.push(q, q);
    }
    sql += ' ORDER BY updated_at DESC';
    return db.prepare(sql).all(...params);
  });

  ipcMain.handle('db:projects:get', (_e, id) => {
    const db = getDb();
    return db.prepare('SELECT * FROM projects WHERE id = ?').get(id);
  });

  ipcMain.handle('db:projects:create', (_e, data) => {
    const db = getDb();
    const result = db.prepare(`
      INSERT INTO projects (name, project_type, client, status, start_date, expected_end_date, description, notes)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(data.name, data.project_type || '法律顾问', data.client || '', '进行中',
      data.start_date || '', data.expected_end_date || '', data.description || '', data.notes || '');

    if (data.template_id) {
      const stages = db.prepare(
        'SELECT * FROM template_stages WHERE template_id = ? ORDER BY sort_order'
      ).all(data.template_id);
      const insertTask = db.prepare(
        'INSERT INTO project_tasks (project_id, title, sort_order, status) VALUES (?, ?, ?, ?)'
      );
      for (const s of stages) {
        insertTask.run(result.lastInsertRowid, s.stage_name, s.sort_order, '待办');
      }
    }
    return result.lastInsertRowid;
  });

  ipcMain.handle('db:projects:update', (_e, id, data) => {
    const db = getDb();
    db.prepare(`
      UPDATE projects SET name=?, project_type=?, client=?, status=?, start_date=?,
      expected_end_date=?, actual_end_date=?, description=?, notes=?,
      updated_at=datetime('now','localtime') WHERE id=?
    `).run(data.name, data.project_type, data.client, data.status, data.start_date,
      data.expected_end_date, data.actual_end_date || '', data.description, data.notes, id);
    return true;
  });

  ipcMain.handle('db:projects:delete', (_e, id) => {
    const db = getDb();
    db.prepare('DELETE FROM projects WHERE id = ?').run(id);
    return true;
  });
}

module.exports = { registerProjectHandlers };
```

- [ ] **Step 2: 编写 tasks.js**

```js
const { getDb } = require('./connection');

function registerTaskHandlers(ipcMain) {
  ipcMain.handle('db:tasks:list', (_e, projectId) => {
    const db = getDb();
    return db.prepare(
      'SELECT * FROM project_tasks WHERE project_id = ? ORDER BY sort_order'
    ).all(projectId);
  });

  ipcMain.handle('db:tasks:create', (_e, projectId, data) => {
    const db = getDb();
    const maxSort = db.prepare(
      'SELECT MAX(sort_order) as mx FROM project_tasks WHERE project_id = ?'
    ).get(projectId);
    const sortOrder = (maxSort?.mx ?? -1) + 1;
    db.prepare(`
      INSERT INTO project_tasks (project_id, title, description, deadline, priority, status, sort_order)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(projectId, data.title, data.description || '', data.deadline || '',
      data.priority || '中', '待办', sortOrder);
    return true;
  });

  ipcMain.handle('db:tasks:update', (_e, id, data) => {
    const db = getDb();
    db.prepare(`
      UPDATE project_tasks SET title=?, description=?, deadline=?, completed_at=?,
      priority=?, status=?, sort_order=? WHERE id=?
    `).run(data.title, data.description, data.deadline, data.completed_at || '',
      data.priority, data.status, data.sort_order, id);

    if (data.status === '已完成') {
      const task = db.prepare('SELECT project_id FROM project_tasks WHERE id = ?').get(id);
      const pending = db.prepare(
        "SELECT COUNT(*) as cnt FROM project_tasks WHERE project_id = ? AND status != '已完成'"
      ).get(task.project_id);
      if (pending.cnt === 0) {
        db.prepare(
          "UPDATE projects SET status = '已完成', actual_end_date = date('now','localtime'), updated_at = datetime('now','localtime') WHERE id = ?"
        ).run(task.project_id);
      }
    }
    return true;
  });

  ipcMain.handle('db:tasks:delete', (_e, id) => {
    const db = getDb();
    db.prepare('DELETE FROM project_tasks WHERE id = ?').run(id);
    return true;
  });

  ipcMain.handle('db:tasks:reorder', (_e, projectId, taskIds) => {
    const db = getDb();
    const stmt = db.prepare('UPDATE project_tasks SET sort_order = ? WHERE id = ? AND project_id = ?');
    const tx = db.transaction(() => {
      taskIds.forEach((id, index) => stmt.run(index, id, projectId));
    });
    tx();
    return true;
  });
}

module.exports = { registerTaskHandlers };
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: add projects and tasks CRUD handlers"
```

---

### Task 5: 数据库 CRUD — templates + documents + reminders

**Files:**
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/templates.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/documents.js`
- Create: `C:/Users/LK/Desktop/日程管理/electron/database/reminders.js`

- [ ] **Step 1: 编写 templates.js**

```js
const { getDb } = require('./connection');

const DEFAULT_TEMPLATES = [
  {
    name: '民事诉讼标准流程',
    category: '诉讼',
    case_type: '民事',
    is_default: 1,
    stages: [
      '委托谈判', '签合同', '立案', '保全', '庭前准备',
      '收集证据', '预判对方证据', '开庭审理', '庭后答复', '调解判决', '归档'
    ],
    critical: ['签合同', '立案', '保全', '收集证据', '开庭审理', '庭后答复', '调解判决'],
  },
  {
    name: '刑事诉讼流程',
    category: '诉讼',
    case_type: '刑事',
    is_default: 1,
    stages: ['委托谈判', '签合同', '侦查阶段', '审查起诉', '阅卷', '庭前准备', '开庭审理', '庭后答复', '判决', '归档'],
    critical: ['签合同', '审查起诉', '开庭审理', '判决'],
  },
  {
    name: '法律顾问标准流程',
    category: '非诉',
    project_type: '法律顾问',
    is_default: 1,
    stages: ['需求沟通', '材料收集', '法律检索', '出具意见', '客户确认', '归档'],
    critical: ['出具意见'],
  },
  {
    name: '尽职调查流程',
    category: '非诉',
    project_type: '尽职调查',
    is_default: 1,
    stages: ['项目启动', '资料清单发出', '现场尽调', '尽调报告撰写', '报告审核', '交付归档'],
    critical: ['尽调报告撰写', '交付归档'],
  },
];

function seedDefaultTemplates() {
  const db = getDb();
  const existing = db.prepare('SELECT COUNT(*) as cnt FROM templates').get();
  if (existing.cnt > 0) return;

  const insertTpl = db.prepare(
    'INSERT INTO templates (name, category, case_type, project_type, is_default, description) VALUES (?, ?, ?, ?, ?, ?)'
  );
  const insertStage = db.prepare(
    'INSERT INTO template_stages (template_id, stage_name, sort_order, is_critical) VALUES (?, ?, ?, ?)'
  );

  for (const tpl of DEFAULT_TEMPLATES) {
    const result = insertTpl.run(tpl.name, tpl.category, tpl.case_type || '', tpl.project_type || '', 1, '');
    tpl.stages.forEach((name, idx) => {
      insertStage.run(result.lastInsertRowid, name, idx, tpl.critical.includes(name) ? 1 : 0);
    });
  }
}

function registerTemplateHandlers(ipcMain) {
  ipcMain.handle('db:templates:list', (_e, category) => {
    const db = getDb();
    if (category) {
      return db.prepare('SELECT * FROM templates WHERE category = ? ORDER BY is_default DESC, id').all(category);
    }
    return db.prepare('SELECT * FROM templates ORDER BY category, is_default DESC, id').all();
  });

  ipcMain.handle('db:templates:stages', (_e, templateId) => {
    const db = getDb();
    return db.prepare(
      'SELECT * FROM template_stages WHERE template_id = ? ORDER BY sort_order'
    ).all(templateId);
  });

  ipcMain.handle('db:templates:create', (_e, data, stages) => {
    const db = getDb();
    const result = db.prepare(
      'INSERT INTO templates (name, category, case_type, project_type, is_default, description) VALUES (?, ?, ?, ?, 0, ?)'
    ).run(data.name, data.category, data.case_type || '', data.project_type || '', data.description || '');

    const insertStage = db.prepare(
      'INSERT INTO template_stages (template_id, stage_name, sort_order, is_critical) VALUES (?, ?, ?, ?)'
    );
    stages.forEach((s, idx) => insertStage.run(result.lastInsertRowid, s.stage_name, idx, s.is_critical ? 1 : 0));

    return result.lastInsertRowid;
  });

  ipcMain.handle('db:templates:update', (_e, id, data, stages) => {
    const db = getDb();
    db.prepare(
      'UPDATE templates SET name=?, category=?, case_type=?, project_type=?, description=?, updated_at=datetime(\'now\',\'localtime\') WHERE id=?'
    ).run(data.name, data.category, data.case_type || '', data.project_type || '', data.description || '', id);

    if (stages) {
      db.prepare('DELETE FROM template_stages WHERE template_id = ?').run(id);
      const insertStage = db.prepare(
        'INSERT INTO template_stages (template_id, stage_name, sort_order, is_critical) VALUES (?, ?, ?, ?)'
      );
      stages.forEach((s, idx) => insertStage.run(id, s.stage_name, idx, s.is_critical ? 1 : 0));
    }
    return true;
  });

  ipcMain.handle('db:templates:delete', (_e, id) => {
    const db = getDb();
    db.prepare('DELETE FROM templates WHERE id = ?').run(id);
    return true;
  });
}

module.exports = { registerTemplateHandlers, seedDefaultTemplates };
```

In main.js, add `seedDefaultTemplates();` after `runMigrations();`:

```js
const { seedDefaultTemplates } = require('./database/templates');
// ... inside app.whenReady():
runMigrations();
seedDefaultTemplates();
```

- [ ] **Step 2: 编写 documents.js**

```js
const { getDb } = require('./connection');
const path = require('path');
const fs = require('fs');
const { app, dialog } = require('electron');

function registerDocumentHandlers(ipcMain) {
  ipcMain.handle('db:documents:list', (_e, caseId, projectId) => {
    const db = getDb();
    if (caseId) {
      return db.prepare('SELECT * FROM documents WHERE case_id = ? ORDER BY upload_date DESC').all(caseId);
    }
    if (projectId) {
      return db.prepare('SELECT * FROM documents WHERE project_id = ? ORDER BY upload_date DESC').all(projectId);
    }
    return [];
  });

  ipcMain.handle('db:documents:add', async (_e, caseId, projectId) => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: '所有文件', extensions: ['*'] },
        { name: '文档', extensions: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'] },
      ],
    });

    if (result.canceled || result.filePaths.length === 0) return [];

    const db = getDb();
    const userDataPath = app.getPath('userData');
    const targetDir = path.join(userDataPath, 'case-files', String(caseId || projectId || 'general'));
    if (!fs.existsSync(targetDir)) fs.mkdirSync(targetDir, { recursive: true });

    const insertDoc = db.prepare(`
      INSERT INTO documents (case_id, project_id, name, file_path, category, file_size, file_type)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `);

    const added = [];
    for (const srcPath of result.filePaths) {
      const fileName = path.basename(srcPath);
      const destPath = path.join(targetDir, fileName);
      fs.copyFileSync(srcPath, destPath);

      const ext = path.extname(fileName).toLowerCase();
      const stats = fs.statSync(destPath);
      insertDoc.run(caseId || null, projectId || null, fileName, destPath, '其他', stats.size, ext);
      added.push({ name: fileName, file_path: destPath, file_size: stats.size, file_type: ext });
    }

    return added;
  });

  ipcMain.handle('db:documents:delete', (_e, id) => {
    const db = getDb();
    const doc = db.prepare('SELECT * FROM documents WHERE id = ?').get(id);
    if (doc) {
      try { fs.unlinkSync(doc.file_path); } catch (_) {}
      db.prepare('DELETE FROM documents WHERE id = ?').run(id);
    }
    return true;
  });

  ipcMain.handle('file:open', (_e, filePath) => {
    const { shell } = require('electron');
    shell.openPath(filePath);
  });
}

module.exports = { registerDocumentHandlers };
```

- [ ] **Step 3: 编写 reminders.js**

```js
const { getDb } = require('./connection');
const { Notification } = require('electron');
const cron = require('node-cron');

let cronJob = null;

function registerReminderHandlers(ipcMain) {
  ipcMain.handle('db:reminders:list', (_e, filters = {}) => {
    const db = getDb();
    let sql = "SELECT * FROM reminders WHERE 1=1";
    const params = [];
    if (filters.is_dismissed !== undefined) {
      sql += ' AND is_dismissed = ?';
      params.push(filters.is_dismissed);
    }
    if (filters.date) {
      sql += " AND remind_at <= ?";
      params.push(filters.date);
    }
    sql += ' ORDER BY remind_at ASC';
    return db.prepare(sql).all(...params);
  });

  ipcMain.handle('db:reminders:dismiss', (_e, id) => {
    const db = getDb();
    db.prepare('UPDATE reminders SET is_dismissed = 1 WHERE id = ?').run(id);
    return true;
  });
}

function startReminderScheduler() {
  cronJob = cron.schedule('* * * * *', () => {
    const db = getDb();
    const now = new Date().toISOString().slice(0, 16).replace('T', ' ');
    const reminders = db.prepare(
      "SELECT * FROM reminders WHERE is_dismissed = 0 AND remind_at <= ?"
    ).all(now + ':00');

    for (const r of reminders) {
      new Notification({ title: '案件提醒', body: r.title, urgency: 'critical' }).show();
      db.prepare('UPDATE reminders SET is_dismissed = 1 WHERE id = ?').run(r.id);
    }
  });
}

module.exports = { registerReminderHandlers, startReminderScheduler };
```

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: add templates, documents, reminders CRUD handlers with seed data"
```

---

### Task 6: React 入口 + 侧边栏布局 + 路由

**Files:**
- Create: `C:/Users/LK/Desktop/日程管理/src/main.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/index.css`
- Create: `C:/Users/LK/Desktop/日程管理/src/App.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/Sidebar.jsx`

- [ ] **Step 1: 编写 main.jsx**

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
);
```

- [ ] **Step 2: 编写 index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
  overflow: hidden;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #64748b; }
```

- [ ] **Step 3: 编写 Sidebar.jsx**

```jsx
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: '仪表盘', icon: '📊' },
  { to: '/cases', label: '案件列表', icon: '📋' },
  { to: '/calendar', label: '日历视图', icon: '📅' },
  { to: '/projects', label: '非诉项目', icon: '📁' },
  { to: '/templates', label: '模板管理', icon: '📄' },
  { to: '/settings', label: '设置', icon: '⚙' },
];

export default function Sidebar() {
  return (
    <aside className="w-[180px] min-w-[180px] bg-sidebar text-slate-300 flex flex-col h-screen select-none">
      <div className="px-4 py-5 text-white font-bold text-[15px] border-b border-slate-700">
        ⚖ 律师工作台
      </div>
      <nav className="flex-1 py-3">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 mx-2 rounded text-sm transition-colors ${
                isActive ? 'bg-sidebar-active text-white' : 'hover:bg-sidebar-hover'
              }`
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 4: 编写 App.jsx**

```jsx
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import CaseList from './pages/CaseList';
import CaseDetail from './pages/CaseDetail';
import CalendarView from './pages/CalendarView';
import ProjectList from './pages/ProjectList';
import ProjectDetail from './pages/ProjectDetail';
import TemplateManager from './pages/TemplateManager';
import Settings from './pages/Settings';

export default function App() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-gray-50">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cases" element={<CaseList />} />
          <Route path="/cases/:id" element={<CaseDetail />} />
          <Route path="/calendar" element={<CalendarView />} />
          <Route path="/projects" element={<ProjectList />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/templates" element={<TemplateManager />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 5: 创建占位页面文件（确保能启动）**

为每个 page 创建最小占位：

```jsx
// src/pages/Dashboard.jsx
export default function Dashboard() {
  return <div className="p-6"><h1 className="text-xl font-bold">仪表盘</h1></div>;
}
```

其余页面 (CaseList, CaseDetail, CalendarView, ProjectList, ProjectDetail, TemplateManager, Settings) 同上结构，替换标题文本。

- [ ] **Step 6: 验证启动**

Run: `cd "C:/Users/LK/Desktop/日程管理" && npx vite` (在另一个终端)
然后检查 localhost:5173 是否显示侧边栏布局

- [ ] **Step 7: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: React shell with sidebar, routing, and placeholder pages"
```

---

### Task 7: 仪表盘页面

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/Dashboard.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/StatsCard.jsx`

- [ ] **Step 1: 编写 StatsCard.jsx**

```jsx
export default function StatsCard({ label, value, color = 'text-gray-900', bgColor = 'bg-white' }) {
  return (
    <div className={`${bgColor} rounded-lg p-4 shadow-sm border border-gray-100`}>
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}
```

- [ ] **Step 2: 编写 Dashboard.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import StatsCard from '../components/StatsCard';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({ activeCases: 0, urgent: 0, todayTasks: 0, archivedMonth: 0 });
  const [todayEvents, setTodayEvents] = useState([]);
  const [recentCases, setRecentCases] = useState([]);

  useEffect(() => {
    (async () => {
      const cases = await window.electronAPI.getCases({});
      const now = new Date();
      const today = now.toISOString().slice(0, 10);

      const active = cases.filter(c => c.status === '进行中');
      const archivedThisMonth = cases.filter(c => {
        if (c.status !== '已归档') return false;
        const d = new Date(c.closing_date || c.updated_at);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
      });

      let urgentCount = 0;
      const events = [];
      for (const c of active) {
        const stages = await window.electronAPI.getStages(c.id);
        for (const s of stages) {
          if (s.status === '进行中' && s.planned_end) {
            const daysLeft = Math.ceil((new Date(s.planned_end) - now) / 86400000);
            if (daysLeft <= 3) urgentCount++;
          }
          if (s.planned_end && s.planned_end.startsWith(today)) {
            events.push({ caseTitle: c.title, stageName: s.stage_name, endDate: s.planned_end, caseId: c.id });
          }
        }
      }

      // Also check project tasks for today
      const projects = await window.electronAPI.getProjects({ status: '进行中' });
      for (const p of projects) {
        const tasks = await window.electronAPI.getTasks(p.id);
        for (const t of tasks) {
          if (t.deadline && t.deadline.startsWith(today) && t.status !== '已完成') {
            events.push({ caseTitle: p.name, stageName: t.title, endDate: t.deadline, projectId: p.id, isTask: true });
          }
        }
      }

      setStats({
        activeCases: active.length,
        urgent: urgentCount,
        todayTasks: events.length,
        archivedMonth: archivedThisMonth.length,
      });

      setTodayEvents(events);
      setRecentCases(cases.slice(0, 5));
    })();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold text-gray-800 mb-5">仪表盘</h1>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatsCard label="进行中案件" value={stats.activeCases} color="text-blue-600" />
        <StatsCard label="临近截止" value={stats.urgent} color="text-red-500" />
        <StatsCard label="今日待办" value={stats.todayTasks} color="text-amber-500" />
        <StatsCard label="本月归档" value={stats.archivedMonth} color="text-green-600" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="font-semibold text-sm text-gray-700 mb-3">今日日程</div>
          {todayEvents.length === 0 ? (
            <p className="text-sm text-gray-400">今日暂无日程安排</p>
          ) : (
            <div className="space-y-2">
              {todayEvents.map((e, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 text-sm py-2 border-b border-gray-50 cursor-pointer hover:bg-gray-50 rounded px-2"
                  onClick={() => navigate(e.isTask ? `/projects/${e.projectId}` : `/cases/${e.caseId}`)}
                >
                  <span className={e.isTask ? 'text-blue-500' : 'text-amber-500'}>●</span>
                  <span className="text-gray-700">{e.stageName}</span>
                  <span className="text-gray-400 text-xs ml-auto">{e.caseTitle}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-sm border p-4">
          <div className="font-semibold text-sm text-gray-700 mb-3">最近案件</div>
          <div className="space-y-2">
            {recentCases.map(c => (
              <div
                key={c.id}
                className="flex items-center gap-3 text-sm py-2 border-b border-gray-50 cursor-pointer hover:bg-gray-50 rounded px-2"
                onClick={() => navigate(`/cases/${c.id}`)}
              >
                <span className="text-gray-500">{c.case_number || '无案号'}</span>
                <span className="text-gray-700 flex-1 truncate">{c.title}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  c.status === '进行中' ? 'bg-amber-50 text-amber-700' : 'bg-green-50 text-green-700'
                }`}>{c.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={() => navigate('/cases')}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors"
        >
          + 新建诉讼案件
        </button>
        <button
          onClick={() => navigate('/projects')}
          className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 transition-colors"
        >
          + 新建非诉项目
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: dashboard with stats cards, today's schedule, and recent cases"
```

---

### Task 8: 案件列表页 + 新建/编辑弹窗

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/CaseList.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/CaseFormModal.jsx`

- [ ] **Step 1: 编写 CaseList.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CaseFormModal from '../components/CaseFormModal';

export default function CaseList() {
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingCase, setEditingCase] = useState(null);

  const loadCases = async () => {
    const filters = {};
    if (statusFilter) filters.status = statusFilter;
    if (typeFilter) filters.case_type = typeFilter;
    if (search) filters.search = search;
    const data = await window.electronAPI.getCases(filters);
    setCases(data);
  };

  useEffect(() => { loadCases(); }, [statusFilter, typeFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    loadCases();
  };

  const handleDelete = async (id) => {
    if (!confirm('确定删除此案件？相关阶段和文档将一并删除。')) return;
    await window.electronAPI.deleteCase(id);
    loadCases();
  };

  const statusColors = {
    '进行中': 'bg-amber-50 text-amber-700',
    '已结案': 'bg-blue-50 text-blue-700',
    '已归档': 'bg-green-50 text-green-700',
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold text-gray-800">案件列表</h1>
        <button
          onClick={() => { setEditingCase(null); setShowModal(true); }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          + 新建案件
        </button>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3 mb-4">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索案号、案件名称、当事人..."
          className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm bg-white">
          <option value="">全部状态</option>
          <option value="进行中">进行中</option>
          <option value="已结案">已结案</option>
          <option value="已归档">已归档</option>
        </select>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm bg-white">
          <option value="">全部类型</option>
          <option value="民事">民事</option>
          <option value="刑事">刑事</option>
          <option value="行政">行政</option>
          <option value="执行">执行</option>
        </select>
        <button type="submit" className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">搜索</button>
      </form>

      <div className="bg-white rounded-lg shadow-sm border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-gray-500">
              <th className="px-4 py-3 font-medium">案号</th>
              <th className="px-4 py-3 font-medium">案件名称</th>
              <th className="px-4 py-3 font-medium">类型</th>
              <th className="px-4 py-3 font-medium">法院</th>
              <th className="px-4 py-3 font-medium">状态</th>
              <th className="px-4 py-3 font-medium">收案日期</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {cases.map(c => (
              <tr key={c.id} className="border-b hover:bg-gray-50 cursor-pointer"
                onClick={() => navigate(`/cases/${c.id}`)}>
                <td className="px-4 py-3 text-gray-500">{c.case_number || '-'}</td>
                <td className="px-4 py-3 font-medium">{c.title}</td>
                <td className="px-4 py-3">{c.case_type}</td>
                <td className="px-4 py-3 text-gray-500">{c.court || '-'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[c.status] || ''}`}>{c.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-500">{c.filing_date || '-'}</td>
                <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                  <button onClick={() => { setEditingCase(c); setShowModal(true); }}
                    className="text-blue-600 hover:underline mr-3 text-xs">编辑</button>
                  <button onClick={() => handleDelete(c.id)}
                    className="text-red-500 hover:underline text-xs">删除</button>
                </td>
              </tr>
            ))}
            {cases.length === 0 && (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">暂无案件，点击"新建案件"开始</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <CaseFormModal
          caseData={editingCase}
          onClose={() => setShowModal(false)}
          onSaved={() => { setShowModal(false); loadCases(); }}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: 编写 CaseFormModal.jsx**

```jsx
import { useState, useEffect } from 'react';

export default function CaseFormModal({ caseData, onClose, onSaved }) {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({
    case_number: '', title: '', case_type: '民事', court: '', judge: '',
    plaintiff: '', defendant: '', filing_date: '', status: '进行中',
    notes: '', template_id: '',
    ...caseData,
  });

  useEffect(() => {
    window.electronAPI.getTemplates('诉讼').then(setTemplates);
  }, []);

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;

    if (caseData?.id) {
      await window.electronAPI.updateCase(caseData.id, form);
    } else {
      await window.electronAPI.createCase(form);
    }
    onSaved();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[560px] max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b font-semibold text-gray-800">
          {caseData?.id ? '编辑案件' : '新建案件'}
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">案件名称 *</label>
              <input name="title" value={form.title} onChange={handleChange} required
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">案号</label>
              <input name="case_number" value={form.case_number} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">案件类型</label>
              <select name="case_type" value={form.case_type} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 bg-white">
                <option>民事</option><option>刑事</option><option>行政</option><option>执行</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">受理法院</label>
              <input name="court" value={form.court} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">原告</label>
              <input name="plaintiff" value={form.plaintiff} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">被告</label>
              <input name="defendant" value={form.defendant} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">承办法官</label>
              <input name="judge" value={form.judge} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">收案日期</label>
              <input type="date" name="filing_date" value={form.filing_date} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          {!caseData?.id && (
            <div>
              <label className="text-xs text-gray-500">流程模板</label>
              <select name="template_id" value={form.template_id} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 bg-white">
                <option value="">不套用模板</option>
                {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="text-xs text-gray-500">备注</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows={2}
              className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
          </div>
          <div className="flex justify-end gap-3 pt-3">
            <button type="button" onClick={onClose}
              className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">取消</button>
            <button type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">保存</button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: case list with search, filter, CRUD modal with template selector"
```

---

### Task 9: 案件详情页 — 垂直时间线

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/CaseDetail.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/StageTimeline.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/DocumentList.jsx`

- [ ] **Step 1: 编写 StageTimeline.jsx**

```jsx
export default function StageTimeline({ stages, onUpdate }) {
  const statusConfig = {
    '已完成': { dot: 'bg-green-500', text: 'text-green-600', icon: '✓' },
    '进行中': { dot: 'bg-blue-500', text: 'text-blue-600 font-semibold', icon: '' },
    '超期': { dot: 'bg-red-500', text: 'text-red-600', icon: '!' },
    '待开始': { dot: 'bg-gray-300', text: 'text-gray-400', icon: '' },
  };

  const cycleStatus = (current) => {
    const order = ['待开始', '进行中', '已完成'];
    const idx = order.indexOf(current);
    return order[(idx + 1) % order.length];
  };

  return (
    <div className="relative pl-8">
      <div className="absolute left-[11px] top-0 bottom-0 w-0.5 bg-gray-200" />
      {stages.map((s, i) => {
        const config = statusConfig[s.status] || statusConfig['待开始'];
        const isOverdue = s.status === '进行中' && s.planned_end && new Date(s.planned_end) < new Date();

        return (
          <div key={s.id} className="relative mb-5">
            <button
              onClick={() => onUpdate(s.id, { status: cycleStatus(s.status) })}
              className={`absolute -left-5 top-1 w-[22px] h-[22px] rounded-full flex items-center justify-center text-white text-xs font-bold transition-transform hover:scale-110 ${
                isOverdue ? 'bg-red-500' : config.dot
              }`}
              title="点击切换状态"
            >
              {isOverdue ? '!' : config.icon}
            </button>
            <div className="ml-6">
              <div className={`text-sm ${isOverdue ? 'text-red-600 font-semibold' : config.text}`}>
                {s.stage_name}
                {isOverdue && <span className="text-xs ml-2 text-red-400">超期</span>}
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
                <input
                  type="date"
                  value={s.planned_start || ''}
                  onChange={e => onUpdate(s.id, { planned_start: e.target.value })}
                  className="text-xs border rounded px-2 py-0.5 w-[130px] text-gray-500"
                  title="计划开始"
                />
                <span className="text-gray-300 text-xs self-center">→</span>
                <input
                  type="date"
                  value={s.planned_end || ''}
                  onChange={e => onUpdate(s.id, { planned_end: e.target.value })}
                  className="text-xs border rounded px-2 py-0.5 w-[130px] text-gray-500"
                  title="计划结束"
                />
                <input
                  type="text"
                  value={s.notes || ''}
                  onChange={e => onUpdate(s.id, { notes: e.target.value })}
                  placeholder="备注..."
                  className="text-xs border rounded px-2 py-0.5 w-[200px] text-gray-400"
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: 编写 DocumentList.jsx**

```jsx
import { useState, useEffect } from 'react';

export default function DocumentList({ caseId, projectId }) {
  const [docs, setDocs] = useState([]);

  const loadDocs = async () => {
    const data = await window.electronAPI.getDocuments(caseId || null, projectId || null);
    setDocs(data);
  };

  useEffect(() => { loadDocs(); }, [caseId, projectId]);

  const handleAdd = async () => {
    await window.electronAPI.addDocument(caseId || null, projectId || null);
    loadDocs();
  };

  const handleDelete = async (id) => {
    await window.electronAPI.deleteDocument(id);
    loadDocs();
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-xs text-gray-500 uppercase tracking-wide">相关文档</h3>
        <button onClick={handleAdd}
          className="text-xs text-blue-600 hover:underline">+ 添加</button>
      </div>
      <div className="space-y-1">
        {docs.map(d => (
          <div key={d.id} className="flex items-center gap-2 text-xs py-1.5 group">
            <span className="text-gray-400">📄</span>
            <button
              onClick={() => window.electronAPI.openDocument(d.file_path)}
              className="text-blue-600 hover:underline truncate flex-1 text-left"
            >
              {d.name}
            </button>
            <span className="text-gray-400 hidden group-hover:inline">{formatSize(d.file_size)}</span>
            <button onClick={() => handleDelete(d.id)}
              className="text-red-400 hover:text-red-600 hidden group-hover:inline">×</button>
          </div>
        ))}
        {docs.length === 0 && <p className="text-xs text-gray-400">暂无文档</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 编写 CaseDetail.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import StageTimeline from '../components/StageTimeline';
import DocumentList from '../components/DocumentList';

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [stages, setStages] = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  useEffect(() => {
    (async () => {
      const c = await window.electronAPI.getCase(parseInt(id));
      if (!c) return navigate('/cases');
      setCaseData(c);
      setForm(c);
      const s = await window.electronAPI.getStages(parseInt(id));
      setStages(s);
    })();
  }, [id]);

  const handleStageUpdate = async (stageId, changes) => {
    const stage = stages.find(s => s.id === stageId);
    const updated = { ...stage, ...changes };
    await window.electronAPI.updateStage(stageId, updated);
    setStages(prev => prev.map(s => s.id === stageId ? updated : s));
    // Refresh case data in case status auto-updated
    const c = await window.electronAPI.getCase(parseInt(id));
    setCaseData(c);
    setForm(c);
  };

  const handleSaveCase = async () => {
    await window.electronAPI.updateCase(caseData.id, form);
    setCaseData(form);
    setEditing(false);
  };

  if (!caseData) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 flex gap-6 h-full">
      {/* 左栏：案件信息 */}
      <div className="w-[280px] min-w-[280px] space-y-4">
        <div className="bg-white rounded-lg shadow-sm border p-4">
          {editing ? (
            <div className="space-y-2">
              {['case_number','title','case_type','court','judge','plaintiff','defendant','filing_date'].map(f => (
                <div key={f}>
                  <label className="text-[10px] text-gray-400">{f === 'case_number' ? '案号' : f === 'title' ? '案件名称' : f === 'case_type' ? '类型' : f === 'court' ? '法院' : f === 'judge' ? '法官' : f === 'plaintiff' ? '原告' : f === 'defendant' ? '被告' : '收案日期'}</label>
                  <input
                    name={f}
                    value={form[f] || ''}
                    onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}
                    className="w-full px-2 py-1 border rounded text-xs"
                  />
                </div>
              ))}
              <div className="flex gap-2 pt-2">
                <button onClick={handleSaveCase} className="px-3 py-1 bg-blue-600 text-white rounded text-xs">保存</button>
                <button onClick={() => { setForm(caseData); setEditing(false); }} className="px-3 py-1 border rounded text-xs">取消</button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="font-bold text-sm text-gray-800">{caseData.case_number || '无案号'}</h2>
                  <p className="text-sm text-gray-700 mt-0.5">{caseData.title}</p>
                </div>
                <button onClick={() => setEditing(true)}
                  className="text-xs text-blue-600 hover:underline">编辑</button>
              </div>
              <div className="mt-3 space-y-1.5 text-xs text-gray-600">
                <div className="flex justify-between"><span className="text-gray-400">类型</span><span>{caseData.case_type}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">法院</span><span>{caseData.court || '-'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">法官</span><span>{caseData.judge || '-'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">原告</span><span className="text-right ml-4 truncate">{caseData.plaintiff || '-'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">被告</span><span className="text-right ml-4 truncate">{caseData.defendant || '-'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">收案日期</span><span>{caseData.filing_date || '-'}</span></div>
                <div className="flex justify-between">
                  <span className="text-gray-400">状态</span>
                  <select value={caseData.status}
                    onChange={async e => {
                      await window.electronAPI.updateCase(caseData.id, { ...caseData, status: e.target.value });
                      setCaseData(prev => ({ ...prev, status: e.target.value }));
                    }}
                    className="text-xs border rounded px-1 py-0.5">
                    <option>进行中</option><option>已结案</option><option>已归档</option>
                  </select>
                </div>
              </div>
              {caseData.notes && (
                <div className="mt-3 pt-3 border-t text-xs text-gray-500">{caseData.notes}</div>
              )}
            </>
          )}
        </div>
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <DocumentList caseId={parseInt(id)} />
        </div>
      </div>

      {/* 右栏：流程时间线 */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border p-5 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-sm text-gray-700">案件流程</h3>
          <span className="text-xs text-gray-400">
            {stages.filter(s => s.status === '已完成').length}/{stages.length} 阶段完成
          </span>
        </div>
        <StageTimeline stages={stages} onUpdate={handleStageUpdate} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: case detail with vertical timeline, editable stages, and document list"
```

---

### Task 10: 日历视图

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/CalendarView.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/MonthCalendar.jsx`

- [ ] **Step 1: 编写 MonthCalendar.jsx**

```jsx
import { useState } from 'react';

export default function MonthCalendar({ events, selectedDate, onSelectDate }) {
  const [viewDate, setViewDate] = useState(new Date());

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const prevMonth = () => setViewDate(new Date(year, month - 1, 1));
  const nextMonth = () => setViewDate(new Date(year, month + 1, 1));

  const today = new Date().toISOString().slice(0, 10);
  const adjustedFirstDay = firstDay === 0 ? 6 : firstDay - 1; // Monday start

  const getEventsForDay = (day) => {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return events.filter(e => e.date === dateStr);
  };

  const weekDays = ['一', '二', '三', '四', '五', '六', '日'];

  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      <div className="flex items-center justify-between mb-4">
        <button onClick={prevMonth} className="text-gray-400 hover:text-gray-600">◀</button>
        <span className="font-semibold text-sm">{year}年 {month + 1}月</span>
        <button onClick={nextMonth} className="text-gray-400 hover:text-gray-600">▶</button>
      </div>

      <div className="grid grid-cols-7 text-center text-xs text-gray-400 mb-2">
        {weekDays.map(d => <div key={d} className={d === '六' || d === '日' ? 'text-red-400' : ''}>{d}</div>)}
      </div>

      <div className="grid grid-cols-7 text-center text-sm gap-y-1">
        {Array.from({ length: adjustedFirstDay }).map((_, i) => (
          <div key={`empty-${i}`} className="py-2" />
        ))}
        {Array.from({ length: daysInMonth }).map((_, i) => {
          const day = i + 1;
          const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
          const dayEvents = getEventsForDay(day);
          const isToday = dateStr === today;
          const isSelected = dateStr === selectedDate;

          return (
            <button
              key={day}
              onClick={() => onSelectDate(dateStr)}
              className={`py-1.5 rounded-lg relative text-sm transition-colors ${
                isSelected ? 'bg-blue-600 text-white' :
                isToday ? 'bg-blue-50 text-blue-600 font-bold' :
                'hover:bg-gray-100'
              }`}
            >
              {day}
              {dayEvents.length > 0 && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 flex gap-0.5">
                  {dayEvents.some(e => e.overdue) && <span className="w-1.5 h-1.5 rounded-full bg-red-500" />}
                  {dayEvents.some(e => !e.overdue) && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="flex gap-4 mt-4 pt-3 border-t text-xs text-gray-400">
        <span>🔴 超期</span><span>🟡 截止日期</span><span>🔵 今天</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 编写 CalendarView.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import MonthCalendar from '../components/MonthCalendar';

export default function CalendarView() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [selectedEvents, setSelectedEvents] = useState([]);

  useEffect(() => {
    (async () => {
      const allEvents = [];
      const now = new Date();
      const cases = await window.electronAPI.getCases({ status: '进行中' });
      for (const c of cases) {
        const stages = await window.electronAPI.getStages(c.id);
        for (const s of stages) {
          if (s.planned_end) {
            const endDate = new Date(s.planned_end);
            allEvents.push({
              date: s.planned_end,
              title: s.stage_name,
              caseTitle: c.title,
              caseId: c.id,
              overdue: s.status !== '已完成' && endDate < now,
              isStage: true,
            });
          }
        }
      }
      const projects = await window.electronAPI.getProjects({ status: '进行中' });
      for (const p of projects) {
        const tasks = await window.electronAPI.getTasks(p.id);
        for (const t of tasks) {
          if (t.deadline) {
            const dl = new Date(t.deadline);
            allEvents.push({
              date: t.deadline,
              title: t.title,
              caseTitle: p.name,
              projectId: p.id,
              overdue: t.status !== '已完成' && dl < now,
              isStage: false,
            });
          }
        }
      }
      setEvents(allEvents);
    })();
  }, []);

  useEffect(() => {
    setSelectedEvents(events.filter(e => e.date === selectedDate));
  }, [selectedDate, events]);

  return (
    <div className="p-6 flex gap-6 h-full">
      <div className="flex-[3]">
        <MonthCalendar
          events={events}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />
      </div>
      <div className="flex-[2] bg-white rounded-lg shadow-sm border p-4">
        <h2 className="font-semibold text-sm text-gray-700 mb-3">
          {selectedDate} 日程
        </h2>
        <div className="space-y-2">
          {selectedEvents.map((e, i) => (
            <div
              key={i}
              onClick={() => navigate(e.isStage ? `/cases/${e.caseId}` : `/projects/${e.projectId}`)}
              className={`p-3 rounded-lg border-l-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                e.overdue ? 'border-l-red-500 bg-red-50' : 'border-l-amber-400 bg-amber-50'
              }`}
            >
              <div className="text-sm font-medium text-gray-800">{e.title}</div>
              <div className="text-xs text-gray-500 mt-0.5">
                {e.caseTitle} · {e.isStage ? '诉讼案件' : '非诉项目'}
              </div>
              {e.overdue && <div className="text-xs text-red-500 mt-0.5 font-medium">已超期</div>}
            </div>
          ))}
          {selectedEvents.length === 0 && (
            <p className="text-sm text-gray-400 py-8 text-center">该日期暂无日程</p>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: calendar view with month calendar and daily event list"
```

---

### Task 11: 非诉项目列表 + 项目详情

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/ProjectList.jsx`
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/ProjectDetail.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/ProjectFormModal.jsx`
- Create: `C:/Users/LK/Desktop/日程管理/src/components/TaskList.jsx`

- [ ] **Step 1: 编写 ProjectFormModal.jsx**

```jsx
import { useState, useEffect } from 'react';

export default function ProjectFormModal({ projectData, onClose, onSaved }) {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({
    name: '', project_type: '法律顾问', client: '', start_date: '',
    expected_end_date: '', description: '', notes: '', template_id: '',
    ...projectData,
  });

  useEffect(() => {
    window.electronAPI.getTemplates('非诉').then(setTemplates);
  }, []);

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    if (projectData?.id) {
      await window.electronAPI.updateProject(projectData.id, form);
    } else {
      await window.electronAPI.createProject(form);
    }
    onSaved();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-[500px]" onClick={e => e.stopPropagation()}>
        <div className="px-6 py-4 border-b font-semibold text-gray-800">
          {projectData?.id ? '编辑项目' : '新建项目'}
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">项目名称 *</label>
              <input name="name" value={form.name} onChange={handleChange} required
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">项目类型</label>
              <select name="project_type" value={form.project_type} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 bg-white">
                <option>法律顾问</option><option>合同审查</option><option>尽职调查</option><option>并购</option><option>其他</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">客户名称</label>
              <input name="client" value={form.client} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">开始日期</label>
              <input type="date" name="start_date" value={form.start_date} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500">预计结束日期</label>
              <input type="date" name="expected_end_date" value={form.expected_end_date} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-500" />
            </div>
          </div>
          {!projectData?.id && (
            <div>
              <label className="text-xs text-gray-500">流程模板</label>
              <select name="template_id" value={form.template_id} onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 bg-white">
                <option value="">不套用模板</option>
                {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="text-xs text-gray-500">备注</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows={2}
              className="w-full px-3 py-2 border rounded-lg text-sm mt-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none" />
          </div>
          <div className="flex justify-end gap-3 pt-3">
            <button type="button" onClick={onClose}
              className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">取消</button>
            <button type="submit"
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700">保存</button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 编写 TaskList.jsx**

```jsx
export default function TaskList({ tasks, onUpdate, onDelete, onAdd }) {
  const [newTitle, setNewTitle] = useState('');

  const handleAdd = () => {
    if (!newTitle.trim()) return;
    onAdd(newTitle);
    setNewTitle('');
  };

  const priorityColors = { '高': 'text-red-500', '中': 'text-amber-500', '低': 'text-gray-400' };
  const cycleStatus = (current) => {
    const order = ['待办', '进行中', '已完成'];
    const idx = order.indexOf(current);
    return order[(idx + 1) % order.length];
  };

  return (
    <div>
      <div className="space-y-1.5">
        {tasks.map(t => (
          <div key={t.id} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-50 group text-sm">
            <button
              onClick={() => onUpdate(t.id, { status: cycleStatus(t.status), completed_at: t.status === '进行中' ? new Date().toISOString().slice(0, 10) : '' })}
              className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                t.status === '已完成' ? 'bg-green-500 border-green-500 text-white text-xs' :
                t.status === '进行中' ? 'border-blue-400' : 'border-gray-300'
              }`}
            >
              {t.status === '已完成' ? '✓' : ''}
            </button>
            <span className={`flex-1 text-sm ${t.status === '已完成' ? 'line-through text-gray-400' : 'text-gray-700'}`}>
              {t.title}
            </span>
            {t.deadline && (
              <span className={`text-xs ${new Date(t.deadline) < new Date() && t.status !== '已完成' ? 'text-red-500' : 'text-gray-400'}`}>
                {t.deadline}
              </span>
            )}
            <select
              value={t.priority}
              onChange={e => onUpdate(t.id, { priority: e.target.value })}
              className={`text-xs border rounded px-1 py-0.5 bg-white ${priorityColors[t.priority]}`}
            >
              <option>高</option><option>中</option><option>低</option>
            </select>
            <button onClick={() => onDelete(t.id)}
              className="text-red-400 hover:text-red-600 hidden group-hover:inline text-xs">×</button>
          </div>
        ))}
      </div>
      <div className="flex gap-2 mt-3 px-3">
        <input
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="添加任务..."
          className="flex-1 px-3 py-1.5 border rounded text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <button onClick={handleAdd}
          className="px-3 py-1.5 bg-emerald-600 text-white rounded text-xs hover:bg-emerald-700">添加</button>
      </div>
    </div>
  );
}
```

Note: Add `import { useState } from 'react';` at the top of TaskList.jsx.

- [ ] **Step 3: 编写 ProjectList.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ProjectFormModal from '../components/ProjectFormModal';

export default function ProjectList() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingProject, setEditingProject] = useState(null);

  const loadProjects = async () => {
    const filters = {};
    if (statusFilter) filters.status = statusFilter;
    if (search) filters.search = search;
    const data = await window.electronAPI.getProjects(filters);
    setProjects(data);
  };

  useEffect(() => { loadProjects(); }, [statusFilter]);

  const handleSearch = (e) => { e.preventDefault(); loadProjects(); };

  const handleDelete = async (id) => {
    if (!confirm('确定删除此项目？相关任务和文档将一并删除。')) return;
    await window.electronAPI.deleteProject(id);
    loadProjects();
  };

  const statusColors = {
    '进行中': 'bg-amber-50 text-amber-700',
    '已完成': 'bg-green-50 text-green-700',
    '已终止': 'bg-gray-50 text-gray-600',
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold text-gray-800">非诉项目</h1>
        <button
          onClick={() => { setEditingProject(null); setShowModal(true); }}
          className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700"
        >
          + 新建项目
        </button>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3 mb-4">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="搜索项目名称、客户..."
          className="flex-1 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 border rounded-lg text-sm bg-white">
          <option value="">全部状态</option>
          <option value="进行中">进行中</option>
          <option value="已完成">已完成</option>
          <option value="已终止">已终止</option>
        </select>
        <button type="submit" className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">搜索</button>
      </form>

      <div className="bg-white rounded-lg shadow-sm border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-gray-500">
              <th className="px-4 py-3 font-medium">项目名称</th>
              <th className="px-4 py-3 font-medium">类型</th>
              <th className="px-4 py-3 font-medium">客户</th>
              <th className="px-4 py-3 font-medium">状态</th>
              <th className="px-4 py-3 font-medium">开始日期</th>
              <th className="px-4 py-3 font-medium">预计结束</th>
              <th className="px-4 py-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id} className="border-b hover:bg-gray-50 cursor-pointer"
                onClick={() => navigate(`/projects/${p.id}`)}>
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3">{p.project_type}</td>
                <td className="px-4 py-3 text-gray-500">{p.client || '-'}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[p.status] || ''}`}>{p.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-500">{p.start_date || '-'}</td>
                <td className="px-4 py-3 text-gray-500">{p.expected_end_date || '-'}</td>
                <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                  <button onClick={() => { setEditingProject(p); setShowModal(true); }}
                    className="text-blue-600 hover:underline mr-3 text-xs">编辑</button>
                  <button onClick={() => handleDelete(p.id)}
                    className="text-red-500 hover:underline text-xs">删除</button>
                </td>
              </tr>
            ))}
            {projects.length === 0 && (
              <tr><td colSpan={7} className="text-center py-10 text-gray-400">暂无项目，点击"新建项目"开始</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <ProjectFormModal
          projectData={editingProject}
          onClose={() => setShowModal(false)}
          onSaved={() => { setShowModal(false); loadProjects(); }}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: 编写 ProjectDetail.jsx**

```jsx
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import TaskList from '../components/TaskList';
import DocumentList from '../components/DocumentList';

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  useEffect(() => {
    (async () => {
      const p = await window.electronAPI.getProject(parseInt(id));
      if (!p) return navigate('/projects');
      setProject(p);
      setForm(p);
      const t = await window.electronAPI.getTasks(parseInt(id));
      setTasks(t);
    })();
  }, [id]);

  const handleTaskUpdate = async (taskId, changes) => {
    const task = tasks.find(t => t.id === taskId);
    const updated = { ...task, ...changes };
    await window.electronAPI.updateTask(taskId, updated);
    setTasks(prev => prev.map(t => t.id === taskId ? updated : t));
    const p = await window.electronAPI.getProject(parseInt(id));
    setProject(p);
    setForm(p);
  };

  const handleTaskAdd = async (title) => {
    await window.electronAPI.createTask(parseInt(id), { title });
    const t = await window.electronAPI.getTasks(parseInt(id));
    setTasks(t);
  };

  const handleTaskDelete = async (taskId) => {
    await window.electronAPI.deleteTask(taskId);
    setTasks(prev => prev.filter(t => t.id !== taskId));
  };

  const handleSaveProject = async () => {
    await window.electronAPI.updateProject(project.id, form);
    setProject(form);
    setEditing(false);
  };

  if (!project) return <div className="p-6 text-gray-400">加载中...</div>;

  return (
    <div className="p-6 flex gap-6 h-full">
      {/* 左栏：项目信息 */}
      <div className="w-[280px] min-w-[280px] space-y-4">
        <div className="bg-white rounded-lg shadow-sm border p-4">
          {editing ? (
            <div className="space-y-2">
              {[
                { key: 'name', label: '项目名称' },
                { key: 'project_type', label: '项目类型' },
                { key: 'client', label: '客户' },
                { key: 'start_date', label: '开始日期' },
                { key: 'expected_end_date', label: '预计结束' },
              ].map(f => (
                <div key={f.key}>
                  <label className="text-[10px] text-gray-400">{f.label}</label>
                  {f.key === 'project_type' ? (
                    <select
                      value={form.project_type}
                      onChange={e => setForm(p => ({ ...p, project_type: e.target.value }))}
                      className="w-full px-2 py-1 border rounded text-xs bg-white">
                      <option>法律顾问</option><option>合同审查</option><option>尽职调查</option><option>并购</option><option>其他</option>
                    </select>
                  ) : f.key.endsWith('_date') ? (
                    <input type="date" value={form[f.key] || ''}
                      onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                      className="w-full px-2 py-1 border rounded text-xs" />
                  ) : (
                    <input value={form[f.key] || ''}
                      onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                      className="w-full px-2 py-1 border rounded text-xs" />
                  )}
                </div>
              ))}
              <div className="flex gap-2 pt-2">
                <button onClick={handleSaveProject} className="px-3 py-1 bg-emerald-600 text-white rounded text-xs">保存</button>
                <button onClick={() => { setForm(project); setEditing(false); }} className="px-3 py-1 border rounded text-xs">取消</button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-start justify-between">
                <h2 className="font-bold text-sm text-gray-800">{project.name}</h2>
                <button onClick={() => setEditing(true)}
                  className="text-xs text-blue-600 hover:underline">编辑</button>
              </div>
              <div className="mt-3 space-y-1.5 text-xs text-gray-600">
                <div className="flex justify-between"><span className="text-gray-400">类型</span><span>{project.project_type}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">客户</span><span>{project.client || '-'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">开始日期</span><span>{project.start_date || '-'}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">预计结束</span><span>{project.expected_end_date || '-'}</span></div>
                <div className="flex justify-between">
                  <span className="text-gray-400">状态</span>
                  <select value={project.status}
                    onChange={async e => {
                      await window.electronAPI.updateProject(project.id, { ...project, status: e.target.value });
                      setProject(prev => ({ ...prev, status: e.target.value }));
                    }}
                    className="text-xs border rounded px-1 py-0.5">
                    <option>进行中</option><option>已完成</option><option>已终止</option>
                  </select>
                </div>
              </div>
              {project.description && (
                <div className="mt-3 pt-3 border-t text-xs text-gray-500">{project.description}</div>
              )}
            </>
          )}
        </div>
        <div className="bg-white rounded-lg shadow-sm border p-4">
          <DocumentList projectId={parseInt(id)} />
        </div>
      </div>

      {/* 右栏：任务列表 */}
      <div className="flex-1 bg-white rounded-lg shadow-sm border p-5 overflow-y-auto">
        <h3 className="font-semibold text-sm text-gray-700 mb-4">任务列表 ({tasks.filter(t => t.status === '已完成').length}/{tasks.length})</h3>
        <TaskList
          tasks={tasks}
          onUpdate={handleTaskUpdate}
          onDelete={handleTaskDelete}
          onAdd={handleTaskAdd}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: non-litigation project list, detail with tasks, and CRUD modals"
```

---

### Task 12: 模板管理页

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/TemplateManager.jsx`

- [ ] **Step 1: 编写 TemplateManager.jsx**

```jsx
import { useState, useEffect } from 'react';

export default function TemplateManager() {
  const [templates, setTemplates] = useState([]);
  const [selectedTpl, setSelectedTpl] = useState(null);
  const [stages, setStages] = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: '', category: '诉讼', case_type: '', project_type: '', description: '' });

  useEffect(() => {
    window.electronAPI.getTemplates().then(setTemplates);
  }, []);

  const loadStages = async (tpl) => {
    setSelectedTpl(tpl);
    const s = await window.electronAPI.getTemplateStages(tpl.id);
    setStages(s);
    setForm({ name: tpl.name, category: tpl.category, case_type: tpl.case_type, project_type: tpl.project_type, description: tpl.description });
    setEditing(false);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    if (selectedTpl?.id) {
      await window.electronAPI.updateTemplate(selectedTpl.id, form, stages);
    } else {
      await window.electronAPI.createTemplate(form, stages);
    }
    const updated = await window.electronAPI.getTemplates();
    setTemplates(updated);
    setEditing(false);
  };

  const handleDelete = async (id) => {
    if (!confirm('确定删除此模板？')) return;
    await window.electronAPI.deleteTemplate(id);
    setTemplates(prev => prev.filter(t => t.id !== id));
    if (selectedTpl?.id === id) { setSelectedTpl(null); setStages([]); }
  };

  const addStage = () => {
    setStages(prev => [...prev, { stage_name: '', is_critical: 0 }]);
  };

  const updateStage = (idx, field, value) => {
    setStages(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s));
  };

  const removeStage = (idx) => {
    setStages(prev => prev.filter((_, i) => i !== idx));
  };

  return (
    <div className="p-6 flex gap-6 h-full">
      <div className="w-[260px] min-w-[260px] bg-white rounded-lg shadow-sm border p-4 overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-sm text-gray-700">流程模板</h2>
          <button onClick={() => { setSelectedTpl(null); setStages([]); setForm({ name: '', category: '诉讼', case_type: '', project_type: '', description: '' }); setEditing(true); }}
            className="text-xs text-blue-600 hover:underline">+ 新建</button>
        </div>
        {['诉讼', '非诉'].map(cat => (
          <div key={cat} className="mb-3">
            <div className="text-xs text-gray-400 font-medium mb-1">{cat}</div>
            {templates.filter(t => t.category === cat).map(t => (
              <button
                key={t.id}
                onClick={() => loadStages(t)}
                className={`w-full text-left px-3 py-2 rounded text-sm mb-0.5 transition-colors ${
                  selectedTpl?.id === t.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50'
                }`}
              >
                {t.name}
                {t.is_default === 1 && <span className="text-xs text-gray-400 ml-1">(默认)</span>}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="flex-1 bg-white rounded-lg shadow-sm border p-5 overflow-y-auto">
        {!selectedTpl && !editing ? (
          <div className="text-center text-gray-400 py-20">选择一个模板查看详情，或点击"新建"创建自定义模板</div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <div>
                {editing ? (
                  <div className="flex gap-3 items-center">
                    <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                      placeholder="模板名称" className="px-3 py-1.5 border rounded text-sm font-semibold" />
                    <select value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                      className="px-2 py-1.5 border rounded text-xs bg-white">
                      <option>诉讼</option><option>非诉</option>
                    </select>
                    {form.category === '诉讼' ? (
                      <input value={form.case_type} onChange={e => setForm(p => ({ ...p, case_type: e.target.value }))}
                        placeholder="案件类型" className="px-2 py-1.5 border rounded text-xs w-[100px]" />
                    ) : (
                      <input value={form.project_type} onChange={e => setForm(p => ({ ...p, project_type: e.target.value }))}
                        placeholder="项目类型" className="px-2 py-1.5 border rounded text-xs w-[100px]" />
                    )}
                  </div>
                ) : (
                  <h3 className="font-semibold text-sm text-gray-800">
                    {selectedTpl?.name}
                    <span className="text-xs text-gray-400 ml-2">{selectedTpl?.category} · {selectedTpl?.case_type || selectedTpl?.project_type}</span>
                  </h3>
                )}
              </div>
              <div className="flex gap-2">
                {editing ? (
                  <>
                    <button onClick={handleSave} className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs">保存</button>
                    <button onClick={() => { setEditing(false); if (selectedTpl) loadStages(selectedTpl); }}
                      className="px-3 py-1.5 border rounded text-xs">取消</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => setEditing(true)} className="px-3 py-1.5 border rounded text-xs hover:bg-gray-50">编辑</button>
                    {selectedTpl?.is_default !== 1 && (
                      <button onClick={() => handleDelete(selectedTpl.id)} className="px-3 py-1.5 text-red-500 border rounded text-xs hover:bg-red-50">删除</button>
                    )}
                  </>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-xs text-gray-400 mb-2">阶段列表（共 {stages.length} 个阶段）</div>
              {stages.map((s, idx) => (
                <div key={idx} className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg text-sm">
                  <span className="text-gray-400 text-xs w-6">{idx + 1}</span>
                  {editing ? (
                    <>
                      <input value={s.stage_name} onChange={e => updateStage(idx, 'stage_name', e.target.value)}
                        className="flex-1 px-2 py-1 border rounded text-xs" placeholder="阶段名称" />
                      <label className="flex items-center gap-1 text-xs text-gray-500">
                        <input type="checkbox" checked={s.is_critical === 1} onChange={e => updateStage(idx, 'is_critical', e.target.checked ? 1 : 0)} />
                        关键节点
                      </label>
                      <button onClick={() => removeStage(idx)} className="text-red-400 text-xs">×</button>
                    </>
                  ) : (
                    <>
                      <span className="flex-1 text-gray-700">{s.stage_name}</span>
                      {s.is_critical === 1 && <span className="text-xs text-amber-500">关键节点</span>}
                    </>
                  )}
                </div>
              ))}
              {editing && (
                <button onClick={addStage}
                  className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-xs text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors">
                  + 添加阶段
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: template manager with create, edit, delete and stage list editor"
```

---

### Task 13: 设置页 + 导出功能

**Files:**
- Modify: `C:/Users/LK/Desktop/日程管理/src/pages/Settings.jsx`

- [ ] **Step 1: 编写 Settings.jsx**

```jsx
import { useState, useEffect } from 'react';

export default function Settings() {
  const [settings, setSettings] = useState({ reminderDays: [1, 3, 7] });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    window.electronAPI.getSettings().then(s => {
      if (s) setSettings(s);
    });
  }, []);

  const toggleDay = (day) => {
    setSettings(prev => {
      const days = prev.reminderDays.includes(day)
        ? prev.reminderDays.filter(d => d !== day)
        : [...prev.reminderDays, day].sort((a, b) => a - b);
      return { ...prev, reminderDays: days };
    });
  };

  const handleSave = async () => {
    await window.electronAPI.saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleExportExcel = async () => {
    const cases = await window.electronAPI.getCases({});
    await window.electronAPI.exportExcel(cases);
  };

  const handleExportPdf = async () => {
    const cases = await window.electronAPI.getCases({});
    await window.electronAPI.exportPdf(cases);
  };

  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-xl font-bold text-gray-800 mb-6">设置</h1>

      <div className="bg-white rounded-lg shadow-sm border p-5 mb-6">
        <h2 className="font-semibold text-sm text-gray-700 mb-3">提醒设置</h2>
        <p className="text-xs text-gray-400 mb-3">设置阶段/任务截止日期的默认提前提醒天数（可多选）</p>
        <div className="flex gap-3">
          {[1, 3, 7, 14].map(day => (
            <button
              key={day}
              onClick={() => toggleDay(day)}
              className={`px-4 py-2 rounded-lg text-sm border transition-colors ${
                settings.reminderDays.includes(day)
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-blue-400'
              }`}
            >
              提前 {day} 天
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-5 mb-6">
        <h2 className="font-semibold text-sm text-gray-700 mb-3">数据导出</h2>
        <div className="flex gap-3">
          <button onClick={handleExportExcel}
            className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
            导出案件清单 (Excel)
          </button>
          <button onClick={handleExportPdf}
            className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50">
            导出案件报告 (PDF)
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-5">
        <h2 className="font-semibold text-sm text-gray-700 mb-3">关于</h2>
        <p className="text-xs text-gray-500">律师工作台 v1.0.0</p>
        <p className="text-xs text-gray-400 mt-1">数据存储位置：应用用户数据目录/lawyer-cms.db</p>
      </div>

      <button onClick={handleSave}
        className="mt-6 px-5 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition-colors">
        {saved ? '✓ 已保存' : '保存设置'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Add export handlers to main.js**

Add these IPC handlers inside `app.whenReady()`:

```js
const XLSX = require('xlsx');
const { jsPDF } = require('jspdf');

ipcMain.handle('export:excel', async (_e, cases) => {
  const { dialog } = require('electron');
  const result = await dialog.showSaveDialog({
    defaultPath: `案件清单_${new Date().toISOString().slice(0,10)}.xlsx`,
    filters: [{ name: 'Excel', extensions: ['xlsx'] }],
  });
  if (result.canceled) return false;

  const rows = cases.map(c => ({
    案号: c.case_number, 案件名称: c.title, 类型: c.case_type,
    法院: c.court, 法官: c.judge, 原告: c.plaintiff, 被告: c.defendant,
    状态: c.status, 收案日期: c.filing_date, 结案日期: c.closing_date,
  }));
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.json_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, '案件清单');
  XLSX.writeFile(wb, result.filePath);
  return true;
});

ipcMain.handle('export:pdf', async (_e, cases) => {
  const { dialog } = require('electron');
  const result = await dialog.showSaveDialog({
    defaultPath: `案件报告_${new Date().toISOString().slice(0,10)}.pdf`,
    filters: [{ name: 'PDF', extensions: ['pdf'] }],
  });
  if (result.canceled) return false;

  const doc = new jsPDF();
  doc.setFont('Helvetica');
  doc.setFontSize(16);
  doc.text('案件清单报告', 20, 20);
  doc.setFontSize(10);

  let y = 35;
  doc.text(`导出日期：${new Date().toISOString().slice(0, 10)}`, 20, y);
  y += 10;

  cases.forEach((c, i) => {
    if (y > 270) { doc.addPage(); y = 20; }
    doc.text(`${i + 1}. [${c.status}] ${c.case_number || '-'} ${c.title}`, 20, y);
    y += 6;
  });

  doc.save(result.filePath);
  return true;
});
```

Also add to preload.js requires at the top of main.js:
```js
const XLSX = require('xlsx');
```

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "feat: settings page with reminder config, Excel/PDF export"
```

---

### Task 14: 集成验证与修复

- [ ] **Step 1: 启动 Electron 应用**

Run: `cd "C:/Users/LK/Desktop/日程管理" && npx vite` (terminal 1)

Run: `cd "C:/Users/LK/Desktop/日程管理" && npx electron . --dev` (terminal 2)

- [ ] **Step 2: 验证核心流程**

Checklist:
1. 侧边栏导航切换各页面正常
2. 仪表盘加载统计数据
3. 新建诉讼案件 → 选择模板 → 自动创建 11 个阶段
4. 案件详情时间线点击节点切换状态（待开始→进行中→已完成）
5. 日历视图显示案件截止日期
6. 新建非诉项目 → 添加任务 → 勾选完成
7. 模板管理中编辑自定义模板
8. 为案件添加文档附件

- [ ] **Step 3: 修复发现的问题**

根据验证结果修复任何运行时错误或 UI 问题。

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "fix: integration testing fixes"
```

---

### Task 15: electron-builder 打包配置

- [ ] **Step 1: 添加应用图标**

Create a placeholder icon or use a simple PNG at `assets/icon.png` (256x256 minimum).

- [ ] **Step 2: 构建**

```bash
cd "C:/Users/LK/Desktop/日程管理" && npm run build
```

This runs `vite build && electron-builder` which produces a Windows installer (.exe) in `dist-electron/`.

- [ ] **Step 3: Commit**

```bash
cd "C:/Users/LK/Desktop/日程管理" && git add -A && git commit -m "chore: electron-builder packaging configuration"
```
