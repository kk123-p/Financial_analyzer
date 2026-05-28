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
    if (tabName === 'ai') { loadTemplates(); }
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

// ---- 图表加载（ECharts） ----
function loadChart(chartType, btn) {
    if (btn) {
        btn.parentElement.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    var container = document.getElementById('chart-container');
    if (!container) return;

    // 显示加载状态
    container.innerHTML = '<div class="result-empty">加载中...</div>';

    fetch('/chart/' + chartType)
        .then(function(r) { return r.json(); })
        .then(function(option) {
            // 检查是否是空数据响应
            if (!option.series || option.series.length === 0) {
                container.innerHTML = '<div class="result-empty">暂无数据</div>';
                return;
            }

            // 清除加载提示，准备 ECharts 容器
            container.innerHTML = '';

            var chart = EchartsUtils.init('chart-container');
            if (chart) {
                EchartsUtils.setOption(chart, option);
            } else {
                container.innerHTML = '<div class="result-empty">图表初始化失败</div>';
            }
        })
        .catch(function() {
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

// ---- ECharts resize handled by echarts-utils.js ----


// ============================================================================
// Phase 2: 统一 AI 对话 WebSocket 客户端
// ============================================================================

let chatWs = null;
let chatInProgress = false;
let _wsOnReady = null;  // callback fired after WebSocket onopen

function _openConversationWs(stockCode, onReady) {
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        if (onReady) onReady();
        return;
    }
    var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    var wsUrl = protocol + '//' + location.host + '/ai/conversation';
    _wsOnReady = onReady;

    chatWs = new WebSocket(wsUrl);
    window._conversationWs = chatWs;
    var messages = document.getElementById('chat-messages');
    var _currentAssistantEl = null;

    chatWs.onopen = function() {
        chatWs.send(JSON.stringify({ stock_code: stockCode }));
        if (_wsOnReady) {
            _wsOnReady();
            _wsOnReady = null;
        }
    };

    chatWs.onmessage = function(event) {
        var msg = JSON.parse(event.data);

        if (msg.type === 'meta') {
            if (msg.content === 'ready') return;

            if (msg.content.startsWith('intent:')) {
                var intent = msg.content.replace('intent:', '');
                var sysEl = document.createElement('div');
                sysEl.className = 'chat-system';
                var intentLabels = { quick: '快速问答', deep: '深度分析', debate: '三方辩论', followup: '追问' };
                sysEl.textContent = intentLabels[intent] || intent;
                var userBubbles = messages.querySelectorAll('.chat-bubble--user');
                if (userBubbles.length > 0) {
                    userBubbles[userBubbles.length - 1].insertAdjacentElement('afterend', sysEl);
                } else {
                    messages.appendChild(sysEl);
                }
                messages.scrollTop = messages.scrollHeight;
            } else if (msg.content === 'debate_start') {
                var header = document.createElement('div');
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
            var card = buildStructuredCard(msg.content, msg.meta || {});
            messages.appendChild(card);
            _currentAssistantEl = null;
            messages.scrollTop = messages.scrollHeight;
        } else if (msg.type === 'done') {
            _currentAssistantEl = null;
            chatInProgress = false;
            document.getElementById('chat-send-btn').style.display = 'inline-block';
            document.getElementById('chat-stop-btn').style.display = 'none';
        } else if (msg.type === 'template_start') {
            appendMeta('🔍 执行模板分析: ' + (msg.meta ? msg.meta.template : '') + ' (' + (msg.meta ? msg.meta.sections : '') + ' 个维度)');
        } else if (msg.type === 'template_section') {
            appendSectionCard(msg.content, msg.meta);
        } else if (msg.type === 'template_done') {
            appendMeta('✅ 模板分析完成');
        } else if (msg.type === 'error') {
            var errEl = document.createElement('div');
            errEl.className = 'chat-bubble chat-bubble--assistant';
            errEl.style.color = 'var(--negative)';
            errEl.textContent = '⚠️ ' + msg.content;
            messages.appendChild(errEl);
            var retryEl = document.createElement('div');
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
        var errEl = document.createElement('div');
        errEl.className = 'chat-bubble chat-bubble--assistant';
        errEl.style.color = 'var(--negative)';
        errEl.textContent = '⚠️ 连接失败，请检查 API Key 配置';
        messages.appendChild(errEl);
        var retryEl = document.createElement('div');
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

    _openConversationWs(stockCode, function() {
        setTimeout(function() {
            if (chatWs && chatWs.readyState === WebSocket.OPEN) {
                chatWs.send(JSON.stringify({ type: 'message', content: message }));
            }
        }, 200);
    });
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
    while (messages.firstChild) {
        messages.removeChild(messages.firstChild);
    }
    // Re-create chat-empty with template-populated quick-actions
    const emptyEl = document.createElement('div');
    emptyEl.className = 'chat-empty';
    emptyEl.id = 'chat-empty';
    emptyEl.innerHTML = '<div style="font-size:40px;opacity:0.3;margin-bottom:8px;">📊</div>' +
        '<div>AI 财务分析助手</div>' +
        '<div class="quick-actions" id="template-quick-actions">' +
        '<div class="hint" style="margin-bottom:6px;">选择一个模板开始分析，或直接输入问题自由提问</div>' +
        '</div>';
    messages.appendChild(emptyEl);

    document.getElementById('chat-send-btn').style.display = 'inline-block';
    document.getElementById('chat-stop-btn').style.display = 'none';
    document.getElementById('chat-input').value = '';
    // 重新加载模板按钮
    loadTemplates();
}

function startDebate() {
    // Switch to the debate tab
    const debateBtn = document.querySelector('.tabs > .tab-btn:nth-child(5)'); // 5th tab
    if (debateBtn) {
        switchTab('debate', debateBtn);
    }
    // Auto-start debate
    setTimeout(function() { startDebateNew(); }, 300);
}


// ============================================================================
// AI 辩论 WebSocket 客户端 — 四区域布局版
// ============================================================================

const ANALYST_META = {
    'value':    { name: '格雷厄姆式价值分析师', icon: '📊', color: '#3B82F6' },
    'growth':   { name: '费雪式成长分析师', icon: '🚀', color: '#14B8A6' },
    'risk':     { name: '塔勒布式风控师', icon: '🛡️', color: '#F59E0B' },
    'consensus': { name: '综合共识', icon: '📋', color: '#A78BFA' },
};

const ROUND_NAMES = {
    'round1_start': '第1轮：独立陈述',
    'round2_start': '第2轮：交叉质询',
    'round3_start': '第3轮：共识与情景概率',
};

const BODY_IDS = {
    'value': 'debate-body-value',
    'growth': 'debate-body-growth',
    'risk': 'debate-body-risk',
};

let debateWs = null;
let debateRunning = false;
let debateData = {
    round1: {},
    round2: {},
    round3: {},
    consensus: '',
    followups: [],
};
let currentRoundKey = '';

function startDebateNew() {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    if (debateWs && debateWs.readyState === WebSocket.OPEN) {
        debateWs.close();
    }

    // 显示布局，隐藏空状态
    document.getElementById('debate-layout').style.display = 'flex';
    const emptyState = document.getElementById('debate-empty-state');
    if (emptyState) emptyState.style.display = 'none';

    // 清空三列
    ['value', 'growth', 'risk'].forEach(role => {
        document.getElementById(BODY_IDS[role]).textContent = '';
    });
    document.getElementById('debate-consensus-body').textContent = '';

    // 重置辩论数据
    debateData = { round1: {}, round2: {}, round3: {}, consensus: '', followups: [] };
    currentRoundKey = '';

    const statusEl = document.getElementById('debate-status');
    statusEl.textContent = '连接中...';

    const startBtn = document.getElementById('debate-start-btn');
    startBtn.disabled = true;
    startBtn.textContent = '辩论中...';
    debateRunning = true;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + location.host + '/ai/debate';

    try {
        debateWs = new WebSocket(wsUrl);

        debateWs.onopen = function() {
            statusEl.textContent = '已连接，准备数据...';
            debateWs.send(JSON.stringify({ stock_code: stockCode }));
        };

        debateWs.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'status') {
                statusEl.textContent = msg.content;
            }
            else if (msg.type === 'meta') {
                if (msg.content in ROUND_NAMES) {
                    currentRoundKey = msg.content.replace('_start', '');
                    statusEl.textContent = ROUND_NAMES[msg.content];
                }
                else if (msg.content.startsWith('analyst_') && msg.content.endsWith('_start')) {
                    const roleKey = msg.content.replace('analyst_', '').replace('_start', '');
                    if (roleKey === 'value' || roleKey === 'growth' || roleKey === 'risk') {
                        const body = document.getElementById(BODY_IDS[roleKey]);
                        const tag = document.createElement('span');
                        tag.className = 'debate-round-tag';
                        tag.textContent = ROUND_NAMES[currentRoundKey + '_start'] || currentRoundKey;
                        body.appendChild(tag);
                        body.appendChild(document.createTextNode('\n'));
                        body.scrollTop = body.scrollHeight;
                    }
                }
                else if (msg.content === 'debate_complete') {
                    statusEl.textContent = '辩论完成';
                    startBtn.disabled = false;
                    startBtn.textContent = '重新辩论';
                    debateRunning = false;
                }
                else if (msg.content.startsWith('error:')) {
                    statusEl.textContent = '出错: ' + msg.content.substring(6);
                    startBtn.disabled = false;
                    startBtn.textContent = '重试';
                    debateRunning = false;
                }
            }
            else if (msg.type === 'chunk') {
                const roleKey = msg.role;
                if (roleKey === 'consensus') {
                    const body = document.getElementById('debate-consensus-body');
                    body.textContent += msg.content;
                    debateData.consensus += msg.content;
                    body.scrollTop = body.scrollHeight;
                } else if (BODY_IDS[roleKey]) {
                    const body = document.getElementById(BODY_IDS[roleKey]);
                    body.textContent += msg.content;
                    body.scrollTop = body.scrollHeight;

                    // 收集到 debateData
                    const roundMap = { 'round1': 'round1', 'round2': 'round2', 'round3': 'round3' };
                    const rk = roundMap[currentRoundKey] || currentRoundKey;
                    if (rk && (rk === 'round1' || rk === 'round2' || rk === 'round3')) {
                        debateData[rk][roleKey] = (debateData[rk][roleKey] || '') + msg.content;
                    }
                }
            }
            else if (msg.type === 'done') {
                statusEl.textContent = '辩论结束';
                startBtn.disabled = false;
                startBtn.textContent = '重新辩论';
                debateRunning = false;
            }
            else if (msg.type === 'error') {
                statusEl.textContent = '出错: ' + (msg.content || '未知错误');
                // 在共识区显示错误详情
                const consensusBody = document.getElementById('debate-consensus-body');
                if (consensusBody && !consensusBody.textContent) {
                    consensusBody.textContent = '⚠️ ' + (msg.content || '辩论启动失败，请检查 API Key 配置和网络连接');
                }
                startBtn.disabled = false;
                startBtn.textContent = '重试';
                debateRunning = false;
            }
        };

        debateWs.onerror = function() {
            statusEl.textContent = '连接失败，请检查 API Key 配置';
            const consensusBody = document.getElementById('debate-consensus-body');
            if (consensusBody && !consensusBody.textContent) {
                consensusBody.textContent = '⚠️ WebSocket 连接失败，请检查：\n1. DeepSeek API Key 是否已配置\n2. 网络连接是否正常\n3. 服务器是否已启动';
            }
            startBtn.disabled = false;
            startBtn.textContent = '重试';
            debateRunning = false;
        };

        debateWs.onclose = function() {
            if (debateRunning) {
                statusEl.textContent = '连接断开';
                startBtn.disabled = false;
                startBtn.textContent = '重试';
                debateRunning = false;
            }
        };
    } catch (e) {
        statusEl.textContent = '连接失败: ' + e.message;
        startBtn.disabled = false;
        startBtn.textContent = '重试';
        debateRunning = false;
    }
}

function sendDebateFollowup() {
    const input = document.getElementById('debate-followup-input');
    const question = input.value.trim();
    if (!question) return;
    if (!debateWs || debateWs.readyState !== WebSocket.OPEN) {
        alert('辩论未连接或已结束，请重新开始辩论');
        return;
    }

    input.value = '';

    const fuEntry = { question: question, value: '', growth: '', risk: '' };
    debateData.followups.push(fuEntry);

    ['value', 'growth', 'risk'].forEach(role => {
        const body = document.getElementById(BODY_IDS[role]);
        const tag = document.createElement('span');
        tag.className = 'debate-round-tag';
        tag.textContent = '追问: ' + question.substring(0, 40) + (question.length > 40 ? '...' : '');
        body.appendChild(tag);
        body.appendChild(document.createTextNode('\n'));
        body.scrollTop = body.scrollHeight;
    });

    // 发送追问到服务器
    debateWs.send(JSON.stringify({ type: 'followup', content: question }));
}

function stopDebate() {
    if (debateWs && debateWs.readyState === WebSocket.OPEN) {
        debateWs.send(JSON.stringify({ type: 'stop' }));
        debateWs.close();
    }
    debateRunning = false;
    document.getElementById('debate-status').textContent = '已停止';
    const startBtn = document.getElementById('debate-start-btn');
    startBtn.disabled = false;
    startBtn.textContent = '重新辩论';
}

async function exportDebate(fmt) {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    try {
        const resp = await fetch('/ai/debate/export/' + fmt, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                debate_data: debateData,
                stock_code: stockCode,
                company_name: '',
            }),
        });
        if (resp.ok) {
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const ext = fmt === 'md' ? 'md' : 'html';
            a.download = 'debate_' + (stockCode || 'result') + '.' + ext;
            a.click();
            URL.revokeObjectURL(url);
        } else {
            const err = await resp.json();
            alert('导出失败: ' + (err.error || '未知错误'));
        }
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}


// ============================================================================
// Phase 2 UX: Prompt Lab + 数据/Prompt 查看
// ============================================================================

let currentTemplateName = '深度分析-默认';
let currentTemplateData = null;
let currentReportData = null;

// ---- 模板选择器 ----

async function loadTemplateList() {
    try {
        const resp = await fetch('/ai/prompts');
        const templates = await resp.json();
        const selector = document.getElementById('prompt-template-selector');
        if (!selector) return;
        selector.innerHTML = '';
        templates.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.name;
            opt.textContent = (t.is_default ? '⭐ ' : '') + t.name + ' (' + t.mode + ')';
            if (t.name === currentTemplateName) opt.selected = true;
            selector.appendChild(opt);
        });
    } catch (e) {
        console.error('加载模板列表失败:', e);
    }
}

