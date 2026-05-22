// app.js — Application entry point
import { $ } from './utils.js';
import { ApiClient } from './api.js';
import { Router } from './router.js';

class App {
  constructor() {
    this.api = new ApiClient();
    this.state = {
      currentStock: null,
      kpiData: null,
      modules: [],
      stockDataCache: {},
    };
    this.router = null;
    this._listeners = {};
  }

  async init() {
    this.router = new Router({
      'dashboard': 'dashboard',
      'analysis': 'analysis',
      'analysis/:module': 'analysis/result',
      'ai': 'ai',
      'data': 'data',
      'settings': 'settings',
    });
    this.router.start();

    try {
      this.state.modules = await this.api.getAnalysisModules();
    } catch {
      console.warn('Failed to load module catalog, using fallback');
    }

    this._bindNavTabs();
    this._bindStockSearch();
    this._bindKeyboardShortcuts();
    this._bindSettingsButton();
    this._bindViewChanges();

    this._restoreSession();
    this.api.connectWebSocket();
  }

  async selectStock(code, name, market) {
    this.state.currentStock = { code, name, market };
    this.state.kpiData = null;
    this.state.stockDataCache = {};

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

    this._saveSession();
  }

  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
  }

  emit(event, data) {
    (this._listeners[event] || []).forEach(cb => cb(data));
  }

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

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = input.value.trim();
        if (!query) return;
        const match = query.match(/^(\d{6})\s*(.*)/);
        if (match) {
          this.selectStock(match[1], match[2] || match[1]);
        }
        dropdown.classList.remove('visible');
      }
    });

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
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.emit('shortcut:command-palette');
      }
      if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
        e.preventDefault();
        this.emit('shortcut:ai-panel');
      }
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

const app = new App();
app.init();
window.__app = app;
export default app;
