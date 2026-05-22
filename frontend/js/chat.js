// chat.js — AI Chat view (conversation, templates, debate)
import { $, $$, h, escapeHtml } from './utils.js';

const TEMPLATES = [
  { id: 'profitability', name: '盈利能力深度解读', desc: '毛利率·净利率·ROE·盈利质量 四维解读', data: 'income, financial' },
  { id: 'audit', name: '财务异常信号排查', desc: '资产端·利润端·现金流·勾稽 四维排查', data: 'balance, income, cashflow' },
  { id: 'valuation', name: '估值合理性判断', desc: 'PE分位·股息率·市净率 三维判断', data: 'daily_basic, financial' },
  { id: 'shareholder', name: '股东结构评估', desc: '股权集中度·机构持仓·筹码变化', data: 'top10_holders, stk_holdernumber' },
  { id: 'capital_flow', name: '资金面多空分析', desc: '主力资金·融资融券·北向资金 三维解读', data: 'moneyflow, margin' },
  { id: 'growth', name: '成长质量检查', desc: '营收成长·利润成长·现金流质量 三维评估', data: 'income, cashflow, financial' },
];

export class ChatView {
  constructor(app) {
    this.app = app;
    this.mode = 'chat';
    this.activeTemplate = null;
    this.isStreaming = false;
    this.currentAiBubble = null;
    this.debateRound = 0;

    this._bindEvents();
  }