async function onTemplateChange() {
    const selector = document.getElementById('prompt-template-selector');
    const name = selector.value;
    if (!name) return;
    currentTemplateName = name;
    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name));
        if (resp.ok) {
            currentTemplateData = await resp.json();
        }
    } catch (e) {
        console.error('加载模板失败:', e);
    }
}

// 页面加载时初始化
(function initPromptLab() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            loadTemplateList();
            fetch('/ai/prompts/' + encodeURIComponent('深度分析-默认'))
                .then(r => r.json())
                .then(d => { currentTemplateData = d; })
                .catch(() => {});
        });
    } else {
        loadTemplateList();
        fetch('/ai/prompts/' + encodeURIComponent('深度分析-默认'))
            .then(r => r.json())
            .then(d => { currentTemplateData = d; })
            .catch(() => {});
    }
})();

// ============================================================================
// AI 模板
// ============================================================================

var currentTemplate = null;

function loadTemplates() {
    fetch('/ai/prompts')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            // API returns array directly: [{name, description, mode, ...}]
            var list = Array.isArray(data) ? data : (data.templates || []);
            var templates = list.filter(function(t) {
                return t.mode === 'template';
            });
            renderTemplateButtons(templates);
        })
        .catch(function(e) {
            console.error('Failed to load templates:', e);
        });
}

