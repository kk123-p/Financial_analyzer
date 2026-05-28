/**
 * Analysis charts — Dupont waterfall, valuation gauge, tech panel.
 * Depends on: echarts (global), EchartsUtils (echarts-utils.js)
 */
(function (global) {
  'use strict';

  var CONTAINER_ID = 'chart-container';

  function _clearContainer() {
    var el = document.getElementById(CONTAINER_ID);
    if (el) el.innerHTML = '';
  }

  function _setContainerClass(cls) {
    var el = document.getElementById(CONTAINER_ID);
    if (!el) return;
    el.className = 'chart-container';
    if (cls) el.classList.add(cls);
  }

  function _showMessage(text) {
    var el = document.getElementById(CONTAINER_ID);
    if (!el) return;
    el.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'result-empty';
    div.textContent = text;
    el.appendChild(div);
  }

  function _isEmptyOption(option) {
    return !option || !option.series || option.series.length === 0;
  }

  // ---- 1. Dupont Waterfall ----

  function renderDupontWaterfall(option) {
    _setContainerClass('');
    if (_isEmptyOption(option)) {
      _showMessage('暂无杜邦分析数据');
      return;
    }
    _clearContainer();
    var chart = EchartsUtils.init(CONTAINER_ID);
    if (chart) {
      EchartsUtils.setOption(chart, option);
    } else {
      _showMessage('图表初始化失败');
    }
  }

  // ---- 2. Valuation Dashboard (dual gauge) ----

  function renderValuationDashboard(option) {
    _setContainerClass('chart-container--gauge');
    if (_isEmptyOption(option)) {
      _showMessage('暂无估值数据');
      return;
    }
    _clearContainer();
    var chart = EchartsUtils.init(CONTAINER_ID);
    if (chart) {
      EchartsUtils.setOption(chart, option);
    } else {
      _showMessage('图表初始化失败');
    }
  }

  // ---- 3. Tech Panel (MACD/RSI/KDJ) ----

  function renderTechPanel(option) {
    _setContainerClass('chart-container--tall');
    if (_isEmptyOption(option)) {
      _showMessage('暂无行情数据');
      return;
    }
    _clearContainer();
    var chart = EchartsUtils.init(CONTAINER_ID);
    if (chart) {
      EchartsUtils.setOption(chart, option);
    } else {
      _showMessage('图表初始化失败');
    }
  }

  // ---- 4. Unified loader ----

  var RENDERERS = {
    dupont_waterfall: renderDupontWaterfall,
    valuation_dashboard: renderValuationDashboard,
    tech_panel: renderTechPanel,
  };

  function loadAnalysisChart(chartType) {
    var renderer = RENDERERS[chartType];
    if (!renderer) {
      _showMessage('未知图表类型: ' + chartType);
      return;
    }

    _showMessage('加载中...');

    fetch('/chart/' + chartType)
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (option) {
        renderer(option);
      })
      .catch(function () {
        _showMessage('图表加载失败');
      });
  }

  // ---- Expose global ----

  global.AnalysisCharts = {
    renderDupontWaterfall: renderDupontWaterfall,
    renderValuationDashboard: renderValuationDashboard,
    renderTechPanel: renderTechPanel,
    loadAnalysisChart: loadAnalysisChart,
  };
})(window);
