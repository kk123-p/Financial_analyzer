// bundle.js — Financial Analyzer Pro (bundled for pywebview)
(function() {
'use strict';

// Error boundary — show errors on screen
window.addEventListener('error', function(e) {
  var el = document.getElementById('js-error');
  if (!el) {
    el = document.createElement('div');
    el.id = 'js-error';
    el.style.cssText = 'position:fixed;top:0;left:0;right:0;background:#EF4444;color:#fff;padding:12px 20px;z-index:99999;font-family:sans-serif;font-size:13px;word-break:break-all;';
    document.body.prepend(el);
  }
  el.innerHTML = '<strong>JS 错误:</strong> ' + (e.message || e.error || 'Unknown') + ' (行 ' + (e.lineno || '?') + ')';
  console.error('[FA]', e);
});

console.log('[FA] Bundle loaded');
document.documentElement.classList.add('js-loaded');

// ============================================================
// utils.js — Pure utility functions
// ============================================================

function formatNumber(n, decimals) {
  if (decimals === void 0) decimals = 2;
  if (n == null || isNaN(n)) return '--';
  return Number(n).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatPercent(n, decimals) {
  if (decimals === void 0) decimals = 2;
  if (n == null || isNaN(n)) return '--';
  return (n * 100).toFixed(decimals) + '%';
}

function formatFinancial(n) {
  if (n == null || isNaN(n)) return '--';
  var abs = Math.abs(n);
  var sign = n < 0 ? '-' : '';
  if (abs >= 1e12) return sign + (abs / 1e12).toFixed(2) + '万亿';
  if (abs >= 1e8) return sign + (abs / 1e8).toFixed(2) + '亿';
  if (abs >= 1e4) return sign + (abs / 1e4).toFixed(2) + '万';
  return sign + abs.toFixed(2);
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  var d = new Date(dateStr);
  if (isNaN(d.getTime())) return String(dateStr);
  return d.toISOString().slice(0, 10);
}

function debounce(fn, ms) {
  if (ms === void 0) ms = 300;
  var timer;
  return function () {
    var args = arguments;
    var self = this;
    clearTimeout(timer);
    timer = setTimeout(function () { fn.apply(self, args); }, ms);
  };
}

function $(selector, parent) {
  if (parent === void 0) parent = document;
  return parent.querySelector(selector);
}

function $$(selector, parent) {
  if (parent === void 0) parent = document;
  return Array.from(parent.querySelectorAll(selector));
}

function escapeHtml(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function h(tag, attrs) {
  var children = [];
  for (var _i = 2; _i < arguments.length; _i++) {
    children.push(arguments[_i]);
  }
  if (attrs === void 0) attrs = {};
  var el = document.createElement(tag);
  for (var _a = 0, _b = Object.entries(attrs); _a < _b.length; _a++) {
    var _c = _b[_a], key = _c[0], val = _c[1];
    if (key === 'className') el.className = val;
    else if (key === 'innerHTML') el.innerHTML = val;
    else if (key.startsWith('on')) el.addEventListener(key.slice(2).toLowerCase(), val);
    else el.setAttribute(key, val);
  }
  for (var _d = 0, children_1 = children; _d < children_1.length; _d++) {
    var child = children_1[_d];
    if (typeof child === 'string') el.appendChild(document.createTextNode(child));
    else if (child instanceof Node) el.appendChild(child);
  }
  return el;
}

// ============================================================
// api.js — API client and WebSocket manager
// ============================================================

var BASE_URL = '';

function ApiClient() {
  this.ws = null;
  this.wsHandlers = {};
  this.reconnectAttempts = 0;
  this.maxReconnectAttempts = 5;
}

/* --- REST --- */

ApiClient.prototype.get = function (endpoint) {
  return fetch(BASE_URL + endpoint).then(function (res) {
    if (!res.ok) throw new Error('GET ' + endpoint + ' failed: ' + res.status);
    return res.json();
  });
};

ApiClient.prototype.post = function (endpoint, data) {
  if (data === void 0) data = {};
  return fetch(BASE_URL + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(function (res) {
    if (!res.ok) throw new Error('POST ' + endpoint + ' failed: ' + res.status);
    return res.json();
  });
};

/* --- Domain methods --- */

/** Fetch stock data and load into server session. Returns {success, kpis, data_types, financial_ready} */
ApiClient.prototype.fetchStockData = function (code, source) {
  if (source === void 0) source = 'tushare';
  return this.post('/api/v1/fetch', { stock_code: code, source: source });
};

/** Get raw data table (not available via JSON API — use web UI for data browsing) */
ApiClient.prototype.fetchDetailedData = function (code, dataType) {
  return Promise.resolve({ data: [], message: '原始数据浏览请使用 Web UI 的数据页面' });
};

/** Get detailed data summary from current session */
ApiClient.prototype.fetchDataSummary = function () {
  return this.get('/api/v1/data/summary');
};

/** Run a specific analysis (reads stock from server session). Returns {success, result_text, result_html} */
ApiClient.prototype.runAnalysis = function (moduleKey) {
  return this.get('/api/v1/analyze/' + moduleKey);
};

/** Get available analysis types. Merges API response with the hardcoded catalog. */
ApiClient.prototype.getAnalysisModules = function () {
  var self = this;
  return this.get('/api/v1/analysis-types').then(function (data) {
    var flatList = data.flat_list || [];
    var apiKeys = new Set(flatList.map(function (item) { return item.key; }));
    var fallback = getFallbackModules();
    if (apiKeys.size === 0) return fallback;
    return fallback.map(function (m) { return Object.assign({}, m, { available: apiKeys.has(m.key) }); });
  }).catch(function () {
    return getFallbackModules();
  });
};

/** AI chat (non-streaming). Returns {success, content} */
ApiClient.prototype.aiChat = function (question, stockCode) {
  return this.post('/api/v1/ai/chat', { question: question, stock_code: stockCode });
};

/** AI chat (SSE streaming). Returns the fetch Response for reading the stream. */
ApiClient.prototype.aiChatStream = function (question, stockCode) {
  return fetch(BASE_URL + '/api/v1/ai/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: question, stock_code: stockCode }),
  });
};

/** Save API tokens */
ApiClient.prototype.saveTokens = function (tushareToken, deepseekKey) {
  return this.post('/api/v1/settings/tokens', {
    tushare_token: tushareToken,
    deepseek_key: deepseekKey,
  });
};

/** Get settings status */
ApiClient.prototype.getSettingsStatus = function () {
  return this.get('/api/v1/settings/status');
};

/** Clear cache */
ApiClient.prototype.clearCache = function () {
  return this.post('/api/v1/cache/clear');
};

/* --- WebSocket --- */

ApiClient.prototype.connectWebSocket = function () {
  if (this.ws && this.ws.readyState === WebSocket.OPEN) return this.ws;

  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var wsUrl = protocol + '//' + location.host + '/ai/conversation';

  this.ws = new WebSocket(wsUrl);

  var self = this;
  this.ws.onopen = function () {
    self.reconnectAttempts = 0;
    self._trigger('open');
  };

  this.ws.onmessage = function (event) {
    try {
      var msg = JSON.parse(event.data);
      self._trigger('message', msg);
    } catch (e) {
      self._trigger('raw', event.data);
    }
  };

  this.ws.onclose = function () {
    self._trigger('close');
    self._tryReconnect();
  };

  this.ws.onerror = function (err) {
    self._trigger('error', err);
  };

  return this.ws;
};

ApiClient.prototype.sendWebSocket = function (data) {
  if (this.ws && this.ws.readyState === WebSocket.OPEN) {
    this.ws.send(JSON.stringify(data));
  }
};

ApiClient.prototype.closeWebSocket = function () {
  if (this.ws) {
    this.ws.close();
    this.ws = null;
  }
};

ApiClient.prototype.onWs = function (event, handler) {
  if (!this.wsHandlers[event]) this.wsHandlers[event] = [];
  this.wsHandlers[event].push(handler);
};

ApiClient.prototype.offWs = function (event, handler) {
  if (!this.wsHandlers[event]) return;
  this.wsHandlers[event] = this.wsHandlers[event].filter(function (h) { return h !== handler; });
};

ApiClient.prototype._trigger = function (event, data) {
  (this.wsHandlers[event] || []).forEach(function (h) { h(data); });
};

ApiClient.prototype._tryReconnect = function () {
  if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
  this.reconnectAttempts++;
  var delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
  var self = this;
  setTimeout(function () { self.connectWebSocket(); }, delay);
};

/* --- Fallback module catalog --- */

function getFallbackModules() {
  return [
    { key: 'market_overview', category: 'market', name: '行情概览', desc: '当前价、涨跌幅、52周高低、成交量、总市值', output: 'text', available: true },
    { key: 'price_trend', category: 'market', name: '价格趋势', desc: '短中长期均线趋势、价格与MA定位', output: 'text', available: true },
    { key: 'technical', category: 'market', name: '技术指标', desc: 'RSI、MACD、布林带、金叉/死叉信号', output: 'chart', available: true },
    { key: 'balance_sheet', category: 'financial', name: '资产负债表', desc: '资产结构、负债结构、偿债能力、营运效率 7节深度', output: 'text', available: true },
    { key: 'income_analysis', category: 'financial', name: '利润表', desc: '收入趋势、成本结构、五层利润分解、利润质量 6节深度', output: 'text', available: true },
    { key: 'cashflow_analysis', category: 'financial', name: '现金流量表', desc: '经营/投资/筹资现金流、生命周期定位 6节深度', output: 'text', available: true },
    { key: 'profitability', category: 'capability', name: '盈利能力', desc: '毛利率、净利率、ROE、ROA 及同比变化', output: 'text', available: true },
    { key: 'operational', category: 'capability', name: '营运能力', desc: '应收账款、存货、总资产周转率 及行业对比', output: 'text', available: true },
    { key: 'solvency', category: 'capability', name: '偿债能力', desc: '流动比率、速动比率、资产负债率、利息保障倍数', output: 'text', available: true },
    { key: 'growth', category: 'capability', name: '成长能力', desc: '营收、净利、总资产、净资产同比增长率', output: 'text', available: true },
    { key: 'ratio_analysis', category: 'capability', name: '财务比率', desc: '20+比率指标、加权综合评分(0-100)、A-F评级', output: 'text', available: true },
    { key: 'dupont', category: 'deep', name: '杜邦分析', desc: '三因子分解(净利率×周转率×杠杆)、ROE驱动识别', output: 'chart', available: true },
    { key: 'dupont_roic', category: 'deep', name: 'ROIC分析', desc: '扩展杜邦框架、投入资本回报率、价值创造分析', output: 'text', available: true },
    { key: 'zscore', category: 'deep', name: 'Z-Score', desc: 'Altman Z值、破产风险区域分类(安全/灰色/困境)', output: 'text', available: true },
    { key: 'fscore', category: 'deep', name: 'F-Score', desc: 'Piotroski 9分基本面强度评分(盈利/杠杆/效率)', output: 'chart', available: true },
    { key: 'mscore', category: 'deep', name: 'M-Score', desc: 'Beneish 8变量财务操纵检测模型', output: 'text', available: true },
    { key: 'fcf', category: 'deep', name: '自由现金流', desc: 'FCF、股东盈余、DCF多情景估值(乐观/基准/悲观)', output: 'text', available: true },
    { key: 'cashflow_quadrant', category: 'deep', name: '现金流象限', desc: '8象限分类(奶牛/成长/困境...)、生命周期判断', output: 'text', available: true },
    { key: 'moat', category: 'deep', name: '护城河分析', desc: '5维度竞争优势评估(无形资产/转换成本/网络效应/成本优势/规模)', output: 'text', available: true },
    { key: 'deep_comprehensive', category: 'deep', name: '深度综合', desc: '全部深度分析子报告汇总', output: 'text', available: true },
    { key: 'pe_valuation', category: 'valuation', name: 'PE估值', desc: 'PE/PB/PS/PEG多指标估值、行业对比', output: 'text', available: true },
    { key: 'pe_percentile', category: 'valuation', name: 'PE历史分位', desc: '当前PE在N年历史区间中的分位、高估/低估判断', output: 'text', available: true },
    { key: 'pb_roe', category: 'valuation', name: 'PB-ROE', desc: 'ROE vs PB散点图、估值与回报匹配度', output: 'chart', available: true },
    { key: 'ev_ebitda', category: 'valuation', name: 'EV/EBITDA', desc: '企业价值/息税折旧摊销前利润、隐含公允价值', output: 'text', available: true },
    { key: 'comprehensive', category: 'valuation', name: '综合投资评级', desc: '7维金字塔评分(市场/会计/财务/盈利/成长/估值)、星级', output: 'chart', available: true },
    { key: 'quality', category: 'valuation', name: '财报质量', desc: '四维检查：盈利质量、收入质量、资产质量、操纵概率', output: 'text', available: true },
    { key: 'shareholder_return', category: 'valuation', name: '股东回报', desc: '股息率+回购率、与债券收益率对比、可持续性', output: 'text', available: true },
    { key: 'audit_full', category: 'audit', name: '全面审计', desc: '32信号6维度全面排查(资产/利润/现金流/勾稽/治理/模型)', output: 'chart', available: true },
    { key: 'audit_asset', category: 'audit', name: '资产端排查', desc: '应收账款通胀、存货异常、固定资产不规范、商誉减值', output: 'text', available: true },
    { key: 'audit_profit', category: 'audit', name: '利润端排查', desc: '收入虚增、利润率操纵、非经常性损益依赖、递延确认', output: 'text', available: true },
    { key: 'audit_cashflow', category: 'audit', name: '现金流排查', desc: '经营现金流背离、投资现金流异常、筹资现金流压力', output: 'text', available: true },
    { key: 'audit_cross', category: 'audit', name: '勾稽验证', desc: '三表交叉验证(资产负债/收入现金/税务利润)', output: 'text', available: true },
    { key: 'fraud_ml', category: 'audit', name: 'ML舞弊检测', desc: '4模型集成(决策树+随机森林+GBDT+XGBoost)欺诈概率', output: 'text', available: true },
    { key: 'shareholder', category: 'shareholder', name: '股东结构', desc: '股东人数趋势、Top10集中度、机构持仓、所有权评分', output: 'text', available: true },
    { key: 'capital_flow', category: 'shareholder', name: '资金流向', desc: '主力资金/融资融券/北向资金/大宗交易 综合评分', output: 'text', available: true },
    { key: 'dividend_analysis', category: 'shareholder', name: '分红分析', desc: '股息率、支付率、分红频率与持续性', output: 'text', available: true },
    { key: 'compare_with_peers', category: 'shareholder', name: '行业对比', desc: 'PE/PB/ROE/毛利率/净利率/负债率 同业排名', output: 'chart', available: true },
    { key: 'risk', category: 'risk', name: '风险评估', desc: '加权多维风险评分(偿付30%+盈利30%+运营20%+信号20%)', output: 'text', available: true },
    { key: 'combined', category: 'risk', name: '量价结合', desc: '股价走势与财务表现相关性、背离异常信号', output: 'text', available: true },
    { key: 'trend_score', category: 'risk', name: '趋势评分', desc: '多期趋势评分(营收/利润/利润率/现金流)、综合趋势方向', output: 'text', available: true },
    { key: 'weekly_pe', category: 'risk', name: '周度PE分位', desc: '每周PE百分位排名、N年历史区间估值水平评估', output: 'text', available: true },
    { key: 'fina_audit', category: 'tushare', name: '审计意见', desc: '历年审计意见类型(标准无保留/保留/否定/无法表示)', output: 'text', available: true },
    { key: 'financial_indicators', category: 'tushare', name: '财务指标表', desc: 'EPS/ROE/ROA/毛利率等原始财务指标数据展示', output: 'table', available: true },
    { key: 'main_business', category: 'tushare', name: '主营业务构成', desc: '按产品/行业/地区划分的营收结构', output: 'table', available: true },
  ];
}

// ============================================================
// router.js — Hash-based SPA router
// ============================================================

function Router(routes) {
  this.routes = routes; // { pattern: handler(viewName, params) }
  this.currentView = null;
  this.currentParams = {};
}

Router.prototype.start = function () {
  var self = this;
  window.addEventListener('hashchange', function () { self._handleRoute(); });
  if (!location.hash) {
    location.hash = '#/dashboard';
  } else {
    this._handleRoute();
  }
};

Router.prototype.navigate = function (hash) {
  location.hash = hash;
};

Router.prototype.getCurrentRoute = function () {
  return { view: this.currentView, params: this.currentParams };
};

Router.prototype._handleRoute = function () {
  var hash = location.hash.slice(1) || '/dashboard';
  var parts = hash.split('/').filter(Boolean);
  var path = parts[0];
  var rest = parts.slice(1);

  var matched = false;
  for (var pattern in this.routes) {
    if (!this.routes.hasOwnProperty(pattern)) continue;
    var handler = this.routes[pattern];
    var patternParts = pattern.split('/').filter(Boolean);
    var hashParts = hash.slice(1).split('/').filter(Boolean);

    if (patternParts.length !== hashParts.length) continue;

    var params = {};
    var matches = true;
    for (var i = 0; i < patternParts.length; i++) {
      if (patternParts[i].startsWith(':')) {
        params[patternParts[i].slice(1)] = hashParts[i];
      } else if (patternParts[i] !== hashParts[i]) {
        matches = false;
        break;
      }
    }

    if (matches) {
      this.currentView = handler;
      this.currentParams = params;
      this._activateView(handler, params);
      matched = true;
      break;
    }
  }

  if (!matched) {
    this.navigate('/dashboard');
    return;
  }

  var activeTab = this.currentView.split('/')[0];
  $$('.nav-tab').forEach(function (tab) {
    var route = tab.dataset.route;
    tab.classList.toggle('active', route === '/' + activeTab);
  });
};

Router.prototype._activateView = function (viewName, params) {
  $$('.view').forEach(function (v) { v.classList.remove('active'); });

  var viewId = 'view-' + viewName.split('/')[0];
  var view = document.getElementById(viewId);
  if (view) {
    view.classList.add('active');
  }

  window.dispatchEvent(new CustomEvent('viewchange', {
    detail: { view: viewName, params: params }
  }));
};

Router.prototype.getViewName = function () {
  var hash = location.hash.slice(1) || '/dashboard';
  var parts = hash.split('/').filter(Boolean);
  return parts[0] || 'dashboard';
};

Router.prototype.getModuleKey = function () {
  var hash = location.hash.slice(1) || '';
  var parts = hash.split('/').filter(Boolean);
  return parts[1] || null;
};

// ============================================================
// dashboard.js — Dashboard view logic
// ============================================================

function DashboardView(app) {
  this.app = app;
  this.chart = null;
  this.kpiOrder = ['latest_price', 'pe_ratio', 'market_cap', 'roe', 'score'];

  this._bindEvents();
}

DashboardView.prototype._bindEvents = function () {
  var self = this;
  this.app.on('stock:loaded', function (data) { self._onStockLoaded(data); });
  this.app.on('stock:error', function () { self._showEmpty(); });
  this.app.on('view:changed', function (detail) {
    if (detail.view === 'dashboard') self._onViewActivated();
  });

  var heroInput = $('#hero-search-input');
  if (heroInput) {
    heroInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var query = heroInput.value.trim();
        var match = query.match(/^(\d{6})\s*(.*)/);
        if (match) {
          self.app.selectStock(match[1], match[2] || match[1]);
        }
      }
    });
  }

  var btnAi = $('#btn-start-ai');
  if (btnAi) {
    btnAi.addEventListener('click', function () {
      self.app.router.navigate('/ai');
    });
  }

  var btnExpand = $('#btn-ai-expand');
  if (btnExpand) {
    btnExpand.addEventListener('click', function () {
      self.app.router.navigate('/ai');
    });
  }
};

DashboardView.prototype._onStockLoaded = function (data) {
  $('#dashboard-empty').style.display = 'none';
  $('#dashboard-data').style.display = 'flex';
  this._renderKpi(data);
  this._renderChart(data);
  this._fetchAiSummary();
  this._loadRecentAnalyses();
};

DashboardView.prototype._showEmpty = function () {
  $('#dashboard-data').style.display = 'none';
  $('#dashboard-empty').style.display = 'flex';
  this._loadRecentStocks();
};

DashboardView.prototype._onViewActivated = function () {
  if (this.app.state.currentStock) {
    $('#dashboard-empty').style.display = 'none';
    $('#dashboard-data').style.display = 'flex';
  } else {
    $('#dashboard-data').style.display = 'none';
    $('#dashboard-empty').style.display = 'flex';
    var input = $('#hero-search-input');
    if (input) input.focus();
  }
};

DashboardView.prototype._renderKpi = function (data) {
  var self = this;
  var strip = $('#kpi-strip');
  if (!strip) return;

  var fields = [
    { key: 'latest_price', label: '最新价', format: function (v) { return formatNumber(v); }, isPrice: true },
    { key: 'change_pct', label: '涨跌幅', format: function (v) { return formatPercent(v / 100); }, isChange: true },
    { key: 'pe_ratio', label: '市盈率 PE', format: function (v) { return formatNumber(v, 1); }, isPrice: false },
    { key: 'market_cap', label: '总市值', format: function (v) { return formatFinancial(v); }, isPrice: false },
    { key: 'roe', label: 'ROE', format: function (v) { return formatPercent(v / 100); }, isPrice: false },
  ];

  var kpi = data.kpi || data;
  strip.innerHTML = fields.map(function (f) {
    var val = kpi[f.key];
    var changeHtml = '';
    if (f.isChange) {
      var isPositive = parseFloat(val) >= 0;
      changeHtml = '<div class="kpi-card-change ' + (isPositive ? 'text-success' : 'text-danger') + '">' +
        (isPositive ? '+' : '') + f.format(val) +
        '</div>';
    }
    return '<div class="kpi-card">' +
      '<div class="kpi-card-label">' + f.label + '</div>' +
      '<div class="kpi-card-value' + (f.key === 'score' ? ' accent-gradient' : '') + '">' + f.format(val) + '</div>' +
      changeHtml +
      '</div>';
  }).join('');

  strip.querySelectorAll('.kpi-card').forEach(function (card, i) {
    card.addEventListener('click', function () {
      var modules = {
        latest_price: 'market_overview',
        change_pct: 'market_overview',
        pe_ratio: 'pe_valuation',
        market_cap: 'market_overview',
        roe: 'dupont',
      };
      var key = fields[i].key;
      if (modules[key]) {
        self.app.router.navigate('/analysis/' + modules[key]);
      }
    });
  });
};

DashboardView.prototype._renderChart = function (data) {
  var canvas = $('#dashboard-chart');
  if (!canvas || !window.Chart) return;

  if (this.chart) this.chart.destroy();

  var prices = data.prices || [];
  var labels = prices.map(function (p) { return p.date; });
  var values = prices.map(function (p) { return p.close; });

  this.chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
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
};

DashboardView.prototype._fetchAiSummary = function () {
  var body = $('#ai-summary-body');
  if (!body) return;

  var kpi = this.app.state.kpiData;
  if (!kpi) {
    body.innerHTML = '<p class="text-muted">输入股票代码后自动生成AI快评</p>';
    return;
  }

  var types = (kpi.data_types || []).join('、');
  body.innerHTML =
    '<p>数据已就绪 · ' + (kpi.financial_ready ? '财务报表数据完整' : '正在加载更多数据...') + '</p>' +
    '<p style="font-size:10px;color:var(--text-muted);margin-top:4px;">可用数据类型：' + (types || '加载中...') + '</p>' +
    '<p style="font-size:10px;color:var(--text-muted);">点击右侧「开始 AI 分析对话」进行深度解读</p>';
};

DashboardView.prototype._loadRecentAnalyses = function () {
  var self = this;
  var container = $('#recent-analyses');
  if (!container) return;

  try {
    var history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
    if (!history.length) {
      container.style.display = 'none';
      return;
    }

    var items = history.slice(0, 5);
    container.style.display = 'flex';
    container.innerHTML =
      '<span class="recent-analyses-label">最近分析：</span>' +
      items.map(function (h) {
        return '<span class="recent-analysis-item" data-module="' + h.module + '">' +
          h.name + ' · ' + h.time +
          '</span>';
      }).join('') +
      '<span class="recent-analysis-new" id="btn-new-analysis">+ 新建分析 →</span>';

    container.querySelectorAll('.recent-analysis-item').forEach(function (item) {
      item.addEventListener('click', function () {
        self.app.router.navigate('/analysis/' + item.dataset.module);
      });
    });

    var btnNew = $('#btn-new-analysis');
    if (btnNew) {
      btnNew.addEventListener('click', function () {
        self.app.router.navigate('/analysis');
      });
    }
  } catch (e) {
    container.style.display = 'none';
  }
};

DashboardView.prototype._loadRecentStocks = function () {
  var self = this;
  var panel = $('#recent-panel');
  if (!panel) return;

  try {
    var history = JSON.parse(localStorage.getItem('fa_stock_history') || '[]');
    var recentStocks = history.slice(0, 5);

    panel.innerHTML =
      '<div style="padding: var(--space-4);">' +
      (recentStocks.length ?
        '<div class="empty-section-title">最近查看</div>' +
        recentStocks.map(function (s) {
          return '<div class="recent-card" data-code="' + s.code + '" data-name="' + s.name + '">' +
            '<div class="recent-card-header">' +
            '<span class="recent-card-code">' + s.code + '</span>' +
            '</div>' +
            '<div class="recent-card-name">' + s.name + '</div>' +
            '</div>';
        }).join('')
        : '') +
      '<div class="empty-section-title" style="margin-top: 12px;">快捷模板</div>' +
      '<div class="template-tags">' +
      '<span class="template-tag" data-template="profitability">盈利能力</span>' +
      '<span class="template-tag" data-template="valuation">估值分析</span>' +
      '<span class="template-tag" data-template="audit">异常排查</span>' +
      '<span class="template-tag" data-template="dupont">杜邦分析</span>' +
      '</div>' +
      '</div>';

    panel.querySelectorAll('.recent-card').forEach(function (card) {
      card.addEventListener('click', function () {
        self.app.selectStock(card.dataset.code, card.dataset.name);
      });
    });

    panel.querySelectorAll('.template-tag').forEach(function (tag) {
      tag.addEventListener('click', function () {
        if (self.app.state.currentStock) {
          self.app.router.navigate('/ai');
        } else {
          var input = $('#hero-search-input');
          if (input) input.focus();
        }
      });
    });
  } catch (e) {}
};

function initDashboard() {
  var app = window.__app;
  if (app) {
    new DashboardView(app);
  } else {
    setTimeout(initDashboard, 50);
  }
}
initDashboard();

// ============================================================
// analysis.js — Analysis Center view
// ============================================================

var CATEGORY_META = {
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

var CATEGORY_ORDER = ['market','financial','capability','deep','valuation','audit','shareholder','risk','tushare'];

function AnalysisView(app) {
  this.app = app;
  this.activeCategory = 'market';
  this._bindEvents();
}

AnalysisView.prototype._bindEvents = function () {
  var self = this;
  this.app.on('view:changed', function (d) {
    if (d.view === 'analysis') self._showCategoryList();
    if (d.view === 'analysis/result') self._showResult(d.params.module);
    if (d.view === 'analysis' && self.app.router.getModuleKey()) {
      self._showResult(self.app.router.getModuleKey());
    }
  });
};

AnalysisView.prototype._showCategoryList = function () {
  $('#analysis-center').style.display = 'flex';
  $('#analysis-result').style.display = 'none';
  this._renderCategories();
  this._renderModules(this.activeCategory);
};

AnalysisView.prototype._renderCategories = function () {
  var self = this;
  var container = $('#analysis-categories');
  container.innerHTML = CATEGORY_ORDER.map(function (cat) {
    return '<button class="category-item' + (cat === self.activeCategory ? ' active' : '') + '" data-category="' + cat + '">' +
      CATEGORY_META[cat].name +
      '</button>';
  }).join('');

  container.querySelectorAll('.category-item').forEach(function (btn) {
    btn.addEventListener('click', function () {
      self.activeCategory = btn.dataset.category;
      self._renderCategories();
      self._renderModules(self.activeCategory);
    });
  });
};

AnalysisView.prototype._renderModules = function (category) {
  var self = this;
  var container = $('#analysis-modules');
  var modules = this.app.state.modules.filter(function (m) { return m.category === category; });
  container.innerHTML =
    '<div class="modules-header">' +
    '<span class="modules-category-title">' + CATEGORY_META[category].name + ' · ' + modules.length + ' 个模块</span>' +
    '</div>' +
    '<div class="module-grid">' +
    modules.map(function (m) {
      return '<div class="module-card" data-key="' + m.key + '">' +
        '<div class="module-card-name">' + m.name + '</div>' +
        '<div class="module-card-desc">' + m.desc + '</div>' +
        '<div class="module-card-tags">' +
        (m.output === 'chart' ? '<span class="module-tag chart">图表</span>' : '') +
        (m.output === 'table' ? '<span class="module-tag chart">表格</span>' : '') +
        '<span class="module-tag">' + (m.output === 'chart' || m.output === 'table' ? '文字+图表' : '文字') + '</span>' +
        '</div>' +
        '</div>';
    }).join('') +
    '</div>';

  container.querySelectorAll('.module-card').forEach(function (card) {
    card.addEventListener('click', function () {
      var key = card.dataset.key;
      self.app.router.navigate('/analysis/' + key);
    });
  });
};

AnalysisView.prototype._showResult = function (moduleKey) {
  var self = this;
  return new Promise(function () {
    if (!moduleKey) return;

    $('#analysis-center').style.display = 'none';
    $('#analysis-result').style.display = 'flex';

    var mod = self.app.state.modules.find(function (m) { return m.key === moduleKey; });
    var stock = self.app.state.currentStock;

    var breadcrumb = $('.result-breadcrumb', $('#analysis-result'));
    if (breadcrumb) {
      var catName = mod ? (CATEGORY_META[mod.category] ? CATEGORY_META[mod.category].name : mod.category) : '';
      breadcrumb.innerHTML =
        '<span class="result-breadcrumb-link" data-nav="/analysis">分析中心</span>' +
        '<span>›</span>' +
        '<span class="result-breadcrumb-link" data-nav="/analysis">' + catName + '</span>' +
        '<span>›</span>' +
        '<span class="current">' + (mod ? mod.name : moduleKey) + '</span>' +
        (stock ? '<span class="stock-badge">' + stock.code + ' ' + stock.name + '</span>' : '');
      breadcrumb.querySelectorAll('.result-breadcrumb-link').forEach(function (link) {
        link.addEventListener('click', function () { self.app.router.navigate(link.dataset.nav); });
      });
    }

    var body = $('.result-text', $('#analysis-result'));
    if (body) {
      body.innerHTML =
        '<div class="skeleton" style="height:40px;width:60%;margin-bottom:16px;"></div>' +
        '<div class="skeleton" style="height:14px;margin-bottom:8px;"></div>' +
        '<div class="skeleton" style="height:14px;width:80%;margin-bottom:8px;"></div>' +
        '<div class="skeleton" style="height:14px;width:90%;margin-bottom:8px;"></div>';

      if (stock) {
        self.app.api.runAnalysis(moduleKey).then(function (result) {
          var text = result.result_text || result.report || '';
          body.innerHTML = text ? self._renderMarkdown(text) : '<p class="text-muted">分析完成，暂无内容</p>';
          self._addCopyButtons(body);
          self._renderChart(moduleKey, result);
          self._renderRecommendations(moduleKey, mod);
          self._saveToHistory(moduleKey, mod);
        }).catch(function (err) {
          body.innerHTML = '<p class="text-danger">分析失败: ' + err.message + '</p>';
        });
      } else {
        body.innerHTML = '<p class="text-muted">请先在顶部输入股票代码</p>';
      }
    }
  });
};

AnalysisView.prototype._renderMarkdown = function (text) {
  if (typeof marked !== 'undefined') {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(String(text));
  }
  return '<pre>' + text + '</pre>';
};

AnalysisView.prototype._addCopyButtons = function (container) {
  container.querySelectorAll('h2, h3').forEach(function (heading) {
    var btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = '复制';
    btn.addEventListener('click', function () {
      var content = '';
      var el = heading.nextElementSibling;
      while (el && ['H2','H3'].indexOf(el.tagName) === -1) {
        content += el.textContent + '\n';
        el = el.nextElementSibling;
      }
      navigator.clipboard.writeText(content).then(function () {
        btn.textContent = '已复制';
        setTimeout(function () { btn.textContent = '复制'; }, 1500);
      }).catch(function () {
        var ta = document.createElement('textarea');
        ta.value = content;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btn.textContent = '已复制';
        setTimeout(function () { btn.textContent = '复制'; }, 1500);
      });
    });
    heading.appendChild(btn);
  });
};

AnalysisView.prototype._renderChart = function (moduleKey, result) {
  var panel = $('.result-chart-panel', $('#analysis-result'));
  if (!panel || !window.Chart) return;

  var chartData = result.chart_data || result;
  var chartModules = ['dupont', 'fscore', 'pb_roe', 'comprehensive', 'audit_full', 'compare_with_peers', 'technical'];

  if (chartModules.indexOf(moduleKey) === -1) {
    panel.innerHTML = '<span class="text-muted" style="font-size:10px;">文本报告</span>';
    return;
  }

  var canvasId = 'result-chart-canvas';
  panel.innerHTML = '<canvas id="' + canvasId + '"></canvas>';
  var canvas = document.getElementById(canvasId);

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
};

AnalysisView.prototype._renderRecommendations = function (moduleKey, currentMod) {
  var self = this;
  var container = $('.result-recommendations', $('#analysis-result'));
  if (!container) return;

  if (currentMod) {
    var siblings = this.app.state.modules
      .filter(function (m) { return m.category === currentMod.category && m.key !== moduleKey; })
      .slice(0, 2);
    if (siblings.length) {
      container.innerHTML =
        '<span class="result-rec-label">推荐下一步：</span>' +
        siblings.map(function (s) {
          return '<span class="result-rec-link" data-key="' + s.key + '">' + s.name + ' →</span>';
        }).join('');
      container.querySelectorAll('.result-rec-link').forEach(function (link) {
        link.addEventListener('click', function () {
          self.app.router.navigate('/analysis/' + link.dataset.key);
        });
      });
      return;
    }
  }
  container.innerHTML = '';
};

AnalysisView.prototype._saveToHistory = function (moduleKey, mod) {
  try {
    var history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
    history.unshift({
      module: moduleKey,
      name: mod ? mod.name : moduleKey,
      time: new Date().toLocaleString('zh-CN'),
    });
    if (history.length > 20) history.length = 20;
    localStorage.setItem('fa_analysis_history', JSON.stringify(history));
  } catch (e) {}
};

function initAnalysis() {
  var app = window.__app;
  if (app) new AnalysisView(app);
  else setTimeout(initAnalysis, 50);
}
initAnalysis();

// ============================================================
// chat.js — AI Chat view (conversation, templates, debate)
// ============================================================

var TEMPLATES = [
  { id: 'profitability', name: '盈利能力深度解读', desc: '毛利率·净利率·ROE·盈利质量 四维解读', data: 'income, financial' },
  { id: 'audit', name: '财务异常信号排查', desc: '资产端·利润端·现金流·勾稽 四维排查', data: 'balance, income, cashflow' },
  { id: 'valuation', name: '估值合理性判断', desc: 'PE分位·股息率·市净率 三维判断', data: 'daily_basic, financial' },
  { id: 'shareholder', name: '股东结构评估', desc: '股权集中度·机构持仓·筹码变化', data: 'top10_holders, stk_holdernumber' },
  { id: 'capital_flow', name: '资金面多空分析', desc: '主力资金·融资融券·北向资金 三维解读', data: 'moneyflow, margin' },
  { id: 'growth', name: '成长质量检查', desc: '营收成长·利润成长·现金流质量 三维评估', data: 'income, cashflow, financial' },
];

function ChatView(app) {
  this.app = app;
  this.mode = 'chat';
  this.activeTemplate = null;
  this.isStreaming = false;
  this.currentAiBubble = null;
  this.debateRound = 0;

  this._bindEvents();
}

ChatView.prototype._bindEvents = function () {
  var self = this;
  this.app.on('view:changed', function (d) {
    if (d.view === 'ai') self._initView();
  });

  this.app.on('shortcut:ai-panel', function () { self._toggleAiPanel(); });
  this.app.on('shortcut:escape', function () { self._closeOverlays(); });
};

ChatView.prototype._initView = function () {
  this._bindSubTabs();
  this._bindTemplateChips();
  this._bindChatInput();
  this._bindDebateControls();
  this._renderContextPanel();
};

ChatView.prototype._bindSubTabs = function () {
  var self = this;
  $$('#ai-subtabs .ai-subtab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      self.mode = tab.dataset.mode;
      $$('#ai-subtabs .ai-subtab').forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');

      $('#ai-main').style.display = self.mode === 'debate' ? 'none' : 'flex';
      $('#ai-debate').style.display = self.mode === 'debate' ? 'flex' : 'none';

      if (self.mode === 'template') {
        self._renderTemplateGrid();
      }
    });
  });
};

