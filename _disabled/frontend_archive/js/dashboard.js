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

  _fetchAiSummary() {
    const body = $('#ai-summary-body');
    if (!body) return;

    const kpi = this.app.state.kpiData;
    if (!kpi) {
      body.innerHTML = '<p class="text-muted">输入股票代码后自动生成AI快评</p>';
      return;
    }

    const types = (kpi.data_types || []).join('、');
    body.innerHTML = `
      <p>数据已就绪 · ${kpi.financial_ready ? '财务报表数据完整' : '正在加载更多数据...'}</p>
      <p style="font-size:10px;color:var(--text-muted);margin-top:4px;">可用数据类型：${types || '加载中...'}</p>
      <p style="font-size:10px;color:var(--text-muted);">点击右侧「开始 AI 分析对话」进行深度解读</p>
    `;
  }

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

      panel.querySelectorAll('.recent-card').forEach(card => {
        card.addEventListener('click', () => {
          this.app.selectStock(card.dataset.code, card.dataset.name);
        });
      });

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

function initDashboard() {
  const app = window.__app;
  if (app) {
    new DashboardView(app);
  } else {
    setTimeout(initDashboard, 50);
  }
}
initDashboard();
