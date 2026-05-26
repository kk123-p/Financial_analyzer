// quant.js — 策略面板逻辑
import { $ } from './utils.js';
import app from './app.js';

class QuantPanel {
  constructor() {
    this.container = $('#view-quant');
    this._loading = false;
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
        <button class="quant-btn" id="btn-run-signal">生成信号</button>
      </div>
      <div class="quant-grid">
        <div class="quant-card" id="card-rankings">
          <h3>因子排名 TOP-10</h3>
          <div id="rankings-content"><p class="quant-status">点击「生成信号」开始分析</p></div>
        </div>
        <div class="quant-card" id="card-signals">
          <h3>调仓信号</h3>
          <div id="signals-content"><p class="quant-status">等待信号生成</p></div>
        </div>
      </div>
      <div class="quant-card" id="card-overview">
        <h3>运行概况</h3>
        <div id="overview-content"></div>
      </div>
    `;

    $('#btn-run-signal').addEventListener('click', () => this._runSignal());
  }

  async _onShow() {}

  async _runSignal() {
    if (this._loading) return;
    this._loading = true;

    const btn = $('#btn-run-signal');
    btn.disabled = true;
    btn.textContent = '计算中...';

    try {
      const resp = await fetch('/api/v1/quant/run?pool=沪深300&top_n=30', {
        method: 'POST',
      });
      const data = await resp.json();

      if (data.success) {
        this._renderResults(data);
      } else {
        $('#rankings-content').innerHTML =
          `<p class="quant-status" style="color:#f44336;">${data.error}</p>`;
      }
    } catch (err) {
      $('#rankings-content').innerHTML =
        `<p class="quant-status" style="color:#f44336;">请求失败: ${err.message}</p>`;
    } finally {
      this._loading = false;
      btn.disabled = false;
      btn.textContent = '生成信号';
    }
  }

  _renderResults(data) {
    let rankHTML = '<ul class="signal-list">';
    (data.top_10 || []).forEach(item => {
      rankHTML += `
        <li class="signal-item">
          <span>
            <span class="rank-tag">#${item.rank}</span>
            <span class="signal-code">${item.code}</span>
            <span class="signal-name">${item.name || ''}</span>
          </span>
          <span class="signal-score">${item.score.toFixed(3)}</span>
        </li>`;
    });
    rankHTML += '</ul>';
    $('#rankings-content').innerHTML = rankHTML;

    let signalHTML = '<ul class="signal-list">';
    (data.signals || []).forEach(s => {
      signalHTML += `
        <li class="signal-item">
          <span>
            <span class="signal-code">${s.code}</span>
            <span class="signal-name">${s.name || ''}</span>
          </span>
          <span>
            <span class="signal-action ${s.action}">${s.action}</span>
            <span style="margin-left:8px;font-size:0.8rem;">权重 ${(s.weight * 100).toFixed(1)}%</span>
          </span>
        </li>`;
    });
    signalHTML += '</ul>';
    $('#signals-content').innerHTML = signalHTML;

    $('#overview-content').innerHTML = `
      <p class="quant-status success">
        选股池: ${data.universe} | 分析股票: ${data.total_stocks_analyzed}只 |
        日期: ${data.date}
      </p>
    `;
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new QuantPanel().init());
} else {
  new QuantPanel().init();
}
