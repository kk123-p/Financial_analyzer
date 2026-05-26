// quant.js — 策略面板逻辑
import { $ } from './utils.js';
import app from './app.js';

class QuantPanel {
  constructor() {
    this.container = $('#view-quant');
    this._loading = false;
    this._pools = [];
  }

  async init() {
    this._renderShell();
    app.on('view:changed', ({ view }) => {
      if (view === 'quant') this._onShow();
    });
  }

  _renderShell() {
    this.container.innerHTML = `
      <div class="quant-header">
        <h2>策略面板</h2>
        <div style="display:flex;gap:12px;align-items:center;">
          <select id="quant-pool-select" class="quant-select">
            <option value="沪深300">沪深300</option>
          </select>
          <button class="quant-btn" id="btn-run-signal">生成信号</button>
        </div>
      </div>
      <div id="quant-progress" style="display:none;margin-bottom:16px;">
        <div class="quant-card">
          <p id="quant-progress-text" class="quant-status">正在获取数据...</p>
        </div>
      </div>
      <div class="quant-grid">
        <div class="quant-card" id="card-signals">
          <h3>调仓信号</h3>
          <div id="signals-content"><p class="quant-status">选择选股池，点击「生成信号」</p></div>
        </div>
        <div class="quant-card" id="card-overview">
          <h3>运行概况</h3>
          <div id="overview-content"></div>
        </div>
      </div>
    `;

    $('#btn-run-signal').addEventListener('click', () => this._runSignal());
  }

  async _onShow() {
    this._loadPools();
  }

  async _loadPools() {
    try {
      const resp = await fetch('/api/v1/quant/pools');
      const data = await resp.json();
      if (data.pools && data.pools.length > 0) {
        this._pools = data.pools;
        const select = $('#quant-pool-select');
        select.innerHTML = data.pools.map(p => `<option value="${p}">${p}</option>`).join('');
      }
    } catch (err) {
      console.warn('Failed to load pools', err);
    }
  }

  _showProgress(msg) {
    const el = $('#quant-progress');
    el.style.display = 'block';
    $('#quant-progress-text').textContent = msg;
  }

  _hideProgress() {
    $('#quant-progress').style.display = 'none';
  }

  async _runSignal() {
    if (this._loading) return;
    this._loading = true;

    const pool = $('#quant-pool-select').value;
    const btn = $('#btn-run-signal');
    btn.disabled = true;
    btn.textContent = '计算中...';

    this._showProgress('正在获取成分股和因子数据（可能需要几分钟）...');

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 600000); // 10min timeout

    try {
      const resp = await fetch(`/api/v1/quant/run?pool=${encodeURIComponent(pool)}&top_n=30`, {
        method: 'POST',
        signal: controller.signal,
      });
      clearTimeout(timeout);

      const data = await resp.json();
      this._hideProgress();

      if (data.success) {
        this._renderResults(data);
      } else {
        const errMsg = data.error || '未知错误';
        $('#signals-content').innerHTML =
          `<p class="quant-status" style="color:#f44336;">${errMsg}</p>`;
        $('#overview-content').innerHTML =
          `<p class="quant-status">分析股票: ${data.total_stocks_analyzed || 0}只 | 有效数据: ${data.valid_stocks || 0}只</p>`;
      }
    } catch (err) {
      clearTimeout(timeout);
      this._hideProgress();
      const msg = err.name === 'AbortError' ? '请求超时（数据量较大时可能需较长时间）' : err.message;
      $('#signals-content').innerHTML =
        `<p class="quant-status" style="color:#f44336;">请求失败: ${msg}</p>`;
    } finally {
      this._loading = false;
      btn.disabled = false;
      btn.textContent = '生成信号';
    }
  }

  _renderResults(data) {
    // 信号列表
    let signalHTML = '<ul class="signal-list">';
    (data.signals || []).forEach(s => {
      const actionLabels = { buy: '买入', sell: '卖出', hold: '持有' };
      const actionLabel = actionLabels[s.action] || s.action;
      signalHTML += `
        <li class="signal-item">
          <span>
            <span class="signal-code">${s.code}</span>
            <span class="signal-name">${s.name || ''}</span>
          </span>
          <span style="display:flex;align-items:center;gap:12px;">
            <span style="font-family:monospace;font-size:0.85em;color:var(--text-secondary);">
              ¥${s.price || '--'}
            </span>
            <span class="signal-action ${s.action}">${actionLabel}</span>
            <span style="font-size:0.8rem;">${(s.weight * 100).toFixed(1)}%</span>
          </span>
        </li>`;
    });
    signalHTML += '</ul>';
    if (!data.signals || data.signals.length === 0) {
      signalHTML = '<p class="quant-status">无调仓信号</p>';
    }
    $('#signals-content').innerHTML = signalHTML;

    // 概况
    const buyCount = (data.signals || []).filter(s => s.action === 'buy').length;
    const sellCount = (data.signals || []).filter(s => s.action === 'sell').length;
    const holdCount = (data.signals || []).filter(s => s.action === 'hold').length;

    $('#overview-content').innerHTML = `
      <p class="quant-status success">
        选股池: ${data.universe} | 分析: ${data.total_stocks_analyzed}只 | 有效: ${data.valid_stocks || 0}只 | 日期: ${data.date}
      </p>
      <p class="quant-status" style="margin-top:4px;">
        买入 ${buyCount} 只 | 卖出 ${sellCount} 只 | 持有 ${holdCount} 只
      </p>
    `;
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new QuantPanel().init());
} else {
  new QuantPanel().init();
}
