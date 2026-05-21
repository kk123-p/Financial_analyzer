/**
 * Financial Analyzer Pro v11 — Precision Glass UI Interactions
 * 精密玻璃美学：平滑过渡、模态动画、页面加载交错效果
 */

// ---- 页面加载动画 ----
(function initPageLoad() {
    // 在 DOM 就绪后为关键区域触发入场动画
    function animateEntry() {
        const zones = [
            document.querySelector('.sidebar-logo'),
            document.querySelector('.top-bar'),
            ...document.querySelectorAll('.kpi-card'),
            document.querySelector('.content-area'),
            document.querySelector('.status-bar'),
        ];
        zones.forEach((el, i) => {
            if (!el) return;
            const delay = i < 2 ? i * 100 : (i - 1) * 40 + 180;
            el.style.opacity = '0';
            el.style.animation = `fade-up ${i < 4 ? '350ms' : '280ms'} var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1)) both`;
            el.style.animationDelay = delay + 'ms';
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', animateEntry);
    } else {
        animateEntry();
    }
})();

// ---- 结果内容淡入观察器 ----
(function initResultObserver() {
    const observer = new MutationObserver(function(mutations) {
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (node.nodeType === 1 && node.id === 'result-content') {
                    node.style.animation = 'fade-up 300ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1)) both';
                }
            }
        }
    });
    const resultEl = document.getElementById('result-content');
    if (resultEl) {
        observer.observe(resultEl.parentElement || resultEl, { childList: true, subtree: false });
    }
})();

