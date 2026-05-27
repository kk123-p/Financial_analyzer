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
    var activePresetName = null;  // currently loaded preset name
    var elapsedTimer = null;      // interval timer for elapsed time display

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
        '<div class="quant-toast-container" id="quant-toast-container"></div>' +
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

        '<div class="preset-bar" id="preset-bar">' +
        '  <label>策略预设:</label>' +
        '  <select id="preset-select" class="preset-select">' +
        '    <option value="">-- 选择预设 --</option>' +
        '  </select>' +
        '  <button class="preset-btn save" id="btn-preset-save">保存当前</button>' +
        '  <button class="preset-btn delete" id="btn-preset-delete" style="display:none;">删除</button>' +
        '  <span class="preset-status" id="preset-status"></span>' +
        '</div>' +

        '<div id="quant-factor-panel" class="factor-panel">' +
        '  <div class="factor-panel-header" id="btn-toggle-factors">' +
        '    <h3><span class="section-icon">⚙️</span>因子权重配置</h3>' +
        '    <span class="factor-toggle-icon" id="factor-toggle-icon">&#9660;</span>' +
        '  </div>' +
        '  <div class="factor-panel-content" id="factor-panel-content" style="display:none;">' +
        '    <div id="factor-grid" class="factor-grid"></div>' +
        '  </div>' +
        '</div>' +

        '<div id="quant-progress" style="display:none;margin-bottom:16px;">' +
        '  <div class="quant-card">' +
        '    <p id="quant-progress-text" class="quant-status">正在获取数据...</p>' +
        '    <div class="quant-progress-bar-wrapper"><div class="quant-progress-bar-fill" id="quant-progress-bar" style="width:0%;"></div></div>' +
        '    <span class="quant-elapsed" id="quant-elapsed"></span>' +
        '  </div>' +
        '</div>' +

        '<div class="quant-grid">' +
        '  <div class="quant-card" id="card-signals">' +
        '    <h3><span class="section-icon">📊</span>调仓信号</h3>' +
        '    <div id="signals-content"><p class="quant-status">选择选股池，点击「生成信号」</p></div>' +
        '  </div>' +
        '  <div class="quant-card" id="card-overview">' +
        '    <h3><span class="section-icon">📈</span>运行概况</h3>' +
        '    <div id="overview-content"></div>' +
        '  </div>' +
        '</div>' +

        '<div class="backtest-panel" id="backtest-panel">' +
        '  <div class="backtest-header">' +
        '    <h3><span class="section-icon">🧪</span>回测分析</h3>' +
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
        '    <h3><span class="section-icon">💰</span>模拟交易</h3>' +
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

      // Preset buttons
      $('#btn-preset-save').addEventListener('click', savePreset);
      $('#btn-preset-delete').addEventListener('click', deletePreset);
      $('#preset-select').addEventListener('change', function () {
        loadPreset(this.value);
      });

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
            var savedDisabled = loadDisabledFactors();
            renderFactorPanel(factors, savedWeights, savedDisabled);
            populatePresetDropdown();
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

    function loadDisabledFactors() {
      try {
        var saved = localStorage.getItem('quant_disabled_factors');
        return saved ? JSON.parse(saved) : [];
      } catch (e) {
        return [];
      }
    }

    function saveDisabledFactors(disabledList) {
      try {
        localStorage.setItem('quant_disabled_factors', JSON.stringify(disabledList));
      } catch (e) { /* ignore */ }
    }

    function getDisabledFactors() {
      var disabled = [];
      var checkboxes = container.querySelectorAll('.factor-checkbox');
      for (var i = 0; i < checkboxes.length; i++) {
        if (!checkboxes[i].checked) {
          disabled.push(checkboxes[i].dataset.name);
        }
      }
      return disabled;
    }

    // ==================== Presets ====================

    function getPresets() {
      try {
        var saved = localStorage.getItem('quant_strategy_presets');
        return saved ? JSON.parse(saved) : {};
      } catch (e) {
        return {};
      }
    }

    function savePresetsToStorage(presets) {
      try {
        localStorage.setItem('quant_strategy_presets', JSON.stringify(presets));
      } catch (e) { /* ignore */ }
    }

    function populatePresetDropdown() {
      var presets = getPresets();
      var select = $('#preset-select');
      var optionsHtml = '<option value="">-- 选择预设 --</option>';
      Object.keys(presets).sort().forEach(function (name) {
        var selected = (activePresetName === name) ? ' selected' : '';
        optionsHtml += '<option value="' + name + '"' + selected + '>' + name + '</option>';
      });
      select.innerHTML = optionsHtml;
      updatePresetButtons();
    }

    function updatePresetButtons() {
      var hasSelection = !!$('#preset-select').value;
      $('#btn-preset-delete').style.display = hasSelection ? 'inline-block' : 'none';
    }

    function savePreset() {
      var name = prompt('请输入预设名称:');
      if (!name || !name.trim()) return;
      name = name.trim();

      var weights = saveWeights();
      var disabled = getDisabledFactors();
      var presets = getPresets();
      presets[name] = { weights: weights, disabled: disabled, saved_at: new Date().toISOString() };
      savePresetsToStorage(presets);
      activePresetName = name;
      populatePresetDropdown();
      $('#preset-status').textContent = '已保存: ' + name;
      setTimeout(function () { $('#preset-status').textContent = ''; }, 3000);
    }

    function loadPreset(name) {
      if (!name) {
        activePresetName = null;
        updatePresetButtons();
        return;
      }
      var presets = getPresets();
      var preset = presets[name];
      if (!preset) return;

      activePresetName = name;
      var disabled = preset.disabled || [];

      // Update weights in localStorage and slider values
      if (preset.weights) {
        localStorage.setItem('quant_factor_weights', JSON.stringify(preset.weights));
        var sliders = container.querySelectorAll('.factor-slider');
        for (var i = 0; i < sliders.length; i++) {
          var sname = sliders[i].dataset.name;
          if (preset.weights[sname] !== undefined) {
            sliders[i].value = preset.weights[sname];
            var display = container.querySelector('#fv-' + sname);
            if (display) display.textContent = parseFloat(preset.weights[sname]).toFixed(1);
          }
        }
      }

      // Update disabled state in localStorage and checkboxes
      saveDisabledFactors(disabled);
      var checkboxes = container.querySelectorAll('.factor-checkbox');
      for (var j = 0; j < checkboxes.length; j++) {
        var cname = checkboxes[j].dataset.name;
        var isDisabled = disabled.indexOf(cname) !== -1;
        checkboxes[j].checked = !isDisabled;
        var row = checkboxes[j].closest('.factor-row');
        if (row) {
          if (isDisabled) { row.classList.add('disabled'); }
          else { row.classList.remove('disabled'); }
        }
      }

      updateCategorySummaries();
      updatePresetButtons();
      $('#preset-status').textContent = '已加载: ' + name;
      setTimeout(function () { $('#preset-status').textContent = ''; }, 3000);
    }

    function deletePreset() {
      var name = $('#preset-select').value;
      if (!name) return;
      if (!confirm('确定删除预设 "' + name + '"?')) return;

      var presets = getPresets();
      delete presets[name];
      savePresetsToStorage(presets);
      if (activePresetName === name) activePresetName = null;
      populatePresetDropdown();
      $('#preset-status').textContent = '已删除: ' + name;
      setTimeout(function () { $('#preset-status').textContent = ''; }, 3000);
    }

    // ==================== Factor Panel Rendering ====================

    function renderFactorPanel(factorList, savedWeights, savedDisabled) {
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
        var enabled = !savedDisabled || savedDisabled.indexOf(f.name) === -1;
        categories[cat].push({ name: f.name, label: f.label, weight: w, enabled: enabled });
      });

      var html = '';
      Object.keys(categories).forEach(function (cat) {
        var catLabel = categoryLabels[cat] || cat;
        var catFactors = categories[cat];
        var enabledCount = catFactors.filter(function (f) { return f.enabled; }).length;
        var avgWeight = 0;
        if (enabledCount > 0) {
          var sumW = 0;
          catFactors.forEach(function (f) { if (f.enabled) sumW += f.weight; });
          avgWeight = sumW / enabledCount;
        }

        html += '<div class="factor-category" data-cat="' + cat + '">';
        html += '<div class="factor-category-header" data-cat="' + cat + '">';
        html += '  <span class="factor-category-title">' + catLabel + '</span>';
        html += '  <span class="factor-category-summary" id="cat-summary-' + cat + '">';
        html += '    <span class="cat-stat">启用 ' + enabledCount + '/' + catFactors.length + '</span>';
        html += '    <span class="cat-stat">均权 ' + avgWeight.toFixed(1) + '</span>';
        html += '  </span>';
        html += '  <span class="factor-category-chevron" id="cat-chevron-' + cat + '">&#9660;</span>';
        html += '</div>';
        html += '<div class="factor-category-items" id="cat-items-' + cat + '">';
        catFactors.forEach(function (f) {
          var disabledClass = f.enabled ? '' : ' disabled';
          var checkedAttr = f.enabled ? ' checked' : '';
          html +=
            '<div class="factor-row' + disabledClass + '">' +
            '  <input type="checkbox" class="factor-checkbox" data-name="' + f.name + '"' + checkedAttr + '>' +
            '  <span class="factor-label">' + f.label + '</span>' +
            '  <input type="range" class="factor-slider" data-name="' + f.name + '"' +
            '    min="0" max="2" step="0.1" value="' + f.weight + '">' +
            '  <span class="factor-value" id="fv-' + f.name + '">' + f.weight.toFixed(1) + '</span>' +
            '</div>';
        });
        html += '</div></div>';
      });

      $('#factor-grid').innerHTML = html;

      // Bind slider events
      var sliders = container.querySelectorAll('.factor-slider');
      for (var i = 0; i < sliders.length; i++) {
        sliders[i].addEventListener('input', function (e) {
          var name = e.target.dataset.name;
          var val = parseFloat(e.target.value);
          var display = container.querySelector('#fv-' + name);
          if (display) display.textContent = val.toFixed(1);
          saveWeights();
          updateCategorySummaries();
        });
      }

      // Bind checkbox events
      var checkboxes = container.querySelectorAll('.factor-checkbox');
      for (var j = 0; j < checkboxes.length; j++) {
        checkboxes[j].addEventListener('change', function (e) {
          var name = e.target.dataset.name;
          var row = e.target.closest('.factor-row');
          if (row) {
            if (e.target.checked) { row.classList.remove('disabled'); }
            else { row.classList.add('disabled'); }
          }
          saveDisabledFactors(getDisabledFactors());
          updateCategorySummaries();
        });
      }

      // Bind category collapse/expand
      var catHeaders = container.querySelectorAll('.factor-category-header');
      for (var k = 0; k < catHeaders.length; k++) {
        catHeaders[k].addEventListener('click', function (e) {
          var cat = this.dataset.cat;
          var items = container.querySelector('#cat-items-' + cat);
          var chevron = container.querySelector('#cat-chevron-' + cat);
          if (items) {
            if (items.classList.contains('collapsed')) {
              items.classList.remove('collapsed');
              items.style.maxHeight = items.scrollHeight + 'px';
              if (chevron) chevron.innerHTML = '&#9660;';
            } else {
              items.classList.add('collapsed');
              items.style.maxHeight = '0';
              if (chevron) chevron.innerHTML = '&#9654;';
            }
          }
        });
      }
    }

    function updateCategorySummaries() {
      var categories = {};
      var factorList = factors;
      var categoryLabels = {
        value: '价值', quality: '质量', growth: '成长',
        momentum: '动量', sentiment: '情绪', low_vol: '低波', risk: '风险'
      };

      factorList.forEach(function (f) {
        var cat = f.category || 'other';
        if (!categories[cat]) categories[cat] = [];
        var slider = container.querySelector('.factor-slider[data-name="' + f.name + '"]');
        var checkbox = container.querySelector('.factor-checkbox[data-name="' + f.name + '"]');
        var w = slider ? parseFloat(slider.value) : f.weight;
        var enabled = checkbox ? checkbox.checked : true;
        categories[cat].push({ name: f.name, weight: w, enabled: enabled });
      });

      Object.keys(categories).forEach(function (cat) {
        var catFactors = categories[cat];
        var enabledCount = catFactors.filter(function (f) { return f.enabled; }).length;
        var avgWeight = 0;
        if (enabledCount > 0) {
          var sumW = 0;
          catFactors.forEach(function (f) { if (f.enabled) sumW += f.weight; });
          avgWeight = sumW / enabledCount;
        }
        var summaryEl = container.querySelector('#cat-summary-' + cat);
        if (summaryEl) {
          summaryEl.innerHTML =
            '<span class="cat-stat">启用 ' + enabledCount + '/' + catFactors.length + '</span>' +
            '<span class="cat-stat">均权 ' + avgWeight.toFixed(1) + '</span>';
        }
      });
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

    var progressStartTime = 0;

    function showProgress(msg, pct) {
      $('#quant-progress').style.display = 'block';
      $('#quant-progress-text').textContent = msg;
      if (pct !== undefined) {
        $('#quant-progress-bar').style.width = pct + '%';
      }
      // Start elapsed timer
      if (!progressStartTime) {
        progressStartTime = Date.now();
        elapsedTimer = setInterval(function () {
          var sec = Math.floor((Date.now() - progressStartTime) / 1000);
          var el = $('#quant-elapsed');
          if (el) el.textContent = '已用时 ' + sec + ' 秒';
        }, 1000);
      }
    }

    function hideProgress() {
      $('#quant-progress').style.display = 'none';
      $('#quant-progress-bar').style.width = '0%';
      if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
      progressStartTime = 0;
      var el = $('#quant-elapsed');
      if (el) el.textContent = '';
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
      setBtnLoading(btn, true, '计算中...');

      // Remove any existing retry button
      var oldRetry = container.querySelector('.quant-retry');
      if (oldRetry) oldRetry.remove();

      showProgress('正在获取成分股和因子数据（可能需要几分钟）...');

      var controller = new AbortController();
      var timeout = setTimeout(function () { controller.abort(); }, 600000);

      // Build request body with user-adjusted factor weights from localStorage
      var savedWeights = loadWeights();
      var disabledFactors = getDisabledFactors();
      var reqBody = {};
      if (savedWeights) {
        reqBody.factor_weights = savedWeights;
      }
      if (disabledFactors.length > 0) {
        reqBody.disabled_factors = disabledFactors;
        // Set weight=0 for disabled factors so scorer skips them
        if (!reqBody.factor_weights) reqBody.factor_weights = {};
        disabledFactors.forEach(function (name) {
          reqBody.factor_weights[name] = 0;
        });
      }
      if (activePresetName) {
        reqBody.preset_name = activePresetName;
      }

      fetch('/api/v1/quant/run?pool=' + encodeURIComponent(pool) + '&top_n=' + topN, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody),
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
            showToast('信号生成成功', 'success');
          } else {
            clearTimeout(timeout);
            hideProgress();
            showError(data.error || '未知错误', data);
            showToast(data.error || '信号生成失败', 'error');
          }
        })
        .catch(function (err) {
          clearTimeout(timeout);
          hideProgress();
          if (err.name === 'AbortError') {
            showError('请求超时（数据量较大时可能需较长时间）');
            showToast('请求超时，请稍后重试', 'error');
          } else {
            showError(err.message);
            showToast(err.message, 'error');
          }
        })
        .then(function () {
          loading = false;
          setBtnLoading(btn, false, '生成信号');
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
              showProgress(task.message || '处理中... (' + task.progress + '%)', task.progress);
            }
            if (task.status === 'done') {
              clearInterval(pollInterval);
              hideProgress();
              var result = task.result || {};
              lastSignalData = result;
              lastSignalTaskId = taskId;
              renderResults(result);
              showToast('信号生成成功', 'success');
              loading = false;
              setBtnLoading($('#btn-run-signal'), false, '生成信号');
            } else if (task.status === 'error') {
              clearInterval(pollInterval);
              hideProgress();
              showError(task.message || '任务失败');
              showToast(task.message || '任务失败', 'error');
              loading = false;
              setBtnLoading($('#btn-run-signal'), false, '生成信号');
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
      var signals = data.signals || [];
      var signalHTML = '';
      var actionLabels = { buy: '买入', sell: '卖出', hold: '持有' };

      // Copy button
      signalHTML += '<div style="display:flex;justify-content:flex-end;margin-bottom:8px;">' +
        '<button class="quant-copy-btn" id="btn-copy-signals">📋 复制信号</button></div>';

      if (signals.length === 0) {
        signalHTML += '<div class="quant-empty">无调仓信号</div>';
      } else {
        signalHTML += '<ul class="signal-list">';
        signals.forEach(function (s) {
          var label = actionLabels[s.action] || s.action;
          signalHTML +=
            '<li class="signal-item">' +
            '  <span>' +
            '    <span class="signal-code">' + s.code + '</span>' +
            '    <span class="signal-name">' + (s.name || '') + '</span>' +
            '  </span>' +
            '  <span style="display:flex;align-items:center;gap:12px;">' +
            '    <span style="font-family:monospace;font-size:0.85em;color:var(--text-secondary);">' + formatMoney(s.price) + '</span>' +
            '    <span class="signal-action ' + s.action + '">' + label + '</span>' +
            '    <span style="font-size:0.8rem;">' + (s.weight * 100).toFixed(1) + '%</span>' +
            '  </span>' +
            '</li>';
        });
        signalHTML += '</ul>';
      }
      $('#signals-content').innerHTML = signalHTML;

      // Bind copy button
      var copyBtn = $('#btn-copy-signals');
      if (copyBtn) {
        copyBtn.addEventListener('click', function () {
          var lines = signals.map(function (s) {
            return s.code + '\t' + (s.name || '') + '\t' + (actionLabels[s.action] || s.action) + '\t' + (s.weight * 100).toFixed(1) + '%';
          });
          copyToClipboard(lines.join('\n')).then(function () {
            copyBtn.classList.add('copied');
            copyBtn.textContent = '✅ 已复制';
            setTimeout(function () {
              copyBtn.classList.remove('copied');
              copyBtn.textContent = '📋 复制信号';
            }, 2000);
          });
        });
      }

      var buyCount = signals.filter(function (s) { return s.action === 'buy'; }).length;
      var sellCount = signals.filter(function (s) { return s.action === 'sell'; }).length;
      var holdCount = signals.filter(function (s) { return s.action === 'hold'; }).length;

      $('#overview-content').innerHTML =
        '<p class="quant-status success">' +
        '  选股池: ' + data.universe +
        ' | 分析: ' + formatNumber(data.total_stocks_analyzed) + '只' +
        ' | 有效: ' + formatNumber(data.valid_stocks || 0) + '只' +
        ' | 日期: ' + data.date +
        '</p>' +
        '<p class="quant-status" style="margin-top:4px;">' +
        '  买入 <span style="color:#4caf50;">' + buyCount + '</span> 只 | ' +
        '卖出 <span style="color:#f44336;">' + sellCount + '</span> 只 | ' +
        '持有 <span style="color:#64b5f6;">' + holdCount + '</span> 只' +
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
      setBtnLoading(btn, true, '回测中...');
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
            setBtnLoading(btn, false, '运行回测');
            var errMsg = data.error || '回测启动失败';
            showBacktestError(errMsg);
            showToast(errMsg, 'error');
          }
        })
        .catch(function (err) {
          clearTimeout(timeout);
          loading = false;
          setBtnLoading(btn, false, '运行回测');
          if (err.name === 'AbortError') {
            showBacktestError('回测超时，请缩短日期范围后重试');
            showToast('回测超时', 'error');
          } else {
            showBacktestError('请求失败: ' + err.message);
            showToast(err.message, 'error');
          }
        });
    }

    function showBacktestError(msg) {
      $('#backtest-content').innerHTML =
        '<p class="quant-status" style="color:#f44336;margin-bottom:8px;">' + msg + '</p>' +
        '<div class="quant-retry"><button class="quant-btn" id="btn-retry-backtest">重试</button></div>';
      $('#btn-retry-backtest').addEventListener('click', function () { runBacktest(); });
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
              setBtnLoading(btn, false, '运行回测');
              fetch('/api/v1/backtest/result/' + taskId)
                .then(function (r) { return r.json(); })
                .then(function (result) {
                  renderBacktestResults(result);
                  showToast('回测完成', 'success');
                });
            } else if (task.status === 'error') {
              clearInterval(pollInterval);
              loading = false;
              setBtnLoading(btn, false, '运行回测');
              var errMsg = task.message || '回测失败';
              showBacktestError(errMsg);
              showToast(errMsg, 'error');
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
        '  <span>初始资金: ' + formatMoney(data.initial_capital || 5000) + '</span>' +
        '  <span>最终市值: ' + formatMoney(data.final_value || 0) + '</span>' +
        '  <span>' + (data.start_date || '') + ' ~ ' + (data.end_date || '') + '</span>' +
        '</div>';

      var metricsHTML =
        '<div class="backtest-metrics">' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label" data-tooltip="策略在回测期间的总收益百分比">总收益率</span>' +
        '    <span class="backtest-metric-value ' + ((m.total_return || 0) >= 0 ? 'positive' : 'negative') + '">' +
             formatPct(m.total_return) + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label" data-tooltip="将总收益折算为每年的平均收益率">年化收益率</span>' +
        '    <span class="backtest-metric-value ' + ((m.annualized_return || 0) >= 0 ? 'positive' : 'negative') + '">' +
             formatPct(m.annualized_return) + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label" data-tooltip="每承担一单位风险所获得的超额收益，>1为较好，>2为优秀">夏普比率</span>' +
        '    <span class="backtest-metric-value">' +
             (m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(2) : '--') + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label" data-tooltip="从最高点到最低点的最大跌幅，越小越好">最大回撤</span>' +
        '    <span class="backtest-metric-value negative">' +
             formatPct(m.max_drawdown) + '</span>' +
        '  </div>' +
        '  <div class="backtest-metric">' +
        '    <span class="backtest-metric-label" data-tooltip="盈利交易占总交易次数的比例">胜率</span>' +
        '    <span class="backtest-metric-value">' +
             formatPct(m.win_rate) + '</span>' +
        '  </div>' +
        '</div>';

      // 月度收益柱状图
      var monthlyHTML = renderMonthlyBars(m.monthly_returns || [], data.start_date, data.end_date);

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
      if (keys.length === 0) return '<div class="quant-empty">无因子归因数据</div>';
      var html = '<div class="backtest-attribution"><h4>因子归因</h4>';
      html += '<div class="attribution-grid">';
      keys.forEach(function (k) {
        var val = attribution[k];
        var color = val >= 0 ? 'var(--success)' : 'var(--danger)';
        html +=
          '<div class="attribution-item">' +
          '  <span class="attribution-name">' + k + '</span>' +
          '  <span class="attribution-value" style="color:' + color + ';">' + formatPct(val) + '</span>' +
          '</div>';
      });
      html += '</div></div>';
      return html;
    }

    function renderMonthlyBars(monthlyReturns, startDate, endDate) {
      if (!monthlyReturns || monthlyReturns.length === 0) return '';

      // Generate month labels from backtest date range
      // monthlyReturns is a flat list of floats (N-1 returns for N portfolio snapshots)
      var labels = [];
      if (startDate && endDate) {
        var sy = parseInt(startDate.substring(0, 4), 10);
        var sm = parseInt(startDate.substring(4, 6), 10);
        var ey = parseInt(endDate.substring(0, 4), 10);
        var em = parseInt(endDate.substring(4, 6), 10);
        var y = sy, m = sm;
        while (y < ey || (y === ey && m <= em)) {
          labels.push(y + '-' + (m < 10 ? '0' + m : '' + m));
          m++;
          if (m > 12) { m = 1; y++; }
        }
        // First return corresponds to the 2nd month (transition from month 1 to month 2)
        if (labels.length > monthlyReturns.length) {
          labels = labels.slice(labels.length - monthlyReturns.length);
        }
      }
      // Fallback labels if date range didn't produce enough
      while (labels.length < monthlyReturns.length) {
        labels.push('#' + (labels.length + 1));
      }

      var maxAbs = 0;
      monthlyReturns.forEach(function (r) {
        var abs = Math.abs(r);
        if (abs > maxAbs) maxAbs = abs;
      });
      if (maxAbs === 0) maxAbs = 0.1;

      var barsHTML = '<div class="monthly-return-chart">';
      barsHTML += '<div class="monthly-return-title">月度收益率</div>';
      barsHTML += '<div class="monthly-return-bars">';

      monthlyReturns.forEach(function (r, i) {
        var pct = r;
        var isPositive = pct >= 0;
        var barHeight = Math.min(Math.abs(pct) / maxAbs * 100, 100);
        var barBottom = isPositive ? 50 : (50 - barHeight);
        var color = isPositive ? 'var(--success)' : 'var(--danger)';
        var label = labels[i] && labels[i].length > 5 ? labels[i].slice(5) : labels[i];

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
        showToast('请先生成信号', 'warning');
        return;
      }

      var btn = $('#btn-execute-signals');
      setBtnLoading(btn, true, '执行中...');

      fetch('/api/v1/paper/execute?task_id=' + encodeURIComponent(lastSignalTaskId), {
        method: 'POST',
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.error) {
            showToast('执行失败: ' + data.error, 'error');
          } else {
            showToast('信号执行成功', 'success');
            loadPaperPortfolio();
            loadPaperLedger();
          }
        })
        .catch(function (err) {
          showToast('请求失败: ' + err.message, 'error');
        })
        .then(function () {
          setBtnLoading(btn, false, '执行信号');
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
            showToast('模拟交易初始化成功', 'success');
            loadPaperPortfolio();
            loadPaperLedger();
          }
        })
        .catch(function (err) { showToast('初始化失败: ' + err.message, 'error'); });
    }

    function resetPaperTrading() {
      if (!confirm('确定要重置模拟盘？所有持仓和交易记录将被清除。')) return;
      fetch('/api/v1/paper/reset', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'ok') {
            showToast('模拟盘已重置', 'info');
            $('#paper-holdings').innerHTML = '<p class="quant-status">已重置，点击「初始化」重新开始</p>';
            $('#paper-trades').style.display = 'none';
          }
        })
        .catch(function (err) { showToast('重置失败: ' + err.message, 'error'); });
    }

    function renderHoldings(data) {
      var holdings = data.holdings || [];
      var html =
        '<div class="paper-summary">' +
        '  <span>现金: ' + formatMoney(data.cash || 0) + '</span>' +
        '  <span>总市值: ' + formatMoney(data.total_value || 0) + '</span>' +
        '</div>';

      if (holdings.length === 0) {
        html += '<div class="quant-empty">暂无持仓</div>';
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
            '  <td>' + formatNumber(h.shares) + '</td>' +
            '  <td>' + formatMoney(h.avg_cost) + '</td>' +
            '  <td>' + formatMoney(h.last_price) + '</td>' +
            '  <td>' + formatMoney(h.market_value) + '</td>' +
            '  <td class="' + pnlClass + '">' + formatMoney(h.unrealized_pnl) + '</td>' +
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
          '  <td>' + formatNumber(t.shares) + '</td>' +
          '  <td>' + formatMoney(t.price) + '</td>' +
          '  <td>' + formatMoney(t.total_cost) + '</td>' +
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
        '  <span>累计盈亏: <span class="' + pnlClass + '">' + formatMoney(latest.total_pnl) + '</span></span>' +
        '  <span>收益率: <span class="' + pnlClass + '">' + formatPct(latest.return_pct) + '</span></span>' +
        '  <span>已实现盈亏: ' + formatMoney(data.realized_pnl || 0) + '</span>' +
        '</div>';
      $('#paper-holdings').insertAdjacentHTML('afterbegin', pnlHTML);
    }

    // ==================== Utilities ====================

    function formatPct(val) {
      if (val == null) return '--';
      return (val * 100).toFixed(2) + '%';
    }

    function formatMoney(val) {
      if (val == null) return '--';
      return '¥' + Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatNumber(val) {
      if (val == null) return '--';
      return Number(val).toLocaleString('zh-CN');
    }

    // ---- Toast Notifications ----
    function showToast(msg, type) {
      type = type || 'info';
      var container = $('#quant-toast-container');
      if (!container) return;
      var toast = document.createElement('div');
      toast.className = 'quant-toast ' + type;
      var icon = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' }[type] || '';
      toast.innerHTML = '<span>' + icon + ' ' + msg + '</span><span class="quant-toast-close">&times;</span>';
      container.appendChild(toast);
      toast.querySelector('.quant-toast-close').addEventListener('click', function () {
        toast.remove();
      });
      setTimeout(function () { if (toast.parentNode) toast.remove(); }, 5000);
    }

    // ---- Button Spinner Helpers ----
    function setBtnLoading(btn, loading, text) {
      if (loading) {
        btn.disabled = true;
        btn.innerHTML = '<span class="quant-spinner"></span>' + text;
      } else {
        btn.disabled = false;
        btn.textContent = text;
      }
    }

    // ---- Copy to Clipboard ----
    function copyToClipboard(text) {
      if (navigator.clipboard) {
        return navigator.clipboard.writeText(text);
      }
      // Fallback
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      return Promise.resolve();
    }
  }
})();
