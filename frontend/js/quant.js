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
    var lastSignalTaskId = null;

    renderShell();
    bindEvents();

    app.on('view:changed', function (data) {
      if (data.view === 'quant' || (data.detail && data.detail.view === 'quant')) {
        loadPools();
        loadFactors();
        loadPaperPortfolio();
        loadPaperLedger();
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
        '    <div style="display:flex;gap:8px;">' +
        '      <button class="quant-btn" id="btn-init-paper" style="font-size:0.8rem;padding:6px 14px;">初始化</button>' +
        '      <button class="quant-btn" id="btn-reset-paper" style="font-size:0.8rem;padding:6px 14px;background:#f44336;">重置</button>' +
        '      <button class="quant-btn" id="btn-execute-signals" style="display:none;">执行信号</button>' +
        '    </div>' +
        '  </div>' +
        '  <div class="paper-holdings" id="paper-holdings">' +
        '    <p class="quant-status">点击「初始化」开始模拟交易</p>' +
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
      $('#btn-init-paper').addEventListener('click', initPaperTrading);
      $('#btn-reset-paper').addEventListener('click', resetPaperTrading);

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
              lastSignalTaskId = taskId;
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
        '<p class="quant-status">正在启动回测...</p>';

      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 600000);

      fetch('/api/v1/backtest/run?pool=' + encodeURIComponent(pool) +
        '&start_date=' + startDate + '&end_date=' + endDate, {
        method: 'POST',
        signal: controller.signal,
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.task_id) {
            pollBacktestTask(data.task_id, controller.signal);
          } else {
            clearTimeout(timeout);
            loading = false;
            btn.disabled = false;
            btn.textContent = '运行回测';
            $('#backtest-content').innerHTML =
              '<p class="quant-status" style="color:#f44336;">' +
              (data.error || '回测启动失败') + '</p>';
          }
        })
        .catch(function (err) {
          clearTimeout(timeout);
          loading = false;
          btn.disabled = false;
          btn.textContent = '运行回测';
          if (err.name === 'AbortError') {
            $('#backtest-content').innerHTML =
              '<p class="quant-status" style="color:#f44336;">回测超时，请缩短日期范围后重试</p>';
          } else {
            $('#backtest-content').innerHTML =
              '<p class="quant-status" style="color:#f44336;">请求失败: ' + err.message + '</p>';
          }
        });
    }

    function pollBacktestTask(taskId, signal) {
      var btn = $('#btn-run-backtest');
      var pollInterval = setInterval(function () {
        if (signal && signal.aborted) {
          clearInterval(pollInterval);
          return;
        }
        fetch('/api/v1/backtest/status/' + taskId)
          .then(function (r) { return r.json(); })
          .then(function (task) {
            if (task.progress !== undefined) {
              $('#backtest-content').innerHTML =
                '<p class="quant-status">' + (task.message || '回测中...') + ' (' + task.progress + '%)</p>';
            }
            if (task.status === 'done') {
              clearInterval(pollInterval);
              loading = false;
              btn.disabled = false;
              btn.textContent = '运行回测';
              fetch('/api/v1/backtest/result/' + taskId)
                .then(function (r) { return r.json(); })
                .then(function (result) { renderBacktestResults(result); });
            } else if (task.status === 'error') {
              clearInterval(pollInterval);
              loading = false;
              btn.disabled = false;
              btn.textContent = '运行回测';
              $('#backtest-content').innerHTML =
                '<p class="quant-status" style="color:#f44336;">' + (task.message || '回测失败') + '</p>';
            }
          })
          .catch(function () { /* ignore poll errors */ });
      }, 3000);
    }

    function renderBacktestResults(data) {
      var m = data.metrics || {};

      // 资金曲线概览
      var summaryHTML =
        '<div class="backtest-summary">' +
        '  <span>初始资金: &yen;' + (data.initial_capital || 5000).toFixed(2) + '</span>' +
        '  <span>最终市值: &yen;' + (data.final_value || 0).toFixed(2) + '</span>' +
        '  <span>' + (data.start_date || '') + ' ~ ' + (data.end_date || '') + '</span>' +
        '</div>';

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

      // 月度收益柱状图
      var monthlyHTML = renderMonthlyBars(m.monthly_returns || []);

      // 调仓记录表
      var tradesHTML = renderBacktestTrades(data.trades || []);

      // 因子归因
      var attrHTML = renderAttribution(data.attribution || {});

      $('#backtest-content').innerHTML = summaryHTML + metricsHTML + monthlyHTML + tradesHTML + attrHTML;
    }

    function renderBacktestTrades(trades) {
      if (!trades || trades.length === 0) return '';
      var actionLabels = { buy: '买入', sell: '卖出', hold: '持有' };
      var html = '<div class="backtest-trades"><h4>调仓记录</h4>';

      trades.forEach(function (period) {
        html += '<div class="backtest-trade-period">';
        html += '<div class="backtest-trade-date">' + (period.date || '') + '</div>';
        html += '<div class="backtest-trade-signals">';
        (period.signals || []).forEach(function (s) {
          var label = actionLabels[s.action] || s.action;
          html +=
            '<span class="backtest-trade-tag">' +
            '  <span class="signal-code">' + s.code + '</span> ' +
            '  <span class="signal-action ' + s.action + '">' + label + '</span>' +
            '  <span style="font-size:0.75rem;color:var(--text-secondary);">' + (s.weight * 100).toFixed(1) + '%</span>' +
            '</span>';
        });
        html += '</div></div>';
      });

      html += '</div>';
      return html;
    }

    function renderAttribution(attribution) {
      var keys = Object.keys(attribution);
      if (keys.length === 0) return '';
      var html = '<div class="backtest-attribution"><h4>因子归因</h4>';
      html += '<div class="attribution-grid">';
      keys.forEach(function (k) {
        var val = attribution[k];
        var color = val >= 0 ? 'var(--success)' : 'var(--danger)';
        html +=
          '<div class="attribution-item">' +
          '  <span class="attribution-name">' + k + '</span>' +
          '  <span class="attribution-value" style="color:' + color + ';">' + (val * 100).toFixed(2) + '%</span>' +
          '</div>';
      });
      html += '</div></div>';
      return html;
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
      if (!lastSignalTaskId) {
        alert('请先生成信号');
        return;
      }

      var btn = $('#btn-execute-signals');
      btn.disabled = true;
      btn.textContent = '执行中...';

      fetch('/api/v1/paper/execute?task_id=' + encodeURIComponent(lastSignalTaskId), {
        method: 'POST',
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) {
            alert('执行失败: ' + data.error);
          } else {
            loadPaperPortfolio();
            loadPaperLedger();
          }
        })
        .catch(function (err) {
          alert('请求失败: ' + err.message);
        })
        .then(function () {
          btn.disabled = false;
          btn.textContent = '执行信号';
        });
    }

    function loadPaperPortfolio() {
      fetch('/api/v1/paper/portfolio')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          renderHoldings(data);
        })
        .catch(function () {});
    }

    function loadPaperLedger() {
      fetch('/api/v1/paper/ledger')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          renderTradeHistory(data.trades || []);
        })
        .catch(function () {});
    }

    function loadPaperPnl() {
      fetch('/api/v1/paper/pnl')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          renderPnlSummary(data);
        })
        .catch(function () {});
    }

    function initPaperTrading() {
      fetch('/api/v1/paper/init?capital=5000', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'ok') {
            loadPaperPortfolio();
            loadPaperLedger();
          }
        })
        .catch(function (err) { alert('初始化失败: ' + err.message); });
    }

    function resetPaperTrading() {
      if (!confirm('确定要重置模拟盘？所有持仓和交易记录将被清除。')) return;
      fetch('/api/v1/paper/reset', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'ok') {
            $('#paper-holdings').innerHTML = '<p class="quant-status">已重置，点击「初始化」重新开始</p>';
            $('#paper-trades').style.display = 'none';
          }
        })
        .catch(function (err) { alert('重置失败: ' + err.message); });
    }

    function renderHoldings(data) {
      var holdings = data.holdings || [];
      var html =
        '<div class="paper-summary">' +
        '  <span>现金: &yen;' + (data.cash || 0).toFixed(2) + '</span>' +
        '  <span>总市值: &yen;' + (data.total_value || 0).toFixed(2) + '</span>' +
        '</div>';

      if (holdings.length === 0) {
        html += '<p class="quant-status">暂无持仓</p>';
      } else {
        html +=
          '<table class="paper-holdings-table">' +
          '<thead><tr>' +
          '  <th>代码</th><th>名称</th><th>数量</th><th>成本</th><th>现价</th><th>市值</th><th>盈亏</th>' +
          '</tr></thead><tbody>';

        holdings.forEach(function (h) {
          var pnlClass = h.unrealized_pnl >= 0 ? 'positive' : 'negative';
          html +=
            '<tr class="holding-row">' +
            '  <td class="signal-code">' + h.code + '</td>' +
            '  <td>' + (h.name || '--') + '</td>' +
            '  <td>' + h.shares + '</td>' +
            '  <td>&yen;' + h.avg_cost.toFixed(2) + '</td>' +
            '  <td>&yen;' + h.last_price.toFixed(2) + '</td>' +
            '  <td>&yen;' + h.market_value.toFixed(2) + '</td>' +
            '  <td class="' + pnlClass + '">&yen;' + h.unrealized_pnl.toFixed(2) + '</td>' +
            '</tr>';
        });

        html += '</tbody></table>';
      }
      $('#paper-holdings').innerHTML = html;
    }

    function renderTradeHistory(trades) {
      if (!trades || trades.length === 0) {
        $('#paper-trades').style.display = 'none';
        return;
      }

      var tbody = $('#paper-trade-body');
      var html = '';
      var actionLabels = { buy: '买入', sell: '卖出' };

      trades.slice(-20).forEach(function (t) {
        var actionClass = t.action === 'buy' ? 'buy' : 'sell';
        html +=
          '<tr class="trade-row">' +
          '  <td>' + t.date + '</td>' +
          '  <td class="signal-code">' + t.stock_code + '</td>' +
          '  <td>' + (t.stock_name || '--') + '</td>' +
          '  <td><span class="signal-action ' + actionClass + '">' + (actionLabels[t.action] || t.action) + '</span></td>' +
          '  <td>' + t.shares + '</td>' +
          '  <td>&yen;' + t.price.toFixed(2) + '</td>' +
          '  <td>&yen;' + t.total_cost.toFixed(2) + '</td>' +
          '</tr>';
      });

      tbody.innerHTML = html;
      $('#paper-trades').style.display = 'block';
    }

    function renderPnlSummary(data) {
      if (!data || !data.latest) return;
      var latest = data.latest;
      var pnlClass = latest.total_pnl >= 0 ? 'positive' : 'negative';
      var pnlHTML =
        '<div class="paper-pnl-summary">' +
        '  <span>累计盈亏: <span class="' + pnlClass + '">&yen;' + latest.total_pnl.toFixed(2) + '</span></span>' +
        '  <span>收益率: <span class="' + pnlClass + '">' + (latest.return_pct * 100).toFixed(2) + '%</span></span>' +
        '  <span>已实现盈亏: &yen;' + (data.realized_pnl || 0).toFixed(2) + '</span>' +
        '</div>';
      $('#paper-holdings').insertAdjacentHTML('afterbegin', pnlHTML);
    }

    // ==================== Utilities ====================

    function formatPct(val) {
      if (val == null) return '--';
      return (val * 100).toFixed(2) + '%';
    }
  }
})();