// ---- Tab 切换 — 交叉淡入 ----
function switchTab(tabName, btn) {
    document.querySelectorAll('.tabs > .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    const oldPanel = document.querySelector('.tab-panel.active');
    const newPanel = document.getElementById('tab-' + tabName);

    if (oldPanel && newPanel && oldPanel !== newPanel) {
        oldPanel.style.opacity = '1';
        oldPanel.style.transition = 'opacity 120ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1)), transform 120ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1))';
        oldPanel.style.transform = 'translateY(4px)';
        oldPanel.style.opacity = '0';
        const finish = function() {
            oldPanel.removeEventListener('transitionend', finish);
            oldPanel.classList.remove('active');
            oldPanel.style.opacity = '';
            oldPanel.style.transform = '';
            oldPanel.style.transition = '';
            newPanel.classList.add('active');
            newPanel.style.opacity = '0';
            newPanel.style.transform = 'translateY(-4px)';
            newPanel.style.transition = 'opacity 200ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1)), transform 200ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1))';
            requestAnimationFrame(function() {
                newPanel.style.opacity = '1';
                newPanel.style.transform = 'translateY(0)';
                const cleanup = function() {
                    newPanel.removeEventListener('transitionend', cleanup);
                    newPanel.style.transition = '';
                };
                newPanel.addEventListener('transitionend', cleanup);
            });
        };
        oldPanel.addEventListener('transitionend', finish);
    } else if (newPanel && !oldPanel) {
        newPanel.classList.add('active');
    } else if (newPanel && oldPanel === newPanel) {
        // 已经是活跃面板，无需操作
    }

    // 切换到图表 tab 时自动加载 K线图
    if (tabName === 'charts') {
        loadChart('candlestick', document.querySelector('.chart-type-btn.active') || document.querySelector('.chart-type-btn'));
    }
}

// ---- AI 子标签切换 ----
function switchAiTab(tab, btn) {
    btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.getElementById('ai-chat-panel').style.display = tab === 'chat' ? 'flex' : 'none';
    document.getElementById('ai-debate-panel').style.display = tab === 'debate' ? 'flex' : 'none';
}

// ---- 侧边栏 — 平滑展开/折叠 + 高度动画 ----
function toggleSection(header) {
    const arrow = header.querySelector('.arrow');
    const items = header.nextElementSibling;
    const isOpen = arrow.classList.contains('open');

    if (isOpen) {
        arrow.classList.remove('open');
        items.style.overflow = 'hidden';
        items.style.transition = 'max-height 250ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1))';
        items.style.maxHeight = items.scrollHeight + 'px';
        requestAnimationFrame(function() {
            items.style.maxHeight = '0px';
        });
    } else {
        arrow.classList.add('open');
        items.style.overflow = 'hidden';
        items.style.transition = 'max-height 250ms var(--ease-out-expo, cubic-bezier(0.16,1,0.3,1))';
        items.style.maxHeight = '0px';
        requestAnimationFrame(function() {
            items.style.maxHeight = items.scrollHeight + 'px';
            const cleanup = function() {
                items.removeEventListener('transitionend', cleanup);
                items.style.overflow = '';
                items.style.maxHeight = '';
                items.style.transition = '';
            };
            items.addEventListener('transitionend', cleanup);
        });
    }
}

// ---- 导航激活 ----
function activateNav(row) {
    document.querySelectorAll('.nav-item-row').forEach(r => r.classList.remove('active'));
    row.classList.add('active');
    document.querySelector('.tab-btn.active')?.classList.remove('active');
    const analysisTab = document.querySelector('.tabs > .tab-btn');
    if (analysisTab) {
        analysisTab.classList.add('active');
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        document.getElementById('tab-analysis')?.classList.add('active');
    }
}

// ---- 图表加载 ----
function loadChart(chartType, btn) {
    if (btn) {
        btn.parentElement.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    const container = document.getElementById('chart-container');
    if (!container) return;
    container.innerHTML = '<div class="result-empty">加载中...</div>';

    fetch('/chart/' + chartType)
        .then(r => r.json())
        .then(fig => {
            if (fig.data && fig.data.length > 0) {
                Plotly.newPlot('chart-container', fig.data, fig.layout, {
                    responsive: true,
                    displayModeBar: true,
                    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                    displaylogo: false,
                });
            } else {
                container.innerHTML = '<div class="result-empty">暂无数据</div>';
            }
        })
        .catch(() => {
            container.innerHTML = '<div class="result-empty">图表加载失败</div>';
        });
}

function loadChartImg(chartType, btn) {
    if (btn) {
        btn.parentElement.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    const container = document.getElementById('chart-container');
    if (!container) return;
    container.innerHTML = '<div class="result-empty">加载中...</div>';

    fetch('/chart/img/' + chartType)
        .then(r => r.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            container.innerHTML = `<img src="${url}" style="max-width:100%;height:auto;" onload="URL.revokeObjectURL(this.src)">`;
        })
        .catch(() => {
            container.innerHTML = '<div class="result-empty">图表加载失败</div>';
        });
}

// ---- AI 辩论 WebSocket (3轮完整辩论) ----
let debateWs = null;

// 分析师显示名与颜色
const ANALYST_DISPLAY = {
    value:   { name: '价值分析师', icon: '💰', color: 'var(--accent-primary)' },
    growth:  { name: '成长分析师', icon: '🚀', color: 'var(--positive)' },
    risk:    { name: '风控分析师', icon: '🛡️', color: 'var(--warning)' },
    consensus: { name: '综合共识', icon: '📊', color: '#A78BFA' },
};

const ROUND_NAMES = {
    round1_start: '第1轮：独立陈述',
    round2_start: '第2轮：交叉质询',
    round3_start: '第3轮：共识与情景概率',
};

function startDebate() {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    if (debateWs && debateWs.readyState === WebSocket.OPEN) {
        debateWs.close();
    }

    const stream = document.getElementById('debate-stream');
    stream.innerHTML = '<p style="color:var(--accent-primary)">正在连接辩论引擎...</p>';
    stream._roleEls = {};
    stream._currentRound = '';
    stream._fallbackEl = null;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ai/debate`;

    try {
        debateWs = new WebSocket(wsUrl);

        debateWs.onopen = function() {
            stream.innerHTML = '<p style="color:var(--accent-primary)">已连接，正在准备辩论数据...</p>';
            debateWs.send(JSON.stringify({ stock_code: stockCode }));
        };

        debateWs.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'meta') {
                if (msg.content in ROUND_NAMES) {
                    stream._currentRound = msg.content;
                    const roundDiv = document.createElement('div');
                    roundDiv.className = 'debate-round-header';
                    roundDiv.textContent = ROUND_NAMES[msg.content];
                    stream.appendChild(roundDiv);
                    stream.scrollTop = stream.scrollHeight;
                }
                else if (msg.content.startsWith('analyst_') && msg.content.endsWith('_start')) {
                    const roleKey = msg.content.replace('analyst_', '').replace('_start', '');
                    const analyst = ANALYST_DISPLAY[roleKey];
                    if (analyst && !stream._roleEls[roleKey]) {
                        const header = document.createElement('div');
                        header.className = 'debate-analyst-header';
                        header.innerHTML = `<span>${analyst.icon}</span> ${analyst.name}`;
                        header.style.color = analyst.color;
                        stream.appendChild(header);
                        stream._roleEls[roleKey] = document.createElement('div');
                        stream._roleEls[roleKey].className = 'debate-analyst-text';
                        stream.appendChild(stream._roleEls[roleKey]);
                        stream.scrollTop = stream.scrollHeight;
                    }
                }
                else if (msg.content === 'debate_complete') {
                    const doneEl = document.createElement('p');
                    doneEl.style.cssText = 'color:var(--positive);margin-top:12px;';
                    doneEl.textContent = '✅ 辩论完成';
                    stream.appendChild(doneEl);
                }
                else if (msg.content.startsWith('error:')) {
                    stream.insertAdjacentHTML('beforeend', `<p style="color:var(--negative);">⚠️ ${msg.content.substring(6)}</p>`);
                }
            }
            else if (msg.type === 'chunk') {
                let roleKey = msg.role;
                if (roleKey === 'consensus') {
                    if (!stream._roleEls['consensus']) {
                        const header = document.createElement('div');
                        header.className = 'debate-analyst-header';
                        const a = ANALYST_DISPLAY.consensus;
                        header.innerHTML = `<span>${a.icon}</span> ${a.name}`;
                        header.style.color = a.color;
                        stream.appendChild(header);
                        stream._roleEls['consensus'] = document.createElement('div');
                        stream._roleEls['consensus'].className = 'debate-analyst-text';
                        stream.appendChild(stream._roleEls['consensus']);
                    }
                    stream._roleEls['consensus'].textContent += msg.content;
                } else if (stream._roleEls[roleKey]) {
                    stream._roleEls[roleKey].textContent += msg.content;
                } else {
                    if (!stream._fallbackEl) {
                        stream._fallbackEl = document.createElement('p');
                        stream.appendChild(stream._fallbackEl);
                    }
                    stream._fallbackEl.textContent += msg.content;
                }
                stream.scrollTop = stream.scrollHeight;
            }
            else if (msg.type === 'done') {
                stream._roleEls = {};
                stream.insertAdjacentHTML('beforeend', '<p style="color:var(--positive);margin-top:8px;">--- 辩论结束 ---</p>');
                stream.scrollTop = stream.scrollHeight;
            }
            else if (msg.type === 'status') {
                stream.insertAdjacentHTML('beforeend', `<p style="color:var(--text-muted);">${msg.content}</p>`);
            }
            else if (msg.type === 'error') {
                stream.insertAdjacentHTML('beforeend', `<p style="color:var(--negative);">⚠️ ${msg.content}</p>`);
            }
        };

        debateWs.onerror = function() {
            stream.insertAdjacentHTML('beforeend', '<p style="color:var(--negative);">⚠️ WebSocket 连接失败，请检查网络或API Key配置</p>');
        };

        debateWs.onclose = function() {
            stream._roleEls = {};
            stream._fallbackEl = null;
        };
    } catch (e) {
        stream.innerHTML = `<p style="color:var(--negative);">⚠️ 连接失败: ${e.message}</p>`;
    }
}

// ---- 导出 ----
function exportData(format) {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || 'data';
    window.open('/export/' + format + '?stock_code=' + encodeURIComponent(stockCode), '_blank');
}

// ---- 时钟 ----
function updateClock() {
    const now = new Date();
    const ts = now.toLocaleTimeString('zh-CN', { hour12: false });
    const el = document.getElementById('clock');
    if (el) el.textContent = ts;
}
setInterval(updateClock, 1000);
updateClock();

// ---- 模态框 — 带 CSS 过渡支持 ----
function openModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = 'flex';
    // 强制回流后添加 visible 类以触发 CSS 过渡
    requestAnimationFrame(function() {
        el.classList.add('modal--visible');
    });
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('modal--visible');
    // 等待过渡完成后隐藏
    el.addEventListener('transitionend', function handler() {
        el.removeEventListener('transitionend', handler);
        el.style.display = 'none';
    });
}

// 点击遮罩关闭
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal(e.target.id);
    }
});

// ---- 键盘快捷键 ----
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        document.querySelector('.top-bar button[type="submit"]')?.click();
    }
});

// ---- Plotly resize ----
window.addEventListener('resize', function() {
    const chartContainer = document.getElementById('chart-container');
    if (chartContainer && chartContainer._fullLayout) {
        Plotly.Plots.resize(chartContainer);
    }
});

// ============================================================================
// Phase 2: 统一 AI 对话 WebSocket 客户端
// ============================================================================

let chatWs = null;
let chatInProgress = false;

function sendQuick(question) {
    document.getElementById('chat-input').value = question;
    sendMessage();
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || chatInProgress) return;

    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    const emptyEl = document.getElementById('chat-empty');
    if (emptyEl) emptyEl.style.display = 'none';

    const messages = document.getElementById('chat-messages');

    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble chat-bubble--user';
    userBubble.textContent = message;
    messages.appendChild(userBubble);
    messages.scrollTop = messages.scrollHeight;

    input.value = '';
    chatInProgress = true;

    document.getElementById('chat-send-btn').style.display = 'none';
    document.getElementById('chat-stop-btn').style.display = 'inline-block';

    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({ type: 'message', content: message }));
        return;
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + location.host + '/ai/conversation';

    try {
        chatWs = new WebSocket(wsUrl);
        let _currentAssistantEl = null;

        chatWs.onopen = function() {
            chatWs.send(JSON.stringify({ stock_code: stockCode }));
            setTimeout(function() {
                if (chatWs.readyState === WebSocket.OPEN) {
                    chatWs.send(JSON.stringify({ type: 'message', content: message }));
                }
            }, 200);
        };

        chatWs.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'meta') {
                if (msg.content === 'ready') return;

                if (msg.content.startsWith('intent:')) {
                    const intent = msg.content.replace('intent:', '');
                    const sysEl = document.createElement('div');
                    sysEl.className = 'chat-system';
                    const intentLabels = { quick: '快速问答', deep: '深度分析', debate: '三方辩论', followup: '追问' };
                    sysEl.textContent = intentLabels[intent] || intent;
                    // Insert AFTER the last user bubble (so it appears between user question and AI response)
                    const userBubbles = messages.querySelectorAll('.chat-bubble--user');
                    if (userBubbles.length > 0) {
                        const lastUserBubble = userBubbles[userBubbles.length - 1];
                        lastUserBubble.insertAdjacentElement('afterend', sysEl);
                    } else {
                        messages.appendChild(sysEl);
                    }
                    messages.scrollTop = messages.scrollHeight;
                } else if (msg.content === 'debate_start') {
                    const header = document.createElement('div');
                    header.className = 'debate-round-header';
                    header.textContent = '三方辩论开始';
                    messages.appendChild(header);
                    messages.scrollTop = messages.scrollHeight;
                } else if (msg.content.startsWith('section:')) {
                    _currentAssistantEl = null;
                }
            } else if (msg.type === 'chunk') {
                if (!_currentAssistantEl) {
                    _currentAssistantEl = document.createElement('div');
                    _currentAssistantEl.className = 'chat-bubble chat-bubble--assistant';
                    messages.appendChild(_currentAssistantEl);
                }
                _currentAssistantEl.textContent += msg.content;
                messages.scrollTop = messages.scrollHeight;
            } else if (msg.type === 'structured') {
                const card = buildStructuredCard(msg.content, msg.meta || {});
                messages.appendChild(card);
                _currentAssistantEl = null;
                messages.scrollTop = messages.scrollHeight;
            } else if (msg.type === 'done') {
                _currentAssistantEl = null;
                chatInProgress = false;
                document.getElementById('chat-send-btn').style.display = 'inline-block';
                document.getElementById('chat-stop-btn').style.display = 'none';
            } else if (msg.type === 'error') {
                const errEl = document.createElement('div');
                errEl.className = 'chat-bubble chat-bubble--assistant';
                errEl.style.color = 'var(--negative)';
                errEl.textContent = '⚠️ ' + msg.content;
                messages.appendChild(errEl);
                // Add retry hint
                const retryEl = document.createElement('div');
                retryEl.style.cssText = 'text-align:center;margin-top:4px;';
                retryEl.innerHTML = '<span onclick="resetChat()" style="color:var(--accent-primary);cursor:pointer;font-size:var(--text-xs);">↺ 开始新对话</span>';
                messages.appendChild(retryEl);
                messages.scrollTop = messages.scrollHeight;
                chatInProgress = false;
                document.getElementById('chat-send-btn').style.display = 'inline-block';
                document.getElementById('chat-stop-btn').style.display = 'none';
            }
        };

        chatWs.onerror = function() {
            const errEl = document.createElement('div');
            errEl.className = 'chat-bubble chat-bubble--assistant';
            errEl.style.color = 'var(--negative)';
            errEl.textContent = '⚠️ 连接失败，请检查 API Key 配置';
            messages.appendChild(errEl);
            // Add retry hint
            const retryEl = document.createElement('div');
            retryEl.style.cssText = 'text-align:center;margin-top:4px;';
            retryEl.innerHTML = '<span onclick="resetChat()" style="color:var(--accent-primary);cursor:pointer;font-size:var(--text-xs);">↺ 开始新对话</span>';
            messages.appendChild(retryEl);
            chatInProgress = false;
            document.getElementById('chat-send-btn').style.display = 'inline-block';
            document.getElementById('chat-stop-btn').style.display = 'none';
        };

        chatWs.onclose = function() {
            chatWs = null;
            chatInProgress = false;
            document.getElementById('chat-send-btn').style.display = 'inline-block';
            document.getElementById('chat-stop-btn').style.display = 'none';
        };
    } catch (e) {
        const errEl = document.createElement('div');
        errEl.className = 'chat-bubble chat-bubble--assistant';
        errEl.style.color = 'var(--negative)';
        errEl.textContent = '⚠️ 连接失败: ' + e.message;
        messages.appendChild(errEl);
        // Add retry hint
        const retryEl = document.createElement('div');
        retryEl.style.cssText = 'text-align:center;margin-top:4px;';
        retryEl.innerHTML = '<span onclick="resetChat()" style="color:var(--accent-primary);cursor:pointer;font-size:var(--text-xs);">↺ 开始新对话</span>';
        messages.appendChild(retryEl);
        chatInProgress = false;
        document.getElementById('chat-send-btn').style.display = 'inline-block';
        document.getElementById('chat-stop-btn').style.display = 'none';
    }
}

function stopAnalysis() {
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({ type: 'stop' }));
    }
}

function buildStructuredCard(text, meta) {
    const card = document.createElement('div');
    card.className = 'chat-structured';

    const sections = text.split(/(?=📊|🔍|✅)/);
    sections.forEach(function(section) {
        const secDiv = document.createElement('div');
        secDiv.className = 'cs-section';

        let labelClass = 'cs-label ';
        if (section.startsWith('📊')) {
            labelClass += 'cs-label--data';
        } else if (section.startsWith('🔍')) {
            labelClass += 'cs-label--reason';
        } else if (section.startsWith('✅')) {
            labelClass += 'cs-label--conclusion';
        }

        const nlIdx = section.indexOf('\n');
        const title = nlIdx > -1 ? section.substring(0, nlIdx) : section;
        const body = nlIdx > -1 ? section.substring(nlIdx + 1).replace(/\n/g, '<br>') : '';

        secDiv.innerHTML = '<div class="' + labelClass + '">' + title + '</div>' +
            (body ? '<div style="color:var(--text-secondary);">' + body + '</div>' : '');
        card.appendChild(secDiv);
    });

    if (meta.confidence && meta.confidence !== '未标注') {
        const badge = document.createElement('span');
        badge.className = 'confidence-badge confidence-badge--' +
            (meta.confidence === '高' ? 'high' : meta.confidence === '中' ? 'medium' : 'low');
        badge.textContent = '置信度 ' + meta.confidence;
        card.appendChild(badge);
    }

    if (meta.signal_tags && meta.signal_tags.length > 0) {
        const tagsDiv = document.createElement('div');
        tagsDiv.className = 'signal-tags';
        meta.signal_tags.forEach(function(tag) {
            const tagSpan = document.createElement('span');
            const value = typeof tag === 'string' ? tag : (tag.name + ' ' + (tag.value || ''));
            const level = value.includes('高') || value.includes('优') ? 'good' :
                          value.includes('低') || value.includes('差') ? 'bad' : 'warn';
            tagSpan.className = 'signal-tag signal-tag--' + level;
            tagSpan.textContent = value;
            tagsDiv.appendChild(tagSpan);
        });
        card.appendChild(tagsDiv);
    }

    return card;
}

function resetChat() {
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.close();
    }
    chatWs = null;
    chatInProgress = false;

    const messages = document.getElementById('chat-messages');
    // Remove all children except chat-empty
    while (messages.firstChild) {
        messages.removeChild(messages.firstChild);
    }
    // Re-create chat-empty
    const emptyEl = document.createElement('div');
    emptyEl.className = 'chat-empty';
    emptyEl.id = 'chat-empty';
    emptyEl.innerHTML = '<div style="font-size:40px;opacity:0.3;margin-bottom:8px;">📊</div>' +
        '<div>AI 财务分析助手</div>' +
        '<div class="hint">支持快速问答、深度分析（/deep）和三方辩论（/debate）</div>' +
        '<div class="quick-actions">' +
        '<button class="quick-action" onclick="sendQuick(\'分析盈利能力\')">分析盈利能力</button>' +
        '<button class="quick-action" onclick="sendQuick(\'评估财务风险\')">评估财务风险</button>' +
        '<button class="quick-action" onclick="sendQuick(\'/deep 全面深度分析\')">全面深度分析</button>' +
        '<button class="quick-action" onclick="sendQuick(\'/debate\')">三方辩论</button>' +
        '</div>';
    messages.appendChild(emptyEl);

    document.getElementById('chat-send-btn').style.display = 'inline-block';
    document.getElementById('chat-stop-btn').style.display = 'none';
    document.getElementById('chat-input').value = '';
}

// DEPRECATED: 旧 AI 函数保留以便向后兼容
function switchAiTab(tab, btn) { /* 统一对话面板已替代子标签 */ }
function startDebate() { sendQuick('/debate'); }