  _bindEvents() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'ai') this._initView();
    });

    this.app.on('shortcut:ai-panel', () => this._toggleAiPanel());
    this.app.on('shortcut:escape', () => this._closeOverlays());
  }

  _initView() {
    this._bindSubTabs();
    this._bindTemplateChips();
    this._bindChatInput();
    this._bindDebateControls();
    this._renderContextPanel();
  }

  _bindSubTabs() {
    $$('#ai-subtabs .ai-subtab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.mode = tab.dataset.mode;
        $$('#ai-subtabs .ai-subtab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        $('#ai-main').style.display = this.mode === 'debate' ? 'none' : 'flex';
        $('#ai-debate').style.display = this.mode === 'debate' ? 'flex' : 'none';

        if (this.mode === 'template') {
          this._renderTemplateGrid();
        }
      });
    });
  }

  _bindTemplateChips() {
    const container = $('#template-chips');
    if (!container) return;

    container.innerHTML = TEMPLATES.map(t => `
      <span class="template-chip" data-id="${t.id}">${t.name}</span>
    `).join('');

    container.querySelectorAll('.template-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const id = chip.dataset.id;
        container.querySelectorAll('.template-chip').forEach(c => c.classList.remove('active'));
        if (this.activeTemplate === id) {
          this.activeTemplate = null;
        } else {
          chip.classList.add('active');
          this.activeTemplate = id;
          $('#chat-input').placeholder = `已选「${TEMPLATES.find(t => t.id === id)?.name}」，输入补充问题或直接发送...`;
        }
      });
    });
  }

  _renderTemplateGrid() {
    const messages = $('#chat-messages');
    if (!messages) return;

    messages.innerHTML = `
      <div class="template-grid">
        ${TEMPLATES.map(t => `
          <div class="template-card${this.activeTemplate === t.id ? ' selected' : ''}" data-id="${t.id}">
            <div class="template-card-name">${t.name}</div>
            <div class="template-card-desc">${t.desc}</div>
            <div class="template-card-data">所需数据：${t.data}</div>
          </div>
        `).join('')}
      </div>
      <p style="text-align:center;font-size:10px;color:var(--text-muted);margin-top:12px;">
        选择模板 → 自动加载所需数据 → 发送给 AI → 流式展示结构化分析结果
      </p>
    `;

    messages.querySelectorAll('.template-card').forEach(card => {
      card.addEventListener('click', () => {
        this.activeTemplate = card.dataset.id;
        this._renderTemplateGrid();
        this._sendTemplateMessage(this.activeTemplate);
      });
    });
  }

  _bindChatInput() {
    const input = $('#chat-input');
    const sendBtn = $('#btn-chat-send');
    const stopBtn = $('#btn-chat-stop');

    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._sendMessage();
      }
    });

    sendBtn?.addEventListener('click', () => this._sendMessage());
    stopBtn?.addEventListener('click', () => this._stopStreaming());
  }

  async _sendMessage() {
    const input = $('#chat-input');
    const text = input.value.trim();
    if (!text || this.isStreaming) return;
    input.value = '';

    const messages = $('#chat-messages');
    messages.appendChild(this._createBubble('user', text));
    messages.scrollTop = messages.scrollHeight;

    if (!this.app.state.currentStock) {
      messages.appendChild(this._createBubble('ai', '请先在顶部输入股票代码'));
      return;
    }

    this._setStreaming(true);
    this.currentAiBubble = this._createBubble('ai', '');
    messages.appendChild(this.currentAiBubble);

    const ws = this.app.api.connectWebSocket();
    const payload = this.activeTemplate
      ? { type: 'template', template_id: this.activeTemplate, stock_code: this.app.state.currentStock.code }
      : { type: 'chat', message: text, stock_code: this.app.state.currentStock.code };

    this.app.api.sendWebSocket(payload);

    const onMessage = (msg) => {
      if (msg.event === 'token') {
        this.currentAiBubble.querySelector('.chat-bubble').innerHTML += msg.data;
        messages.scrollTop = messages.scrollHeight;
      } else if (msg.event === 'section') {
        const bubble = this.currentAiBubble.querySelector('.chat-bubble');
        bubble.innerHTML += `<h3 style="color:var(--accent-soft);margin-top:8px;">${msg.title || ''}</h3>`;
      } else if (msg.event === 'done') {
        this._setStreaming(false);
        this.app.api.offWs('message', onMessage);
      }
    };

    this.app.api.onWs('message', onMessage);
  }

  async _sendTemplateMessage(templateId) {
    if (!this.app.state.currentStock) return;
    this._setStreaming(true);

    const messages = $('#chat-messages');
    messages.innerHTML = '';
    this.currentAiBubble = this._createBubble('ai', '');
    messages.appendChild(this.currentAiBubble);

    const ws = this.app.api.connectWebSocket();
    this.app.api.sendWebSocket({
      type: 'template',
      template_id: templateId,
      stock_code: this.app.state.currentStock.code,
    });

    const onMessage = (msg) => {
      if (msg.event === 'token') {
        this.currentAiBubble.querySelector('.chat-bubble').innerHTML += msg.data;
        messages.scrollTop = messages.scrollHeight;
      } else if (msg.event === 'section') {
        const bubble = this.currentAiBubble.querySelector('.chat-bubble');
        bubble.innerHTML += `<h3 style="color:var(--accent-soft);margin-top:8px;">${msg.title || ''}</h3>`;
      } else if (msg.event === 'done') {
        this._setStreaming(false);
        this.app.api.offWs('message', onMessage);
      }
    };

    this.app.api.onWs('message', onMessage);
  }

  _createBubble(role, text) {
    return h('div', { className: `chat-message ${role}` },
      h('div', { className: `chat-avatar ${role}`, innerHTML: role === 'ai' ? 'AI' : 'U' }),
      h('div', { className: 'chat-bubble', innerHTML: text }),
    );
  }

  _setStreaming(streaming) {
    this.isStreaming = streaming;
    $('#btn-chat-send').style.display = streaming ? 'none' : 'flex';
    $('#btn-chat-stop').style.display = streaming ? 'flex' : 'none';
  }

  _stopStreaming() {
    this.app.api.closeWebSocket();
    this.app.api.connectWebSocket();
    this._setStreaming(false);
    if (this.currentAiBubble) {
      const bubble = this.currentAiBubble.querySelector('.chat-bubble');
      if (bubble && !bubble.textContent.trim()) {
        bubble.textContent = '[已取消]';
      }
    }
  }

  _bindDebateControls() {
    this.app.on('view:changed', (d) => {
      if (d.view === 'ai' && this.mode === 'debate' && this.app.state.currentStock) {
        this._startDebate();
      }
    });
  }

  async _startDebate() {
    const cols = $('#debate-columns');
    const consensus = $('#debate-consensus');
    if (!cols) return;

    cols.innerHTML = `
      <div class="debate-col"><div class="debate-col-header value">价值投资者</div><div class="debate-col-body" id="debate-value">分析中...</div></div>
      <div class="debate-col"><div class="debate-col-header growth">成长投资者</div><div class="debate-col-body" id="debate-growth">分析中...</div></div>
      <div class="debate-col"><div class="debate-col-header risk">风控分析师</div><div class="debate-col-body" id="debate-risk">分析中...</div></div>
    `;

    const ws = this.app.api.connectWebSocket();
    this.app.api.sendWebSocket({
      type: 'debate',
      topic: `${this.app.state.currentStock.name || this.app.state.currentStock.code} 投资价值分析`,
      stock_code: this.app.state.currentStock.code,
    });

    const onMessage = (msg) => {
      if (msg.event === 'debate_round') {
        this.debateRound = msg.round;
        const analystMap = { value: 'debate-value', growth: 'debate-growth', risk: 'debate-risk' };
        const col = document.getElementById(analystMap[msg.analyst]);
        if (col) col.innerHTML += `<p>${msg.data || ''}</p>`;
        cols.scrollTop = cols.scrollHeight;
      } else if (msg.event === 'done') {
        consensus.innerHTML = `
          <div class="debate-consensus-label">共识结论 (第${this.debateRound}轮)</div>
          <div class="debate-consensus-text">${msg.summary || '分析完成'}</div>
        `;
        this.app.api.offWs('message', onMessage);
      }
    };

    this.app.api.onWs('message', onMessage);
  }

  _renderContextPanel() {
    const panel = $('#ai-context-panel');
    if (!panel) return;

    const stock = this.app.state.currentStock;
    const kpi = this.app.state.kpiData;

    panel.innerHTML = `
      <div class="ctx-section">
        <div class="ctx-section-title">当前股票</div>
        ${stock ? `
          <div class="ctx-card">
            <div class="ctx-card-title">${stock.code} ${stock.name || ''}</div>
            <div class="ctx-card-text">
              ${kpi ? `最新价 ${kpi.latest_price || '--'} · PE ${kpi.pe_ratio || '--'}` : '数据加载中...'}
            </div>
          </div>
        ` : '<div class="ctx-card-text text-muted">未选择股票</div>'}
      </div>
      <div class="ctx-section">
        <div class="ctx-section-title">分析历史</div>
        <div class="ctx-card-text text-muted" id="ctx-history">--</div>
      </div>
    `;

    try {
      const history = JSON.parse(localStorage.getItem('fa_analysis_history') || '[]');
      const ctxHistory = $('#ctx-history');
      if (ctxHistory && history.length) {
        ctxHistory.innerHTML = history.slice(0, 5).map(h =>
          `<div style="margin-bottom:2px;">${h.name} · <span style="color:var(--text-disabled)">${h.time}</span></div>`
        ).join('');
      }
    } catch {}
  }

  _toggleAiPanel() {
    const panel = $('#ai-panel');
    if (!panel) return;
    const isOpen = panel.style.display === 'flex';
    panel.style.display = isOpen ? 'none' : 'flex';

    if (!isOpen) {
      this._renderAiPanelContext();
      $('#ai-panel-input')?.focus();
    }
  }

  _renderAiPanelContext() {
    const ctx = $('#ai-panel-context');
    if (!ctx) return;
    const stock = this.app.state.currentStock;
    ctx.innerHTML = stock
      ? `<div class="ctx-section-title" style="text-align:center;">上下文：${stock.code} ${stock.name || ''} 当前数据</div>`
      : '<div class="ctx-section-title" style="text-align:center;">未选择股票</div>';
  }

  _closeOverlays() {
    $('#ai-panel').style.display = 'none';
    $('#command-palette').style.display = 'none';
  }
}

function initChat() {
  const app = window.__app;
  if (app) new ChatView(app);
  else setTimeout(initChat, 50);
}
initChat();