ChatView.prototype._bindTemplateChips = function () {
  var self = this;
  var container = $('#template-chips');
  if (!container) return;

  container.innerHTML = TEMPLATES.map(function (t) {
    return '<span class="template-chip" data-id="' + t.id + '">' + t.name + '</span>';
  }).join('');

  container.querySelectorAll('.template-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var id = chip.dataset.id;
      container.querySelectorAll('.template-chip').forEach(function (c) { c.classList.remove('active'); });
      if (self.activeTemplate === id) {
        self.activeTemplate = null;
      } else {
        chip.classList.add('active');
        self.activeTemplate = id;
        var template = TEMPLATES.find(function (t) { return t.id === id; });
        $('#chat-input').placeholder = '已选「' + (template ? template.name : '') + '」，输入补充问题或直接发送...';
      }
    });
  });
};

ChatView.prototype._renderTemplateGrid = function () {
  var self = this;
  var messages = $('#chat-messages');
  if (!messages) return;

  messages.innerHTML =
    '<div class="template-grid">' +
    TEMPLATES.map(function (t) {
      return '<div class="template-card' + (self.activeTemplate === t.id ? ' selected' : '') + '" data-id="' + t.id + '">' +
        '<div class="template-card-name">' + t.name + '</div>' +
        '<div class="template-card-desc">' + t.desc + '</div>' +
        '<div class="template-card-data">所需数据：' + t.data + '</div>' +
        '</div>';
    }).join('') +
    '</div>' +
    '<p style="text-align:center;font-size:10px;color:var(--text-muted);margin-top:12px;">' +
    '选择模板 → 自动加载所需数据 → 发送给 AI → 流式展示结构化分析结果' +
    '</p>';

  messages.querySelectorAll('.template-card').forEach(function (card) {
    card.addEventListener('click', function () {
      self.activeTemplate = card.dataset.id;
      self._renderTemplateGrid();
      self._sendTemplateMessage(self.activeTemplate);
    });
  });
};

