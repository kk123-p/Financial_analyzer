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
