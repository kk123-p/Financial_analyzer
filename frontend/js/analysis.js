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