ChatView.prototype._bindChatInput = function () {
  var self = this;
  var input = $('#chat-input');
  var sendBtn = $('#btn-chat-send');
  var stopBtn = $('#btn-chat-stop');

  if (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        self._sendMessage();
      }
    });
  }

  if (sendBtn) sendBtn.addEventListener('click', function () { self._sendMessage(); });
  if (stopBtn) stopBtn.addEventListener('click', function () { self._stopStreaming(); });
};

ChatView.prototype._sendMessage = function () {
  var self = this;
  var input = $('#chat-input');
  var text = input.value.trim();
  if (!text || this.isStreaming) return;
  input.value = '';

  var messages = $('#chat-messages');
  messages.appendChild(this._createBubble('user', text));
  messages.scrollTop = messages.scrollHeight;

  if (!this.app.state.currentStock) {
    messages.appendChild(this._createBubble('ai', '请先在顶部输入股票代码'));
    return;
  }

  this._setStreaming(true);
  this.currentAiBubble = this._createBubble('ai', '');
  messages.appendChild(this.currentAiBubble);

  var ws = this.app.api.connectWebSocket();
  var payload = this.activeTemplate
    ? { type: 'template', template_id: this.activeTemplate, stock_code: this.app.state.currentStock.code }
    : { type: 'chat', message: text, stock_code: this.app.state.currentStock.code };

  this.app.api.sendWebSocket(payload);

  var onMessage = function (msg) {
    if (msg.event === 'token') {
      self.currentAiBubble.querySelector('.chat-bubble').innerHTML += msg.data;
      messages.scrollTop = messages.scrollHeight;
    } else if (msg.event === 'section') {
      var bubble = self.currentAiBubble.querySelector('.chat-bubble');
      bubble.innerHTML += '<h3 style="color:var(--accent-soft);margin-top:8px;">' + (msg.title || '') + '</h3>';
    } else if (msg.event === 'done') {
      self._setStreaming(false);
      self.app.api.offWs('message', onMessage);
    }
  };

  this.app.api.onWs('message', onMessage);
};

