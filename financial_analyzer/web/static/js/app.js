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

// ---- AI 辩论 WebSocket ----
let debateWs = null;

function startDebate() {
    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    const stream = document.getElementById('debate-stream');
    stream.innerHTML = '<p style="color:var(--accent)">正在连接辩论引擎...</p>';

    // 使用轮询方式替代 WebSocket（更简单可靠）
    stream.innerHTML += '<p style="color:var(--fg-muted)">提示：辩论功能需配置 DeepSeek API Key</p>';
    stream.innerHTML += '<p style="color:var(--fg-secondary)">请通过左侧「Token 配置」设置 API Key 后重试</p>';
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
