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
      'quant': 'quant',
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

    $('#stock-input').value = `${code || ''} ${name || ''}`.trim();
    $('#search-status').className = 'search-status connected';
    $('#search-status').textContent = '加载中...';

    try {
      // Step 1: Fetch stock data into server session
      const fetchResult = await this.api.fetchStockData(code);
      if (!fetchResult.success) {
        throw new Error(fetchResult.error || '数据获取失败');
      }

      // Step 2: Build KPI from response
      const kpis = fetchResult.kpis || {};
      this.state.kpiData = {
        kpi: {
          latest_price: kpis.latest_price || kpis.price || '--',
          change_pct: kpis.change_pct || kpis.change || 0,
          pe_ratio: kpis.pe_ratio || kpis.pe || '--',
          market_cap: kpis.market_cap || kpis.total_mv || '--',
          roe: kpis.roe || '--',
        },
        prices: kpis.prices || [],
        financial_ready: fetchResult.financial_ready,
        data_types: fetchResult.data_types || [],
      };
      $('#search-status').textContent = '● 已连接';
      this.emit('stock:loaded', this.state.kpiData);
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

    // Enter key triggers data fetch
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = input.value.trim();
        if (!query) return;
        const match = query.match(/^(\d{6})\s*(.*)/);
        if (match) {
          this.selectStock(match[1], match[2] || match[1]);
        }
      }
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