ChatView.prototype._sendTemplateMessage = function (templateId) {
  var self = this;
  if (!this.app.state.currentStock) return;
  this._setStreaming(true);

  var messages = $('#chat-messages');
  messages.innerHTML = '';
  this.currentAiBubble = this._createBubble('ai', '');
  messages.appendChild(this.currentAiBubble);

  var ws = this.app.api.connectWebSocket();
  this.app.api.sendWebSocket({
    type: 'template',
    template_id: templateId,
    stock_code: this.app.state.currentStock.code,
  });

  var onMessage = function (msg) {
    if (msg.event === 'token') {
      self.currentAiBubble.querySelector('.chat-bubble').innerHTML += msg.data;
      messages.scrollTop = messages.scrollHeight;
    } else if (msg.event === 'section') {
      var bubble = self.currentAiBubble.querySelector('.chat-bubble');
      bubble.innerHTML += '<h3 style="color:var(--accent-soft);margin-top:8px;">' + (msg.title || '') + '</h3>';
    } else if (msg.event === 'done') {
      self._setStreaming(false);
      self.app.api.offWs('message', onMessage);
    }
  };

  this.app.api.onWs('message', onMessage);
};

ChatView.prototype._createBubble = function (role, text) {
  return h('div', { className: 'chat-message ' + role },
    h('div', { className: 'chat-avatar ' + role, innerHTML: role === 'ai' ? 'AI' : 'U' }),
    h('div', { className: 'chat-bubble', innerHTML: text }),
  );
};

