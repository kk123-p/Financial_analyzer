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
