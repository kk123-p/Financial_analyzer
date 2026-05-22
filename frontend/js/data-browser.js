// data-browser.js — Data table view
import { $, $$, h, formatNumber, formatPercent, formatDate, formatFinancial, debounce } from './utils.js';

const DATA_TYPES = [
  { value: 'fina_income', label: '利润表' },
  { value: 'fina_balance', label: '资产负债表' },
  { value: 'fina_cashflow', label: '现金流量表' },
  { value: 'fina_indicator', label: '财务指标' },
  { value: 'daily', label: '日线行情' },
  { value: 'dividend', label: '分红数据' },
  { value: 'top10_holders', label: '十大股东' },
  { value: 'moneyflow', label: '资金流向' },
  { value: 'margin', label: '融资融券' },
  { value: 'stk_holdernumber', label: '股东人数' },
  { value: 'fina_audit', label: '审计意见' },
  { value: 'fina_mainbz', label: '主营业务构成' },
];

const PAGE_SIZE = 50;

export class DataBrowserView {
  constructor(app) {
    this.app = app;
    this.data = [];
    this.filteredData = [];
    this.currentPage = 1;
    this.sortCol = null;
    this.sortAsc = true;
    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'data') this._init();
    });
  }

  _init() {
    this._populateTypeSelect();
    this._bindControls();
  }

  _populateTypeSelect() {
    const select = $('#data-type-select');
    if (!select) return;

    select.innerHTML = `
      <option value="">选择数据类型...</option>
      ${DATA_TYPES.map(dt => `<option value="${dt.value}">${dt.label}</option>`).join('')}
    `;

    select.addEventListener('change', () => {
      const type = select.value;
      if (type) this._loadData(type);
    });
  }

  _bindControls() {
    const filter = $('#data-filter');
    filter?.addEventListener('input', debounce(() => {
      this._applyFilter(filter.value);
    }, 200));

    $('#btn-export-data')?.addEventListener('click', () => this._exportCSV());
  }

  async _loadData(dataType) {
    const stock = this.app.state.currentStock;
    if (!stock) {
      $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">请先在顶部输入股票代码</td></tr>';
      return;
    }

    $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;"><div class="skeleton" style="height:200px;"></div></td></tr>';

    try {
      const result = await this.app.api.fetchDetailedData(stock.code, dataType);
      this.data = result.data || result.records || result || [];
      this.filteredData = [...this.data];
      this.currentPage = 1;
      this.sortCol = null;
      this._renderTable();
    } catch (err) {
      $('#data-table-body').innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--danger);">加载失败: ${err.message}</td></tr>`;
    }
  }

  _applyFilter(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
      this.filteredData = [...this.data];
    } else {
      this.filteredData = this.data.filter(row =>
        Object.values(row).some(v => String(v).toLowerCase().includes(q))
      );
    }
    this.currentPage = 1;
    this._renderTableBody();
    this._renderPagination();
  }

  _renderTable() {
    if (!this.filteredData.length) {
      $('#data-table-head').innerHTML = '';
      $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">暂无数据</td></tr>';
      return;
    }

    const columns = Object.keys(this.filteredData[0]);

    $('#data-table-head').innerHTML = columns.map(col => `
      <th data-col="${col}">
        ${col}
        <span class="sort-icon">${this.sortCol === col ? (this.sortAsc ? '▲' : '▼') : ''}</span>
      </th>
    `).join('');

    $('#data-table-head').querySelectorAll('th').forEach(th => {
      th.addEventListener('click', () => {
        const col = th.dataset.col;
        if (this.sortCol === col) {
          this.sortAsc = !this.sortAsc;
        } else {
          this.sortCol = col;
          this.sortAsc = true;
        }
        this.filteredData.sort((a, b) => {
          const va = a[col], vb = b[col];
          if (va == null) return 1;
          if (vb == null) return -1;
          if (typeof va === 'number' && typeof vb === 'number') return this.sortAsc ? va - vb : vb - va;
          return this.sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
        });
        this.currentPage = 1;
        this._renderTableBody();
        this._renderTable();
      });
    });

    this._renderTableBody();
    this._renderPagination();
  }

  _renderTableBody() {
    const columns = Object.keys(this.filteredData[0] || {});
    const start = (this.currentPage - 1) * PAGE_SIZE;
    const page = this.filteredData.slice(start, start + PAGE_SIZE);

    $('#data-table-body').innerHTML = page.map(row =>
      `<tr>${columns.map(col => {
        const val = row[col];
        let cls = '';
        if (typeof val === 'number') {
          cls = 'cell-number';
        }
        const display = val == null ? '--' : String(val);
        return `<td class="${cls}">${display}</td>`;
      }).join('')}</tr>`
    ).join('');
  }

  _renderPagination() {
    const totalPages = Math.ceil(this.filteredData.length / PAGE_SIZE);
    if (totalPages <= 1) {
      $('#pagination').innerHTML = '';
      return;
    }

    let pages = [];
    for (let i = Math.max(1, this.currentPage - 2); i <= Math.min(totalPages, this.currentPage + 2); i++) {
      pages.push(i);
    }

    $('#pagination').innerHTML = `
      <button class="page-btn" data-page="1" ${this.currentPage === 1 ? 'disabled' : ''}>«</button>
      <button class="page-btn" data-page="${this.currentPage - 1}" ${this.currentPage === 1 ? 'disabled' : ''}>‹</button>
      ${pages.map(p => `<button class="page-btn${p === this.currentPage ? ' active' : ''}" data-page="${p}">${p}</button>`).join('')}
      <button class="page-btn" data-page="${this.currentPage + 1}" ${this.currentPage === totalPages ? 'disabled' : ''}>›</button>
      <button class="page-btn" data-page="${totalPages}" ${this.currentPage === totalPages ? 'disabled' : ''}>»</button>
      <span class="page-info">${this.filteredData.length} 条</span>
    `;

    $('#pagination').querySelectorAll('.page-btn:not([disabled])').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = parseInt(btn.dataset.page);
        if (page >= 1 && page <= totalPages) {
          this.currentPage = page;
          this._renderTableBody();
          this._renderPagination();
        }
      });
    });
  }

  _exportCSV() {
    if (!this.filteredData.length) return;
    const columns = Object.keys(this.filteredData[0]);
    const header = columns.join(',');
    const rows = this.filteredData.map(row =>
      columns.map(col => {
        const val = row[col];
        if (val == null) return '';
        const str = String(val);
        return str.includes(',') ? `"${str}"` : str;
      }).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `data_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}

function initDataBrowser() {
  const app = window.__app;
  if (app) new DataBrowserView(app);
  else setTimeout(initDataBrowser, 50);
}
initDataBrowser();