ChatView.prototype._setStreaming = function (streaming) {
  this.isStreaming = streaming;
  $('#btn-chat-send').style.display = streaming ? 'none' : 'flex';
  $('#btn-chat-stop').style.display = streaming ? 'flex' : 'none';
};

ChatView.prototype._stopStreaming = function () {
  this.app.api.closeWebSocket();
  this.app.api.connectWebSocket();
  this._setStreaming(false);
  if (this.currentAiBubble) {
    var bubble = this.currentAiBubble.querySelector('.chat-bubble');
    if (bubble && !bubble.textContent.trim()) {
      bubble.textContent = '[已取消]';
    }
  }
};

ChatView.prototype._bindDebateControls = function () {
  var self = this;
  this.app.on('view:changed', function (d) {
    if (d.view === 'ai' && self.mode === 'debate' && self.app.state.currentStock) {
      self._startDebate();
    }
  });
};

ChatView.prototype._startDebate = function () {
  var self = this;
  var cols = $('#debate-columns');
  var consensus = $('#debate-consensus');
  if (!cols) return;

  cols.innerHTML =
    '<div class="debate-col"><div class="debate-col-header value">价值投资者</div><div class="debate-col-body" id="debate-value">分析中...</div></div>' +
    '<div class="debate-col"><div class="debate-col-header growth">成长投资者</div><div class="debate-col-body" id="debate-growth">分析中...</div></div>' +
    '<div class="debate-col"><div class="debate-col-header risk">风控分析师</div><div class="debate-col-body" id="debate-risk">分析中...</div></div>';

  var ws = this.app.api.connectWebSocket();
  this.app.api.sendWebSocket({
    type: 'debate',
    topic: (this.app.state.currentStock.name || this.app.state.currentStock.code) + ' 投资价值分析',
    stock_code: this.app.state.currentStock.code,
  });

  var onMessage = function (msg) {
    if (msg.event === 'debate_round') {
      self.debateRound = msg.round;
      var analystMap = { value: 'debate-value', growth: 'debate-growth', risk: 'debate-risk' };
      var col = document.getElementById(analystMap[msg.analyst]);
      if (col) col.innerHTML += '<p>' + (msg.data || '') + '</p>';
      cols.scrollTop = cols.scrollHeight;
    } else if (msg.event === 'done') {
      consensus.innerHTML =
        '<div class="debate-consensus-label">共识结论 (第' + self.debateRound + '轮)</div>' +
        '<div class="debate-consensus-text">' + (msg.summary || '分析完成') + '</div>';
      self.app.api.offWs('message', onMessage);
    }
  };

  this.app.api.onWs('message', onMessage);
};

