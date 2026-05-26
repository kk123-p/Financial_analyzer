// quant.js — 策略面板逻辑 (loaded as regular script, uses global $ and window.__app)
(function () {
  var app = window.__app;
  if (!app) {
    console.warn('[quant] app not ready, retrying...');
    document.addEventListener('DOMContentLoaded', function () { initPanel(); });
    return;
  }
  initPanel();

  function initPanel() {
    var app = window.__app;
    if (!app) return;

    var container = $('#view-quant');
    var loading = false;
    var pools = [];

    renderShell();
    app.on('view:changed', function (data) {
      if (data.view === 'quant' || (data.detail && data.detail.view === 'quant')) {
        loadPools();
      }
    });

    function renderShell() {
      container.innerHTML =
        '<div class="quant-header">' +
        '  <h2>策略面板</h2>' +
        '  <div style="display:flex;gap:12px;align-items:center;">' +
        '    <select id="quant-pool-select" class="quant-select">' +
        '      <option value="沪深300">沪深300</option>' +
        '    </select>' +
        '    <button class="quant-btn" id="btn-run-signal">生成信号</button>' +
        '  </div>' +
        '</div>' +
        '<div id="quant-progress" style="display:none;margin-bottom:16px;">' +
        '  <div class="quant-card">' +
        '    <p id="quant-progress-text" class="quant-status">正在获取数据...</p>' +
        '  </div>' +
        '</div>' +
        '<div class="quant-grid">' +
        '  <div class="quant-card" id="card-signals">' +
        '    <h3>调仓信号</h3>' +
        '    <div id="signals-content"><p class="quant-status">选择选股池，点击「生成信号」</p></div>' +
        '  </div>' +
        '  <div class="quant-card" id="card-overview">' +
        '    <h3>运行概况</h3>' +
        '    <div id="overview-content"></div>' +
        '  </div>' +
        '</div>';

      $('#btn-run-signal').addEventListener('click', runSignal);
    }

    function loadPools() {
      fetch('/api/v1/quant/pools')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.pools && data.pools.length > 0) {
            pools = data.pools;
            var select = $('#quant-pool-select');
            select.innerHTML = data.pools.map(function (p) {
              return '<option value="' + p + '">' + p + '</option>';
            }).join('');
          }
        })
        .catch(function (err) { console.warn('Failed to load pools', err); });
    }

    function showProgress(msg) {
      $('#quant-progress').style.display = 'block';
      $('#quant-progress-text').textContent = msg;
    }

    function hideProgress() {
      $('#quant-progress').style.display = 'none';
    }

    function runSignal() {
      if (loading) return;
      loading = true;

      var pool = $('#quant-pool-select').value;
      var btn = $('#btn-run-signal');
      btn.disabled = true;
      btn.textContent = '计算中...';

      showProgress('正在获取成分股和因子数据（可能需要几分钟）...');

      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 600000);

      fetch('/api/v1/quant/run?pool=' + encodeURIComponent(pool) + '&top_n=30', {
        method: 'POST',
        signal: controller.signal,
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          clearTimeout(timeout);
          hideProgress();
          if (data.success) {
            renderResults(data);
          } else {
            $('#signals-content').innerHTML =
              '<p class="quant-status" style="color:#f44336;">' + (data.error || '未知错误') + '</p>';
            $('#overview-content').innerHTML =
              '<p class="quant-status">分析股票: ' + (data.total_stocks_analyzed || 0) +
              '只 | 有效数据: ' + (data.valid_stocks || 0) + '只</p>';
          }
        })
        .catch(function (err) {
          clearTimeout(timeout);
          hideProgress();
          var msg = err.name === 'AbortError' ? '请求超时（数据量较大时可能需较长时间）' : err.message;
          $('#signals-content').innerHTML =
            '<p class="quant-status" style="color:#f44336;">请求失败: ' + msg + '</p>';
        })
        .then(function () {
          loading = false;
          btn.disabled = false;
          btn.textContent = '生成信号';
        });
    }

    function renderResults(data) {
      var signalHTML = '<ul class="signal-list">';
      var actionLabels = { buy: '买入', sell: '卖出', hold: '持有' };

      (data.signals || []).forEach(function (s) {
        var label = actionLabels[s.action] || s.action;
        signalHTML +=
          '<li class="signal-item">' +
          '  <span>' +
          '    <span class="signal-code">' + s.code + '</span>' +
          '    <span class="signal-name">' + (s.name || '') + '</span>' +
          '  </span>' +
          '  <span style="display:flex;align-items:center;gap:12px;">' +
          '    <span style="font-family:monospace;font-size:0.85em;color:var(--text-secondary);">¥' + (s.price || '--') + '</span>' +
          '    <span class="signal-action ' + s.action + '">' + label + '</span>' +
          '    <span style="font-size:0.8rem;">' + (s.weight * 100).toFixed(1) + '%</span>' +
          '  </span>' +
          '</li>';
      });
      signalHTML += '</ul>';
      if (!data.signals || data.signals.length === 0) {
        signalHTML = '<p class="quant-status">无调仓信号</p>';
      }
      $('#signals-content').innerHTML = signalHTML;

      var buyCount = (data.signals || []).filter(function (s) { return s.action === 'buy'; }).length;
      var sellCount = (data.signals || []).filter(function (s) { return s.action === 'sell'; }).length;
      var holdCount = (data.signals || []).filter(function (s) { return s.action === 'hold'; }).length;

      $('#overview-content').innerHTML =
        '<p class="quant-status success">' +
        '  选股池: ' + data.universe +
        ' | 分析: ' + data.total_stocks_analyzed + '只' +
        ' | 有效: ' + (data.valid_stocks || 0) + '只' +
        ' | 日期: ' + data.date +
        '</p>' +
        '<p class="quant-status" style="margin-top:4px;">' +
        '  买入 ' + buyCount + ' 只 | 卖出 ' + sellCount + ' 只 | 持有 ' + holdCount + ' 只' +
        '</p>';
    }
  }
})();