function renderTemplateButtons(templates) {
    // 填充模板栏按钮
    var tbar = document.getElementById('template-buttons');
    if (tbar) {
        tbar.innerHTML = '';
        templates.forEach(function(t) {
            var btn = document.createElement('button');
            btn.className = 'template-quick-btn';
            btn.textContent = t.name;
            btn.title = t.description || '';
            btn.onclick = function() { selectTemplate(t.name); };
            tbar.appendChild(btn);
        });
    }
    // 填充快捷入口按钮
    var qarea = document.getElementById('template-quick-actions');
    if (qarea) {
        qarea.innerHTML = templates.map(function(t) {
            return '<button class="quick-action" onclick="selectTemplate(\'' +
                t.name.replace(/'/g, "\\'") + '\')">' + t.name + '</button>';
        }).join('');
    }
}

function selectTemplate(name) {
    currentTemplate = name;
    document.querySelectorAll('.template-quick-btn, .quick-action').forEach(function(b) {
        b.classList.toggle('active', b.textContent === name);
    });

    var stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    var emptyEl = document.getElementById('chat-empty');
    if (emptyEl) emptyEl.style.display = 'none';

    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({type: 'template', template_name: name, extra_question: ''}));
        return;
    }

    chatInProgress = true;
    document.getElementById('chat-send-btn').style.display = 'none';
    document.getElementById('chat-stop-btn').style.display = 'inline-block';

    _openConversationWs(stockCode, function() {
        setTimeout(function() {
            if (chatWs && chatWs.readyState === WebSocket.OPEN) {
                chatWs.send(JSON.stringify({type: 'template', template_name: name, extra_question: ''}));
            }
        }, 200);
    });
}