ChatView.prototype._renderContextPanel = function () {
  var panel = $('#ai-context-panel');
  if (!panel) return;

  var stock = this.app.state.currentStock;
  var kpi = this.app.state.kpiData;

  panel.innerHTML =
    '<div class="ctx-section">' +
    '<div class="ctx-section-title">当前股票</div>' +
    (stock ?
      '<div class="ctx-card">' +
      '<div class="ctx-card-title">' + stock.code + ' ' + (stock.name || '') + '</div>' +
      '<div class="ctx-card-text">' +
      (kpi ? '最新价 ' + (kpi.latest_price || '--') + ' · PE ' + (kpi.pe_ratio || '--') : '数据加载中...') +
      '</div>' +
      '</div>'
      : '<div class="ctx-card-text text-muted">未选择股票</div>') +
    '</div>' +
    '<div class="ctx-section">' +
    '<div class="ctx-section-title">分析历史</div>' +
    '<div class="ctx-card-text text-muted" id="ctx-history">--</div>' +
    '</div>';

  try {
    var history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
    var ctxHistory = $('#ctx-history');
    if (ctxHistory && history.length) {
      ctxHistory.innerHTML = history.slice(0, 5).map(function (h) {
        return '<div style="margin-bottom:2px;">' + h.name + ' · <span style="color:var(--text-disabled)">' + h.time + '</span></div>';
      }).join('');
    }
  } catch (e) {}
};

ChatView.prototype._toggleAiPanel = function () {
  var self = this;
  var panel = $('#ai-panel');
  if (!panel) return;
  var isOpen = panel.style.display === 'flex';
  panel.style.display = isOpen ? 'none' : 'flex';

  if (!isOpen) {
    this._renderAiPanelContext();
    var panelInput = $('#ai-panel-input');
    if (panelInput) panelInput.focus();
  }
};

ChatView.prototype._renderAiPanelContext = function () {
  var ctx = $('#ai-panel-context');
  if (!ctx) return;
  var stock = this.app.state.currentStock;
  ctx.innerHTML = stock
    ? '<div class="ctx-section-title" style="text-align:center;">上下文：' + stock.code + ' ' + (stock.name || '') + ' 当前数据</div>'
    : '<div class="ctx-section-title" style="text-align:center;">未选择股票</div>';
};

ChatView.prototype._closeOverlays = function () {
  $('#ai-panel').style.display = 'none';
  $('#command-palette').style.display = 'none';
};

function initChat() {
  var app = window.__app;
  if (app) new ChatView(app);
  else setTimeout(initChat, 50);
}
initChat();

// ============================================================
// command-palette.js — Global command palette
// ============================================================

function CommandPalette(app) {
  this.app = app;
  this.activeIndex = -1;
  this._bindEvents();
}

CommandPalette.prototype._bindEvents = function () {
  var self = this;
  this.app.on('shortcut:command-palette', function () { self._toggle(); });
  this.app.on('shortcut:escape', function () { self._close(); });

  var input = $('#cp-input');
  if (input) {
    input.addEventListener('input', debounce(function () { self._search(input.value); }, 100));
    input.addEventListener('keydown', function (e) { self._handleKey(e); });
  }
};

CommandPalette.prototype._toggle = function () {
  var palette = $('#command-palette');
  if (!palette) return;
  var isOpen = palette.style.display === 'flex';
  if (isOpen) {
    this._close();
  } else {
    this._open();
  }
};

CommandPalette.prototype._open = function () {
  var palette = $('#command-palette');
  palette.style.display = 'flex';
  $('#cp-input').value = '';
  this.activeIndex = -1;
  this._search('');
  setTimeout(function () {
    var input = $('#cp-input');
    if (input) input.focus();
  }, 50);
};

CommandPalette.prototype._close = function () {
  $('#command-palette').style.display = 'none';
  this.activeIndex = -1;
};

