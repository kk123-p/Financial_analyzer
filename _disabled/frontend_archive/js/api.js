// api.js — API client and WebSocket manager
import { debounce } from './utils.js';

const BASE_URL = '';

export class ApiClient {
  constructor() {
    this.ws = null;
    this.wsHandlers = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  /* --- REST --- */

  async get(endpoint) {
    const res = await fetch(BASE_URL + endpoint);
    if (!res.ok) throw new Error(`GET ${endpoint} failed: ${res.status}`);
    return res.json();
  }

  async post(endpoint, data = {}) {
    const res = await fetch(BASE_URL + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`POST ${endpoint} failed: ${res.status}`);
    return res.json();
  }

  /* --- Domain methods --- */

  /** Fetch stock data and load into server session. Returns {success, kpis, data_types, financial_ready} */
  async fetchStockData(code, source = 'tushare') {
    return this.post('/api/v1/fetch', { stock_code: code, source });
  }

  /** Get raw data table (not available via JSON API — use web UI for data browsing) */
  async fetchDetailedData(code, dataType) {
    return { data: [], message: '原始数据浏览请使用 Web UI 的数据页面' };
  }

  /** Get detailed data summary from current session */
  async fetchDataSummary() {
    return this.get('/api/v1/data/summary');
  }

  /** Run a specific analysis (reads stock from server session). Returns {success, result_text, result_html} */
  async runAnalysis(moduleKey) {
    return this.get(`/api/v1/analyze/${moduleKey}`);
  }

  /** Get available analysis types. Merges API response with the hardcoded catalog. */
  async getAnalysisModules() {
    try {
      const data = await this.get('/api/v1/analysis-types');
      const flatList = data.flat_list || [];
      // Merge: use API keys to filter/augment the fallback catalog
      const apiKeys = new Set(flatList.map(item => item.key));
      const fallback = getFallbackModules();
      if (apiKeys.size === 0) return fallback;
      // Mark modules that exist in API
      return fallback.map(m => ({
        ...m,
        available: apiKeys.has(m.key),
      }));
    } catch {
      return getFallbackModules();
    }
  }

  /** AI chat (non-streaming). Returns {success, content} */
  async aiChat(question, stockCode) {
    return this.post('/api/v1/ai/chat', { question, stock_code: stockCode });
  }

  /** AI chat (SSE streaming). Returns the fetch Response for reading the stream. */
  async aiChatStream(question, stockCode) {
    return fetch(BASE_URL + '/api/v1/ai/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, stock_code: stockCode }),
    });
  }

  /** Save API tokens */
  async saveTokens(tushareToken, deepseekKey) {
    return this.post('/api/v1/settings/tokens', {
      tushare_token: tushareToken,
      deepseek_key: deepseekKey,
    });
  }

  /** Get settings status */
  async getSettingsStatus() {
    return this.get('/api/v1/settings/status');
  }

  /** Clear cache */
  async clearCache() {
    return this.post('/api/v1/cache/clear');
  }

  /* --- WebSocket --- */

  connectWebSocket() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return this.ws;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ai/conversation`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this._trigger('open');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this._trigger('message', msg);
      } catch {
        this._trigger('raw', event.data);
      }
    };

    this.ws.onclose = () => {
      this._trigger('close');
      this._tryReconnect();
    };

    this.ws.onerror = (err) => {
      this._trigger('error', err);
    };

    return this.ws;
  }

  sendWebSocket(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  closeWebSocket() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  onWs(event, handler) {
    if (!this.wsHandlers[event]) this.wsHandlers[event] = [];
    this.wsHandlers[event].push(handler);
  }

  offWs(event, handler) {
    if (!this.wsHandlers[event]) return;
    this.wsHandlers[event] = this.wsHandlers[event].filter(h => h !== handler);
  }

  _trigger(event, data) {
    (this.wsHandlers[event] || []).forEach(h => h(data));
  }

  _tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    setTimeout(() => this.connectWebSocket(), delay);
  }
}

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
