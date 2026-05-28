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
      InteractionUtils.addZoomControls(CONTAINER_ID, chart);
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
      InteractionUtils.addZoomControls(CONTAINER_ID, chart);
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
      // Enable dataZoom for time-series navigation (candlestick + indicators)
      InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
      InteractionUtils.addZoomControls(CONTAINER_ID, chart);
      // Enable drill-down on candlestick click to show OHLC detail
      InteractionUtils.enableDrillDown(chart, function (params) {
        if (!params) return;
        var esc = InteractionUtils.escapeHtml;
        var name = params.name || '';
        var seriesName = params.seriesName || '';
        var html = '';
        if (params.componentType === 'series' && params.data) {
          var d = params.data;
          if (Array.isArray(d)) {
            var open = d[0], close = d[1], low = d[2], high = d[3];
            var color = close >= open ? '#3FB950' : '#F85149';
            html = '<div style="text-align:center;padding:20px;">' +
              '<div style="font-size:1.1rem;font-weight:600;color:var(--fg-primary);margin-bottom:12px;">' + esc(name) + '</div>' +
              '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 24px;font-size:0.95rem;">' +
              '<div>开盘: <b style="color:' + color + ';">' + (open != null ? esc(open.toFixed(2)) : '--') + '</b></div>' +
              '<div>收盘: <b style="color:' + color + ';">' + (close != null ? esc(close.toFixed(2)) : '--') + '</b></div>' +
              '<div>最低: <b>' + (low != null ? esc(low.toFixed(2)) : '--') + '</b></div>' +
              '<div>最高: <b>' + (high != null ? esc(high.toFixed(2)) : '--') + '</b></div>' +
              '</div></div>';
          } else if (typeof d === 'object' && d.value !== undefined) {
            html = '<div style="text-align:center;padding:20px;">' +
              '<div style="font-size:1.1rem;font-weight:600;color:var(--fg-primary);margin-bottom:8px;">' + esc(name) + '</div>' +
              '<div>' + esc(seriesName) + ': <b>' + esc(d.value) + '</b></div></div>';
          }
        }
        if (html) {
          InteractionUtils.showDrillDownModal(esc(seriesName) + ' — ' + esc(name), html);
        }
      });
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