CommandPalette.prototype._search = function (query) {
  var self = this;
  var q = query.toLowerCase().trim();
  var modules = this.app.state.modules || [];
  var aiTemplates = [
    { key: 'ai_profitability', name: '盈利能力深度解读', category: 'ai', desc: 'AI模板' },
    { key: 'ai_audit', name: '财务异常信号排查', category: 'ai', desc: 'AI模板' },
    { key: 'ai_valuation', name: '估值合理性判断', category: 'ai', desc: 'AI模板' },
    { key: 'ai_shareholder', name: '股东结构评估', category: 'ai', desc: 'AI模板' },
    { key: 'ai_capital_flow', name: '资金面多空分析', category: 'ai', desc: 'AI模板' },
    { key: 'ai_growth', name: '成长质量检查', category: 'ai', desc: 'AI模板' },
  ];

  var allItems = modules.concat(aiTemplates);
  var filtered = q
    ? allItems.filter(function (m) {
        return m.name.toLowerCase().indexOf(q) !== -1 ||
          m.key.toLowerCase().indexOf(q) !== -1 ||
          (m.category || '').toLowerCase().indexOf(q) !== -1 ||
          (m.desc || '').toLowerCase().indexOf(q) !== -1;
      })
    : allItems;

  var results = $('#cp-results');
  if (!filtered.length) {
    results.innerHTML = '<div class="cp-empty">未找到匹配项</div>';
    return;
  }

  this.activeIndex = 0;
  results.innerHTML = filtered.map(function (m, i) {
    return '<div class="cp-result-item' + (i === 0 ? ' active' : '') + '" data-index="' + i + '" data-key="' + m.key + '" data-is-ai="' + (m.category === 'ai') + '">' +
      '<div class="cp-result-left">' +
      '<span class="cp-result-name">' + m.name + '</span>' +
      '<span class="cp-result-path">' + (m.category || '') + (m.desc ? ' · ' + m.desc : '') + '</span>' +
      '</div>' +
      '<span class="cp-result-hint">⏎</span>' +
      '</div>';
  }).join('');

  results.querySelectorAll('.cp-result-item').forEach(function (item) {
    item.addEventListener('click', function () {
      self._executeSelection(item);
    });
  });
};

CommandPalette.prototype._handleKey = function (e) {
  var results = $$('.cp-result-item', $('#cp-results'));
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
};

CommandPalette.prototype._updateActive = function (results) {
  results.forEach(function (item, i) { item.classList.toggle('active', i === this.activeIndex); }, this);
};

CommandPalette.prototype._executeSelection = function (item) {
  var key = item.dataset.key;
  var isAi = item.dataset.isAi === 'true';
  if (isAi) {
    this.app.router.navigate('/ai');
    setTimeout(function () {
      var chip = $('.template-chip[data-id="' + key.replace('ai_', '') + '"]');
      if (chip) chip.click();
    }, 300);
  } else {
    this.app.router.navigate('/analysis/' + key);
  }
  this._close();
};

function initCommandPalette() {
  var app = window.__app;
  if (app) new CommandPalette(app);
  else setTimeout(initCommandPalette, 50);
}
initCommandPalette();

// ============================================================
// data-browser.js — Data table view
// ============================================================

var DATA_TYPES = [
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

var PAGE_SIZE = 50;

function DataBrowserView(app) {
  this.app = app;
  this.data = [];
  this.filteredData = [];
  this.currentPage = 1;
  this.sortCol = null;
  this.sortAsc = true;
  this._bindEvents();
}

DataBrowserView.prototype._bindEvents = function () {
  var self = this;
  this.app.on('view:changed', function (d) {
    if (d.view === 'data') self._init();
  });
};

DataBrowserView.prototype._init = function () {
  this._populateTypeSelect();
  this._bindControls();
};

DataBrowserView.prototype._populateTypeSelect = function () {
  var self = this;
  var select = $('#data-type-select');
  if (!select) return;

  select.innerHTML =
    '<option value="">选择数据类型...</option>' +
    DATA_TYPES.map(function (dt) { return '<option value="' + dt.value + '">' + dt.label + '</option>'; }).join('');

  select.addEventListener('change', function () {
    var type = select.value;
    if (type) self._loadData(type);
  });
};

DataBrowserView.prototype._bindControls = function () {
  var self = this;
  var filter = $('#data-filter');
  if (filter) {
    filter.addEventListener('input', debounce(function () {
      self._applyFilter(filter.value);
    }, 200));
  }

  var btnExport = $('#btn-export-data');
  if (btnExport) {
    btnExport.addEventListener('click', function () { self._exportCSV(); });
  }
};

DataBrowserView.prototype._loadData = function (dataType) {
  var self = this;
  var stock = this.app.state.currentStock;
  if (!stock) {
    $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">请先在顶部输入股票代码</td></tr>';
    return;
  }

  $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;"><div class="skeleton" style="height:200px;"></div></td></tr>';

  this.app.api.fetchDetailedData(stock.code, dataType).then(function (result) {
    self.data = result.data || result.records || result || [];
    self.filteredData = self.data.slice();
    self.currentPage = 1;
    self.sortCol = null;
    self._renderTable();
  }).catch(function (err) {
    $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--danger);">加载失败: ' + err.message + '</td></tr>';
  });
};

DataBrowserView.prototype._applyFilter = function (query) {
  var q = query.toLowerCase().trim();
  if (!q) {
    this.filteredData = this.data.slice();
  } else {
    this.filteredData = this.data.filter(function (row) {
      return Object.values(row).some(function (v) { return String(v).toLowerCase().indexOf(q) !== -1; });
    });
  }
  this.currentPage = 1;
  this._renderTableBody();
  this._renderPagination();
};

DataBrowserView.prototype._renderTable = function () {
  var self = this;
  if (!this.filteredData.length) {
    $('#data-table-head').innerHTML = '';
    $('#data-table-body').innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);">暂无数据</td></tr>';
    return;
  }

  var columns = Object.keys(this.filteredData[0]);

  $('#data-table-head').innerHTML = columns.map(function (col) {
    return '<th data-col="' + col + '">' +
      col +
      '<span class="sort-icon">' + (self.sortCol === col ? (self.sortAsc ? '▲' : '▼') : '') + '</span>' +
      '</th>';
  }).join('');

  $('#data-table-head').querySelectorAll('th').forEach(function (th) {
    th.addEventListener('click', function () {
      var col = th.dataset.col;
      if (self.sortCol === col) {
        self.sortAsc = !self.sortAsc;
      } else {
        self.sortCol = col;
        self.sortAsc = true;
      }
      self.filteredData.sort(function (a, b) {
        var va = a[col], vb = b[col];
        if (va == null) return 1;
        if (vb == null) return -1;
        if (typeof va === 'number' && typeof vb === 'number') return self.sortAsc ? va - vb : vb - va;
        return self.sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      });
      self.currentPage = 1;
      self._renderTableBody();
      self._renderTable();
    });
  });

  this._renderTableBody();
  this._renderPagination();
};

DataBrowserView.prototype._renderTableBody = function () {
  var columns = Object.keys(this.filteredData[0] || {});
  var start = (this.currentPage - 1) * PAGE_SIZE;
  var page = this.filteredData.slice(start, start + PAGE_SIZE);

  $('#data-table-body').innerHTML = page.map(function (row) {
    return '<tr>' + columns.map(function (col) {
      var val = row[col];
      var cls = '';
      if (typeof val === 'number') {
        cls = 'cell-number';
      }
      var display = val == null ? '--' : String(val);
      return '<td class="' + cls + '">' + display + '</td>';
    }).join('') + '</tr>';
  }).join('');
};

DataBrowserView.prototype._renderPagination = function () {
  var self = this;
  var totalPages = Math.ceil(this.filteredData.length / PAGE_SIZE);
  if (totalPages <= 1) {
    $('#pagination').innerHTML = '';
    return;
  }

  var pages = [];
  for (var i = Math.max(1, this.currentPage - 2); i <= Math.min(totalPages, this.currentPage + 2); i++) {
    pages.push(i);
  }

  $('#pagination').innerHTML =
    '<button class="page-btn" data-page="1" ' + (this.currentPage === 1 ? 'disabled' : '') + '>«</button>' +
    '<button class="page-btn" data-page="' + (this.currentPage - 1) + '" ' + (this.currentPage === 1 ? 'disabled' : '') + '>‹</button>' +
    pages.map(function (p) { return '<button class="page-btn' + (p === self.currentPage ? ' active' : '') + '" data-page="' + p + '">' + p + '</button>'; }).join('') +
    '<button class="page-btn" data-page="' + (this.currentPage + 1) + '" ' + (this.currentPage === totalPages ? 'disabled' : '') + '>›</button>' +
    '<button class="page-btn" data-page="' + totalPages + '" ' + (this.currentPage === totalPages ? 'disabled' : '') + '>»</button>' +
    '<span class="page-info">' + this.filteredData.length + ' 条</span>';

  $('#pagination').querySelectorAll('.page-btn:not([disabled])').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var page = parseInt(btn.dataset.page);
      if (page >= 1 && page <= totalPages) {
        self.currentPage = page;
        self._renderTableBody();
        self._renderPagination();
      }
    });
  });
};