function appendMeta(text) {
    var msgs = document.getElementById('chat-messages');
    var div = document.createElement('div');
    div.className = 'chat-meta';
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

function appendSectionCard(content, meta) {
    var msgs = document.getElementById('chat-messages');
    var card = document.createElement('div');
    card.className = 'template-section-card';

    var title = (meta && meta.section_title) ? meta.section_title : '';
    var titleHtml = title ? '<div class="section-card-title">▌ ' + escapeHtml(title) + '</div>' : '';

    card.innerHTML = titleHtml + '<div class="section-card-body">' + formatMarkdown(content) + '</div>';
    msgs.appendChild(card);
    msgs.scrollTop = msgs.scrollHeight;
}

function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// ---- Prompt 编辑器 ----

async function openPromptEditor(templateName) {
    const name = templateName || currentTemplateName;
    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name));
        if (!resp.ok) { alert('模板加载失败'); return; }
        const t = await resp.json();

        document.getElementById('pe-name').value = t.name || '';
        document.getElementById('pe-desc').value = t.description || '';
        document.getElementById('pe-mode').value = t.mode || 'deep';
        document.getElementById('pe-role').value = t.system_role || '';
        document.getElementById('pe-harvard').value = (t.frameworks && t.frameworks.harvard) || '';
        document.getElementById('pe-crosscheck').value = (t.frameworks && t.frameworks.crosscheck) || '';
        document.getElementById('pe-lifecycle').value = (t.frameworks && t.frameworks.lifecycle) || '';
        document.getElementById('pe-warnings').value = (t.frameworks && t.frameworks.warnings) || '';
        document.getElementById('pe-output').value = t.output_format || '';

        document.getElementById('prompt-editor-overlay').style.display = 'flex';
        requestAnimationFrame(function() {
            document.getElementById('prompt-editor-overlay').classList.add('modal--visible');
        });
    } catch (e) {
        alert('打开编辑器失败: ' + e.message);
    }
}

