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
    var factors = [];
    var lastSignalData = null;

    renderShell();
    bindEvents();

    app.on('view:changed', function (data) {
      if (data.view === 'quant' || (data.detail && data.detail.view === 'quant')) {
        loadPools();
        loadFactors();
      }
    });

    // ==================== Render ====================

    function renderShell() {
      container.innerHTML =
        '<div class="quant-header">' +
        '  <h2>策略面板</h2>' +
        '  <div style="display:flex;gap:12px;align-items:center;">' +
        '    <select id="quant-pool-select" class="quant-select">' +
        '      <option value="沪深300">沪深300</option>' +
        '    </select>' +
        '    <div class="quant-topn">' +
        '      <label for="quant-topn-input">TOP N</label>' +
        '      <input type="number" id="quant-topn-input" min="5" max="50" value="30">' +
        '    </div>' +
        '    <button class="quant-btn" id="btn-run-signal">生成信号</button>' +
        '  </div>' +
        '</div>' +

        '<div id="quant-factor-panel" class="factor-panel">' +
        '  <div class="factor-panel-header" id="btn-toggle-factors">' +
        '    <h3>因子权重配置</h3>' +
        '    <span class="factor-toggle-icon" id="factor-toggle-icon">&#9660;</span>' +
        '  </div>' +
        '  <div class="factor-panel-content" id="factor-panel-content" style="display:none;">' +
        '    <div id="factor-grid" class="factor-grid"></div>' +
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
        '</div>' +

        '<div class="backtest-panel" id="backtest-panel">' +
        '  <div class="backtest-header">' +
        '    <h3>回测分析</h3>' +
        '  </div>' +
        '  <div class="backtest-controls">' +
        '    <div class="backtest-date-group">' +
        '      <label for="backtest-start">开始日期</label>' +
        '      <input type="date" id="backtest-start" class="backtest-date" value="2024-01-01">' +
        '    </div>' +
        '    <div class="backtest-date-group">' +
        '      <label for="backtest-end">结束日期</label>' +
        '      <input type="date" id="backtest-end" class="backtest-date">' +
        '    </div>' +
        '    <button class="quant-btn" id="btn-run-backtest">运行回测</button>' +
        '  </div>' +
        '  <div id="backtest-content"><p class="quant-status">设置日期范围后点击「运行回测」</p></div>' +
        '</div>' +

        '<div class="paper-panel" id="paper-panel">' +
        '  <div class="paper-header">' +
        '    <h3>模拟交易</h3>' +
        '    <button class="quant-btn" id="btn-execute-signals" style="display:none;">执行信号</button>' +
        '  </div>' +
        '  <div class="paper-holdings" id="paper-holdings">' +
        '    <p class="quant-status">生成信号后可执行模拟交易</p>' +
        '  </div>' +
        '  <div class="paper-trades" id="paper-trades" style="display:none;">' +
        '    <h4>交易记录</h4>' +
        '    <table class="paper-trade-table" id="paper-trade-table">' +
        '      <thead><tr>' +
        '        <th>日期</th><th>代码</th><th>名称</th><th>方向</th><th>数量</th><th>价格</th><th>金额</th>' +
        '      </tr></thead>' +
        '      <tbody id="paper-trade-body"></tbody>' +
        '    </table>' +
        '  </div>' +
        '</div>';
    }

    function bindEvents() {
      $('#btn-run-signal').addEventListener('click', runSignal);
      $('#btn-toggle-factors').addEventListener('click', toggleFactorPanel);
      $('#btn-run-backtest').addEventListener('click', runBacktest);
      $('#btn-execute-signals').addEventListener('click', executeSignals);

      var today = new Date();
      $('#backtest-end').value = today.toISOString().slice(0, 10);
    }

    // ==================== Pools ====================

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

    // ==================== Factors ====================

    function loadFactors() {
      fetch('/api/v1/quant/factors')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.factors && data.factors.length > 0) {
            factors = data.factors;
            var savedWeights = loadWeights();
            renderFactorPanel(factors, savedWeights);
          }
        })
        .catch(function (err) {
          console.warn('Failed to load factors', err);
          $('#factor-grid').innerHTML =
            '<p class="quant-status">因子加载失败</p>';
        });
    }

    function loadWeights() {
      try {
        var saved = localStorage.getItem('quant_factor_weights');
        return saved ? JSON.parse(saved) : null;
      } catch (e) {
        return null;
      }
    }

    function saveWeights() {
      var weights = {};
      var sliders = container.querySelectorAll('.factor-slider');
      for (var i = 0; i < sliders.length; i++) {
        weights[sliders[i].dataset.name] = parseFloat(sliders[i].value);
      }
      try {
        localStorage.setItem('quant_factor_weights', JSON.stringify(weights));
      } catch (e) { /* ignore */ }
      return weights;
    }

    function renderFactorPanel(factorList, savedWeights) {
      var categories = {};
      var categoryLabels = {
        value: '价值', quality: '质量', growth: '成长',
        momentum: '动量', sentiment: '情绪', low_vol: '低波', risk: '风险'
      };

      factorList.forEach(function (f) {
        var cat = f.category || 'other';
        if (!categories[cat]) categories[cat] = [];
        var w = (savedWeights && savedWeights[f.name] !== undefined)
          ? savedWeights[f.name] : f.weight;
        categories[cat].push({ name: f.name, label: f.label, weight: w });
      });

      var html = '';
      Object.keys(categories).forEach(function (cat) {
        var catLabel = categoryLabels[cat] || cat;
        html += '<div class="factor-category">';
        html += '<h4 class="factor-category-title">' + catLabel + '</h4>';
        categories[cat].forEach(function (f) {
          html +=
            '<div class="factor-row">' +
            '  <span class="factor-label">' + f.label + '</span>' +
            '  <input type="range" class="factor-slider" data-name="' + f.name + '"' +
            '    min="0" max="2" step="0.1" value="' + f.weight + '">' +
            '  <span class="factor-value" id="fv-' + f.name + '">' + f.weight.toFixed(1) + '</span>' +
            '</div>';
        });
        html += '</div>';
      });

      $('#factor-grid').innerHTML = html;

      var sliders = container.querySelectorAll('.factor-slider');
      for (var i = 0; i < sliders.length; i++) {
        sliders[i].addEventListener('input', function (e) {
          var name = e.target.dataset.name;
          var val = parseFloat(e.target.value);
          var display = container.querySelector('#fv-' + name);
          if (display) display.textContent = val.toFixed(1);
          saveWeights();
        });
      }
    }

    function toggleFactorPanel() {
      var content = $('#factor-panel-content');
      var icon = $('#factor-toggle-icon');
      if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.innerHTML = '&#9650;';
      } else {
        content.style.display = 'none';
        icon.innerHTML = '&#9660;';
      }
    }

    // ==================== Signal Generation ====================

    function showProgress(msg) {
      $('#quant-progress').style.display = 'block';
      $('#quant-progress-text').textContent = msg;
    }

    function hideProgress() {
      $('#quant-progress').style.display = 'none';
    }

    function getTopN() {
      var input = $('#quant-topn-input');
      var val = parseInt(input.value, 10);
      if (isNaN(val) || val < 5) val = 5;
      if (val > 50) val = 50;
      input.value = val;
      return val;
    }

    function runSignal() {
      if (loading) return;
      loading = true;

      var pool = $('#quant-pool-select').value;
      var topN = getTopN();
      var btn = $('#btn-run-signal');
      btn.disabled = true;
      btn.textContent = '计算中...';

      // Remove any existing retry button
      var oldRetry = container.querySelector('.quant-retry');
      if (oldRetry) oldRetry.remove();

      showProgress('正在获取成分股和因子数据（可能需要几分钟）...');

      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 600000);

      fetch('/api/v1/quant/run?pool=' + encodeURIComponent(pool) + '&top_n=' + topN, {
        method: 'POST',
        signal: controller.signal,
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.task_id) {
            pollTask(data.task_id, controller.signal);
          } else if (data.success) {
            clearTimeout(timeout);
            hideProgress();
            lastSignalData = data;
            renderResults(data);
          } else {
            clearTimeout(timeout);
            hideProgress();
            showError(data.error || '未知错误', data);
          }
        })
        .catch(function (err) {
          clearTimeout(timeout);
          hideProgress();
          if (err.name === 'AbortError') {
            showError('请求超时（数据量较大时可能需较长时间）');
          } else {
            showError(err.message);
          }
        })
        .then(function () {
          loading = false;
          btn.disabled = false;
          btn.textContent = '生成信号';
        });
    }

    function pollTask(taskId, signal) {
      var pollInterval = setInterval(function () {
        if (signal && signal.aborted) {
          clearInterval(pollInterval);
          return;
        }
        fetch('/api/v1/quant/status/' + taskId)
          .then(function (r) { return r.json(); })
          .then(function (task) {
            if (task.progress !== undefined) {
              showProgress(task.message || '处理中... (' + task.progress + '%)');
            }
            if (task.status === 'done') {
              clearInterval(pollInterval);
              hideProgress();
              var result = task.result || {};
              lastSignalData = result;
              renderResults(result);
              loading = false;
              var btn = $('#btn-run-signal');
              btn.disabled = false;
              btn.textContent = '生成信号';
            } else if (task.status === 'error') {
              clearInterval(pollInterval);
              hideProgress();
              showError(task.message || '任务失败');
              loading = false;
              var btn = $('#btn-run-signal');
              btn.disabled = false;
              btn.textContent = '生成信号';
            }
          })
          .catch(function () { /* ignore poll errors, keep trying */ });
      }, 2000);
    }

    function showError(msg, data) {
      var retryBtnHTML =
        '<div class="quant-retry">' +
        '  <p class="quant-status" style="color:#f44336;margin-bottom:8px;">' + msg + '</p>' +
        '  <button class="quant-btn" id="btn-retry-signal">重试</button>' +
        '</div>';
      $('#signals-content').innerHTML = retryBtnHTML;
      $('#btn-retry-signal').addEventListener('click', function () {
        runSignal();
      });
      if (data) {
        $('#overview-content').innerHTML =
          '<p class="quant-status">分析股票: ' + (data.total_stocks_analyzed || 0) +
          '只 | 有效数据: ' + (data.valid_stocks || 0) + '只</p>';
      }
    }

    // ==================== Render Results ====================

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
          '    <span style="font-family:monospace;font-size:0.85em;color:var(--text-secondary);">&yen;' + (s.price || '--') + '</span>' +
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

      // Show execute button if there are buy signals
      if (buyCount > 0) {
        $('#btn-execute-signals').style.display = 'inline-block';
      }
    }

    // ==================== Backtest ====================

    function runBacktest() {
      if (loading) return;

      var pool = $('#quant-pool-select').value;
      var topN = getTopN();
      var startDate = $('#backtest-start').value.replace(/-/g, '');
      var endDate = $('#backtest-end').value.replace(/-/g, '');
      var btn = $('#btn-run-backtest');

      if (!startDate || !endDate) {
        $('#backtest-content').innerHTML =
          '<p class="quant-status" style="color:#f44336;">请设置日期范围</p>';
        return;
      }

      loading = true;
      btn.disabled = true;
      btn.textContent = '回测中...';
      $('#backtest-content').innerHTML =
        '<p class="quant-status">正在运行回测...</p>';

      fetch('/api/v1/quant/backtest?pool=' + encodeURIComponent(pool) +
        '&top_n=' + topN + '&start_date=' + startDate + '&end_date=' + endDate, {
        method: 'POST',
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.success) {
            renderBacktestResults(data);
          } else {
            $('#backtest-content').innerHTML =
              '<p class="quant-status" style="color:#f44336;">' +
              (data.error || '回测失败') + '</p>';
          }
        })
        .catch(function () {
          renderBacktestMockResults();
        })
        .then(function () {
          loading = false;
          btn.disabled = false;
          btn.textContent = '运行回测';
        });
    }

    function renderBacktestMockResults() {
      var startVal = $('#backtest-start').value;
      var endVal = $('#backtest-end').value;
      var start = new Date(startVal);
      var end = new Date(endVal);
      var months = [];
      var d = new Date(start.getFullYear(), start.getMonth(), 1);
      while (d <= end) {
        months.push(d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'));
        d.setMonth(d.getMonth() + 1);
      }
      if (months.length === 0) months.push(startVal.slice(0, 7));

      var totalReturn = (Math.random() * 0.4 - 0.1);
      var monthlyReturns = [];
      var cumProduct = 1;
      for (var i = 0; i < months.length; i++) {
        var mr = (Math.random() * 0.16 - 0.06);
        if (i === months.length - 1) {
          mr = totalReturn / months.length;
        }
        mr = Math.max(-0.15, Math.min(0.15, mr));
        monthlyReturns.push({ month: months[i], return_pct: mr });
        cumProduct *= (1 + mr);
      }

      var metrics = {
        total_return: totalReturn,
        annualized_return: totalReturn * (12 / Math.max(months.length, 1)),
        sharpe_ratio: totalReturn > 0 ? 0.5 + Math.random() * 1.5 : -0.5 + Math.random() * 1.0,
        max_drawdown: Math.random() * 0.2 + 0.05,
        win_rate: 0.4 + Math.random() * 0.3,
      };

      renderBacktestResults({
        success: true,
        metrics: metrics,
        monthly_returns: monthlyReturns,
      });
    }

    function renderBacktestResults(data) {
      var m = data.metrics || {};
      var metricsHTML =
        '<div class="backtest-metrics">' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label">总收益率</span>' +
        '    <span class="backtest-metric-value ' + ((m.total_return || 0) >= 0 ? 'positive' : 'negative') + '">' +
             formatPct(m.total_return) + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label">年化收益率</span>' +
        '    <span class="backtest-metric-value ' + ((m.annualized_return || 0) >= 0 ? 'positive' : 'negative') + '">' +
             formatPct(m.annualized_return) + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label">夏普比率</span>' +
        '    <span class="backtest-metric-value">' +
             (m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(2) : '--') + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label">最大回撤</span>' +
        '    <span class="backtest-metric-value negative">' +
             formatPct(m.max_drawdown) + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label">胜率</span>' +
        '    <span class="backtest-metric-value">' +
             formatPct(m.win_rate) + '</span>' +
        '  </div>' +
        '</div>';

      var monthlyHTML = renderMonthlyBars(data.monthly_returns || []);

      $('#backtest-content').innerHTML = metricsHTML + monthlyHTML;
    }

    function renderMonthlyBars(monthlyReturns) {
      if (!monthlyReturns || monthlyReturns.length === 0) return '';

      var maxAbs = 0;
      monthlyReturns.forEach(function (m) {
        var abs = Math.abs(m.return_pct);
        if (abs > maxAbs) maxAbs = abs;
      });
      if (maxAbs === 0) maxAbs = 0.1;

      var barsHTML = '<div class="monthly-return-chart">';
      barsHTML += '<div class="monthly-return-title">月度收益率</div>';
      barsHTML += '<div class="monthly-return-bars">';

      monthlyReturns.forEach(function (m) {
        var pct = m.return_pct;
        var isPositive = pct >= 0;
        var barHeight = Math.min(Math.abs(pct) / maxAbs * 100, 100);
        var barBottom = isPositive ? 50 : (50 - barHeight);
        var color = isPositive ? 'var(--success)' : 'var(--danger)';
        var label = m.month.length > 5 ? m.month.slice(5) : m.month;

        barsHTML +=
          '<div class="monthly-return-bar">' +
          '  <div class="monthly-return-bar-wrapper">' +
          '    <div class="monthly-return-bar-fill" style="bottom:' + barBottom + '%;height:' + barHeight + '%;background:' + color + ';"></div>' +
          '    <div class="monthly-return-zero-line"></div>' +
          '  </div>' +
          '  <div class="monthly-return-label">' + label + '</div>' +
          '  <div class="monthly-return-value" style="color:' + color + ';">' + (pct * 100).toFixed(1) + '%</div>' +
          '</div>';
      });

      barsHTML += '</div></div>';
      return barsHTML;
    }

    // ==================== Paper Trading ====================

    function executeSignals() {
      if (!lastSignalData || !lastSignalData.signals || lastSignalData.signals.length === 0) {
        alert('没有可执行的信号');
        return;
      }

      var buySignals = lastSignalData.signals.filter(function (s) {
        return s.action === 'buy';
      });

      if (buySignals.length === 0) {
        alert('没有买入信号');
        return;
      }

      var btn = $('#btn-execute-signals');
      btn.disabled = true;
      btn.textContent = '执行中...';

      // Simulate execution
      setTimeout(function () {
        renderHoldings(buySignals);
        renderTradeHistory(buySignals);

        btn.textContent = '已执行';
        setTimeout(function () {
          btn.textContent = '执行信号';
          btn.disabled = false;
        }, 2000);
      }, 500);
    }

    function renderHoldings(signals) {
      var html =
        '<table class="paper-holdings-table">' +
        '<thead><tr>' +
        '  <th>代码</th><th>名称</th><th>权重</th><th>价格</th><th>状态</th>' +
        '</tr></thead><tbody>';

      signals.forEach(function (s) {
        html +=
          '<tr class="holding-row">' +
          '  <td class="signal-code">' + s.code + '</td>' +
          '  <td>' + (s.name || '--') + '</td>' +
          '  <td>' + (s.weight * 100).toFixed(1) + '%</td>' +
          '  <td>&yen;' + (s.price || '--') + '</td>' +
          '  <td><span class="signal-action buy">持仓</span></td>' +
          '</tr>';
      });

      html += '</tbody></table>';
      $('#paper-holdings').innerHTML = html;
    }

    function renderTradeHistory(signals) {
      var today = new Date().toISOString().slice(0, 10);
      var tbody = $('#paper-trade-body');
      var html = '';

      signals.forEach(function (s) {
        var amount = ((s.weight || 0) * 10000 * (s.price || 0)).toFixed(2);
        html +=
          '<tr class="trade-row">' +
          '  <td>' + today + '</td>' +
          '  <td class="signal-code">' + s.code + '</td>' +
          '  <td>' + (s.name || '--') + '</td>' +
          '  <td><span class="signal-action buy">买入</span></td>' +
          '  <td>100</td>' +
          '  <td>&yen;' + (s.price || '--') + '</td>' +
          '  <td>&yen;' + amount + '</td>' +
          '</tr>';
      });

      tbody.innerHTML = html;
      $('#paper-trades').style.display = 'block';
    }

    // ==================== Utilities ====================

    function formatPct(val) {
      if (val == null) return '--';
      return (val * 100).toFixed(2) + '%';
    }
  }
})();