DataBrowserView.prototype._exportCSV = function () {
  if (!this.filteredData.length) return;
  var columns = Object.keys(this.filteredData[0]);
  var header = columns.join(',');
  var rows = this.filteredData.map(function (row) {
    return columns.map(function (col) {
      var val = row[col];
      if (val == null) return '';
      var str = String(val);
      return str.indexOf(',') !== -1 ? '"' + str + '"' : str;
    }).join(',');
  });
  var csv = [header].concat(rows).join('\n');
  var blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'data_' + new Date().toISOString().slice(0, 10) + '.csv';
  a.click();
  URL.revokeObjectURL(url);
};

function initDataBrowser() {
  var app = window.__app;
  if (app) new DataBrowserView(app);
  else setTimeout(initDataBrowser, 50);
}
initDataBrowser();

// ============================================================
// settings.js — Settings page
// ============================================================

function SettingsView(app) {
  this.app = app;
  this._bindEvents();
}

SettingsView.prototype._bindEvents = function () {
  var self = this;
  this.app.on('view:changed', function (d) {
    if (d.view === 'settings') self._render();
  });
};

SettingsView.prototype._render = function () {
  var page = $('#settings-page');
  if (!page) return;

  page.innerHTML =
    '<div class="settings-section">' +
    '<h2>Token 管理</h2>' +
    '<div class="settings-field">' +
    '<label>Tushare Token</label>' +
    '<input type="password" id="setting-tushare-token" value="' + (localStorage.getItem('fa_tushare_token') || '') + '" placeholder="输入 Tushare API Token">' +
    '<div class="hint">用于获取 A 股财务数据</div>' +
    '</div>' +
    '<div class="settings-field">' +
    '<label>DeepSeek API Key</label>' +
    '<input type="password" id="setting-deepseek-key" value="' + (localStorage.getItem('fa_deepseek_key') || '') + '" placeholder="输入 DeepSeek API Key">' +
    '<div class="hint">用于 AI 分析功能</div>' +
    '</div>' +
    '<button class="btn-primary" id="btn-save-tokens">保存 Token</button>' +
    '</div>' +
    '<div class="settings-section">' +
    '<h2>数据源</h2>' +
    '<div class="settings-field">' +
    '<label>默认数据源</label>' +
    '<select id="setting-datasource">' +
    '<option value="tushare">Tushare (A股)</option>' +
    '<option value="yfinance">YFinance (美股)</option>' +
    '<option value="akshare">AKShare (A股补充)</option>' +
    '</select>' +
    '</div>' +
    '</div>' +
    '<div class="settings-section">' +
    '<h2>缓存</h2>' +
    '<div class="settings-field">' +
    '<label>缓存过期时间 (小时)</label>' +
    '<input type="number" id="setting-cache-hours" value="' + (localStorage.getItem('fa_cache_hours') || 24) + '" min="1" max="168">' +
    '</div>' +
    '<button class="btn-danger" id="btn-clear-cache">清除缓存</button>' +
    '</div>' +
    '<div class="settings-section">' +
    '<h2>关于</h2>' +
    '<p style="font-size:13px;color:var(--text-secondary);">Financial Analyzer Pro v9.0</p>' +
    '<p style="font-size:11px;color:var(--text-muted);">桌面 GUI 重构版 · Modern Dark SaaS</p>' +
    '</div>';

  this._bindSettingsActions();
};

SettingsView.prototype._bindSettingsActions = function () {
  var self = this;
  var btnSave = $('#btn-save-tokens');
  if (btnSave) {
    btnSave.addEventListener('click', function () {
      var tushare = ($('#setting-tushare-token') ? $('#setting-tushare-token').value : '') || '';
      var deepseek = ($('#setting-deepseek-key') ? $('#setting-deepseek-key').value : '') || '';
      localStorage.setItem('fa_tushare_token', tushare);
      localStorage.setItem('fa_deepseek_key', deepseek);
      alert('Token 已保存');
    });
  }

  var btnClearCache = $('#btn-clear-cache');
  if (btnClearCache) {
    btnClearCache.addEventListener('click', function () {
      if (confirm('确认清除所有缓存数据？')) {
        self.app.api.post('/api/settings/clear-cache').then(function () {
          alert('缓存已清除');
        }).catch(function () {
          alert('清除失败');
        });
      }
    });
  }

  var cacheHours = $('#setting-cache-hours');
  if (cacheHours) {
    cacheHours.addEventListener('change', function () {
      localStorage.setItem('fa_cache_hours', this.value);
    });
  }

  var ds = $('#setting-datasource');
  if (ds) {
    ds.value = localStorage.getItem('fa_datasource') || 'tushare';
    ds.addEventListener('change', function () {
      localStorage.setItem('fa_datasource', this.value);
    });
  }
};

function initSettings() {
  var app = window.__app;
  if (app) new SettingsView(app);
  else setTimeout(initSettings, 50);
}
initSettings();

// ============================================================
// app.js — Application entry point
// ============================================================

function App() {
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

App.prototype.init = function () {
  var self = this;
  this.router = new Router({
    'dashboard': 'dashboard',
    'analysis': 'analysis',
    'analysis/:module': 'analysis/result',
    'ai': 'ai',
    'data': 'data',
    'settings': 'settings',
  });
  this.router.start();

  this.api.getAnalysisModules().then(function (modules) {
    self.state.modules = modules;
  }).catch(function () {
    console.warn('Failed to load module catalog, using fallback');
  });

  this._bindNavTabs();
  this._bindStockSearch();
  this._bindKeyboardShortcuts();
  this._bindSettingsButton();
  this._bindViewChanges();

  this._restoreSession();
  this.api.connectWebSocket();
};

App.prototype.selectStock = function (code, name, market) {
  var self = this;
  this.state.currentStock = { code: code, name: name, market: market };
  this.state.kpiData = null;
  this.state.stockDataCache = {};

  $('#stock-input').value = (code || '') + ' ' + (name || '').trim();
  $('#search-status').className = 'search-status connected';
  $('#search-status').textContent = '加载中...';

  // Step 1: Fetch stock data into server session
  this.api.fetchStockData(code).then(function (fetchResult) {
    if (!fetchResult.success) {
      throw new Error(fetchResult.error || '数据获取失败');
    }

    // Step 2: Build KPI from response
    var kpis = fetchResult.kpis || {};
    self.state.kpiData = {
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
    self.emit('stock:loaded', self.state.kpiData);
  }).catch(function (err) {
    $('#search-status').className = 'search-status disconnected';
    $('#search-status').textContent = '加载失败';
    self.emit('stock:error', err);
  });

  this._saveSession();
};

App.prototype.on = function (event, callback) {
  if (!this._listeners[event]) this._listeners[event] = [];
  this._listeners[event].push(callback);
};

App.prototype.emit = function (event, data) {
  (this._listeners[event] || []).forEach(function (cb) { cb(data); });
};

App.prototype._bindNavTabs = function () {
  var self = this;
  $$('.nav-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var route = tab.dataset.route;
      if (route) self.router.navigate(route);
    });
  });
};

App.prototype._bindStockSearch = function () {
  var self = this;
  var input = $('#stock-input');

  // Enter key triggers data fetch
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      var query = input.value.trim();
      if (!query) return;
      var match = query.match(/^(\d{6})\s*(.*)/);
      if (match) {
        self.selectStock(match[1], match[2] || match[1]);
      }
    }
  });
};

App.prototype._bindKeyboardShortcuts = function () {
  var self = this;
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      self.emit('shortcut:command-palette');
    }
    if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
      e.preventDefault();
      self.emit('shortcut:ai-panel');
    }
    if (e.key === 'Escape') {
      self.emit('shortcut:escape');
    }
  });
};

App.prototype._bindSettingsButton = function () {
  var self = this;
  $('#btn-settings').addEventListener('click', function () {
    self.router.navigate('/settings');
  });
};

App.prototype._bindViewChanges = function () {
  var self = this;
  window.addEventListener('viewchange', function (e) {
    self.emit('view:changed', e.detail);
  });
};

App.prototype._saveSession = function () {
  try {
    localStorage.setItem('fa_last_stock', JSON.stringify(this.state.currentStock));
  } catch (e) {}
};

App.prototype._restoreSession = function () {
  var self = this;
  try {
    var lastStock = JSON.parse(localStorage.getItem('fa_last_stock'));
    if (lastStock && lastStock.code) {
      self.selectStock(lastStock.code, lastStock.name, lastStock.market);
    }
  } catch (e) {}
};

var app = new App();
app.init();
window.__app = app;

})();