function closePromptEditor() {
    const overlay = document.getElementById('prompt-editor-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

async function saveTemplate() {
    const name = document.getElementById('pe-name').value.trim();
    if (!name) { alert('请输入模板名称'); return; }

    const data = {
        name: name,
        description: document.getElementById('pe-desc').value.trim(),
        mode: document.getElementById('pe-mode').value,
        system_role: document.getElementById('pe-role').value,
        frameworks: {
            harvard: document.getElementById('pe-harvard').value,
            crosscheck: document.getElementById('pe-crosscheck').value,
            lifecycle: document.getElementById('pe-lifecycle').value,
            warnings: document.getElementById('pe-warnings').value,
        },
        output_format: document.getElementById('pe-output').value,
    };

    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (resp.ok) {
            currentTemplateName = name;
            currentTemplateData = data;
            closePromptEditor();
            loadTemplateList();
        } else {
            const err = await resp.json();
            alert('保存失败: ' + (err.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

async function exportTemplate() {
    const name = document.getElementById('pe-name').value.trim();
    if (!name) { alert('请先输入模板名称'); return; }
    window.open('/ai/prompts/' + encodeURIComponent(name) + '/export', '_blank');
}

function importTemplate() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async function() {
        const file = input.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        try {
            const resp = await fetch('/ai/prompts/import', { method: 'POST', body: formData });
            if (resp.ok) {
                loadTemplateList();
                alert('模板导入成功');
            } else {
                const err = await resp.json();
                alert('导入失败: ' + (err.error || '未知错误'));
            }
        } catch (e) {
            alert('导入失败: ' + e.message);
        }
    };
    input.click();
}

async function duplicateTemplate() {
    const name = document.getElementById('pe-name').value.trim();
    const newName = prompt('新模板名称:', name + ' - 副本');
    if (!newName) return;
    try {
        const resp = await fetch('/ai/prompts/' + encodeURIComponent(name) + '/duplicate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: newName }),
        });
        if (resp.ok) {
            loadTemplateList();
            alert('模板已复制为: ' + newName);
        }
    } catch (e) {
        alert('复制失败: ' + e.message);
    }
}

// ---- 数据报告查看器 ----

async function openDataViewer() {
    document.getElementById('data-viewer-overlay').style.display = 'flex';
    requestAnimationFrame(function() {
        document.getElementById('data-viewer-overlay').classList.add('modal--visible');
    });

    const body = document.getElementById('data-viewer-body');
    body.innerHTML = '<p style="color:var(--text-muted);">加载中...</p>';

    try {
        const resp = await fetch('/ai/report');
        if (!resp.ok) {
            const err = await resp.json();
            body.innerHTML = '<p style="color:var(--negative);">' + (err.error || '请先获取财务数据') + '</p>';
            return;
        }
        const report = await resp.json();
        currentReportData = report;

        const snap = report.company_snapshot || {};
        const titleEl = document.getElementById('data-viewer-title');
        titleEl.textContent = '财务体检报告 — ' + (snap.name || report.stock_code || '');

        let html = '';

        // 公司快照
        html += '<div class="viewer-section"><h4>公司快照</h4>';
        html += '<div class="kv-row"><span>股价</span><span class="kv-value">' + (snap.price || 'N/A') + '</span></div>';
        html += '<div class="kv-row"><span>PE</span><span class="kv-value">' + (snap.pe || 'N/A') + '</span></div>';
        html += '<div class="kv-row"><span>PB</span><span class="kv-value">' + (snap.pb || 'N/A') + '</span></div>';
        html += '<div class="kv-row"><span>市值(亿)</span><span class="kv-value">' + (snap.market_cap_yi || 'N/A') + '</span></div>';
        html += '</div>';

        // 财务健康
        const health = report.financial_health || {};
        for (const [section, data] of Object.entries(health)) {
            if (section.startsWith('_') || !data || typeof data !== 'object') continue;
            html += '<div class="viewer-section"><h4>' + section + '</h4>';
            for (const [k, v] of Object.entries(data)) {
                html += '<div class="kv-row"><span>' + k + '</span><span class="kv-value">' + (v != null ? v : 'N/A') + '</span></div>';
            }
            html += '</div>';
        }

        // 杜邦
        const dupont = report.dupont_analysis || {};
        if (dupont.three_factor && dupont.three_factor.length > 0) {
            html += '<div class="viewer-section"><h4>杜邦分析</h4>';
            dupont.three_factor.forEach(dp => {
                html += '<div class="kv-row"><span>' + (dp.end_date || '') + '</span><span class="kv-value">ROE=' + dp.roe + '% = ' + dp.net_margin + '% x ' + dp.asset_turnover + ' x ' + dp.equity_multiplier + '</span></div>';
            });
            html += '</div>';
        }

        // 风险模型
        const risk = report.risk_models || {};
        if (Object.keys(risk).length > 0) {
            html += '<div class="viewer-section"><h4>风险模型</h4>';
            for (const [key, val] of Object.entries(risk)) {
                if (val && typeof val === 'object') {
                    html += '<div class="kv-row"><span>' + key + '</span><span class="kv-value">' + JSON.stringify(val).substring(0, 120) + '</span></div>';
                }
            }
            html += '</div>';
        }

        // 现金流
        const cf = report.cashflow_analysis || {};
        if (cf.quadrant && cf.quadrant.length > 0) {
            html += '<div class="viewer-section"><h4>现金流象限</h4>';
            cf.quadrant.forEach(q => {
                html += '<div class="kv-row"><span>' + (q.end_date || '') + '</span><span class="kv-value">' + q.quadrant_type + '</span></div>';
            });
            html += '</div>';
        }

        body.innerHTML = html || '<p style="color:var(--text-muted);">暂无数据</p>';
    } catch (e) {
        body.innerHTML = '<p style="color:var(--negative);">加载失败: ' + e.message + '</p>';
    }
}

function closeDataViewer() {
    const overlay = document.getElementById('data-viewer-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

function exportDataReport() {
    window.open('/ai/report/export', '_blank');
}

// ---- Prompt 预览 ----

async function openPromptPreview() {
    document.getElementById('prompt-preview-overlay').style.display = 'flex';
    requestAnimationFrame(function() {
        document.getElementById('prompt-preview-overlay').classList.add('modal--visible');
    });

    const contentEl = document.getElementById('prompt-preview-content');
    contentEl.textContent = '加载中...';

    if (!currentTemplateData) {
        try {
            const resp = await fetch('/ai/prompts/' + encodeURIComponent(currentTemplateName));
            if (resp.ok) currentTemplateData = await resp.json();
        } catch (e) {}
    }

    if (currentTemplateData) {
        let preview = '【系统角色】\n' + (currentTemplateData.system_role || '(未设置)') + '\n\n';
        preview += '【分析模式】' + (currentTemplateData.mode || 'deep') + '\n\n';
        const fws = currentTemplateData.frameworks || {};
        for (const [key, content] of Object.entries(fws)) {
            if (content) preview += '--- ' + key + ' ---\n' + content + '\n\n';
        }
        preview += '【输出格式】\n' + (currentTemplateData.output_format || '(未设置)');
        contentEl.textContent = preview;
    } else {
        contentEl.textContent = '请先获取数据并选择模板';
    }
}

function closePromptPreview() {
    const overlay = document.getElementById('prompt-preview-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

// ============================================================================
// 分析结果复制按钮
// ============================================================================

function copyResult(btn) {
    var header = btn.closest('.r-section-header, .r-subheading-header, .r-title-header');
    var container = header ? header.parentElement : btn.closest('.result-container, #result-content');
    if (!container) return;
    var text = container.innerText.trim();
    if (!text) return;
    navigator.clipboard.writeText(text).then(function() {
        var orig = btn.textContent;
        btn.textContent = '✓';
        setTimeout(function() { btn.textContent = orig; }, 1500);
    }).catch(function() {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btn.textContent = '✓';
        setTimeout(function() { btn.textContent = '📋'; }, 1500);
    });
}

// ============================================================================
// 数据导出弹窗
// ============================================================================

function openExportModal() {
    var container = document.getElementById('export-categories');
    container.innerHTML = '';

    // 预设数据类型 — 全部可用类别
    var categories = [
        { group: '行情数据', items: [
            { key: 'daily', label: '日线行情' },
            { key: 'weekly', label: '周线行情' },
            { key: 'monthly', label: '月线行情' },
            { key: 'daily_basic', label: '每日指标' },
            { key: 'basic', label: '基本信息' },
            { key: 'stock_basic', label: '股票信息' },
        ]},
        { group: '财务报表', items: [
            { key: 'income', label: '利润表' },
            { key: 'balance', label: '资产负债表' },
            { key: 'cashflow', label: '现金流量表' },
            { key: 'financial', label: '财务指标' },
            { key: 'fina_audit', label: '审计意见' },
            { key: 'fina_mainbz', label: '主营业务构成' },
        ]},
        { group: '市场数据', items: [
            { key: 'moneyflow', label: '资金流向' },
            { key: 'margin', label: '融资融券' },
            { key: 'margin_detail', label: '融资融券明细' },
            { key: 'hk_hold', label: '北向资金' },
            { key: 'block_trade', label: '大宗交易' },
        ]},
        { group: '股东数据', items: [
            { key: 'stk_holdernumber', label: '股东人数' },
            { key: 'top10_holders', label: '前十大股东' },
            { key: 'top10_floatholders', label: '前十大流通股东' },
            { key: 'dividend', label: '分红送股' },
        ]},
    ];

    categories.forEach(function(group) {
        var groupTitle = document.createElement('div');
        groupTitle.style.cssText = 'color:var(--fg-muted);font-size:10px;font-weight:600;margin:8px 0 4px 0;text-transform:uppercase;';
        groupTitle.textContent = group.group;
        container.appendChild(groupTitle);

        group.items.forEach(function(cat) {
            var label = document.createElement('label');
            label.style.cssText = 'display:flex;align-items:center;gap:8px;padding:3px 0 3px 8px;color:var(--text-primary);cursor:pointer;font-size:13px;';
            label.innerHTML = '<input type="checkbox" name="export-cat" value="' + cat.key + '" checked> ' + cat.label;
            container.appendChild(label);
        });
    });

    document.getElementById('export-modal-overlay').style.display = 'flex';
    requestAnimationFrame(function() {
        document.getElementById('export-modal-overlay').classList.add('modal--visible');
    });
}

function closeExportModal() {
    var overlay = document.getElementById('export-modal-overlay');
    overlay.classList.remove('modal--visible');
    overlay.addEventListener('transitionend', function h() {
        overlay.removeEventListener('transitionend', h);
        overlay.style.display = 'none';
    });
}

function doExport() {
    var cats = [];
    document.querySelectorAll('input[name="export-cat"]:checked').forEach(function(cb) {
        cats.push(cb.value);
    });
    var fmt = document.querySelector('input[name="export-fmt"]:checked');
    var format = fmt ? fmt.value : 'xlsx';
    var stockCode = document.querySelector('input[name="stock_code"]')?.value || '';

    var url = '/export/' + format + '?stock_code=' + encodeURIComponent(stockCode);
    if (cats.length > 0) {
        url += '&categories=' + cats.join(',');
    }
    window.open(url, '_blank');
    closeExportModal();
}
