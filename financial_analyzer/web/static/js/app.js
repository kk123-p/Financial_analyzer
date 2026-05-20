/**
 * Financial Analyzer Pro — Terminal UI Interactions
 */

// ---- Tab 切换 ----
function switchTab(tabName, btn) {
    document.querySelectorAll('.tabs > .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById('tab-' + tabName);
    if (panel) panel.classList.add('active');

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

// ---- 侧边栏 ----
function toggleSection(header) {
    const arrow = header.querySelector('.arrow');
    const items = header.nextElementSibling;
    const isOpen = arrow.classList.contains('open');

    if (isOpen) {
        arrow.classList.remove('open');
        items.style.display = 'none';
    } else {
        arrow.classList.add('open');
        items.style.display = 'block';
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
let currentChartData = null;

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
    value:   { name: '价值分析师', icon: '💰', color: 'var(--accent)' },
    growth:  { name: '成长分析师', icon: '🚀', color: 'var(--success)' },
    risk:    { name: '风控分析师', icon: '🛡️', color: 'var(--warning)' },
    consensus: { name: '综合共识', icon: '📊', color: '#BC8CFF' },
};

// 轮次显示名
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
    stream.innerHTML = '<p style="color:var(--accent)">正在连接辩论引擎...</p>';
    stream._roleEls = {};     // 每个角色的当前文本段落
    stream._currentRound = '';

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ai/debate`;

    try {
        debateWs = new WebSocket(wsUrl);

        debateWs.onopen = function() {
            stream.innerHTML = '<p style="color:var(--accent)">已连接，正在准备辩论数据...</p>';
            debateWs.send(JSON.stringify({ stock_code: stockCode }));
        };

        debateWs.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'meta') {
                // 轮次切换
                if (msg.content in ROUND_NAMES) {
                    stream._currentRound = msg.content;
                    const roundDiv = document.createElement('div');
                    roundDiv.className = 'debate-round-header';
                    roundDiv.textContent = ROUND_NAMES[msg.content];
                    stream.appendChild(roundDiv);
                    stream.scrollTop = stream.scrollHeight;
                }
                // 分析师开始
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
                    doneEl.style.cssText = 'color:var(--success);margin-top:12px;';
                    doneEl.textContent = '✅ 辩论完成';
                    stream.appendChild(doneEl);
                }
                else if (msg.content.startsWith('error:')) {
                    stream.insertAdjacentHTML('beforeend', `<p style="color:var(--danger);">⚠️ ${msg.content.substring(6)}</p>`);
                }
            }
            else if (msg.type === 'chunk') {
                // 确定角色元素
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
                    // 回退：直接追加
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
                stream.insertAdjacentHTML('beforeend', '<p style="color:var(--success);margin-top:8px;">--- 辩论结束 ---</p>');
                stream.scrollTop = stream.scrollHeight;
            }
            else if (msg.type === 'status') {
                stream.insertAdjacentHTML('beforeend', `<p style="color:var(--fg-muted);">${msg.content}</p>`);
            }
            else if (msg.type === 'error') {
                stream.insertAdjacentHTML('beforeend', `<p style="color:var(--danger);">⚠️ ${msg.content}</p>`);
            }
        };

        debateWs.onerror = function() {
            stream.insertAdjacentHTML('beforeend', '<p style="color:var(--danger);">⚠️ WebSocket 连接失败，请检查网络或API Key配置</p>');
        };

        debateWs.onclose = function() {
            stream._roleEls = {};
            stream._fallbackEl = null;
        };
    } catch (e) {
        stream.innerHTML = `<p style="color:var(--danger);">⚠️ 连接失败: ${e.message}</p>`;
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

// ---- Modal ----
function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'flex';
}
function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
}
// 点击遮罩关闭
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.style.display = 'none';
    }
});

// ---- 键盘快捷键 ----
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        // Ctrl+Enter: 提交获取数据
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
