/**
 * ECharts utility helpers — dark theme, lifecycle management.
 */
(function (global) {
  'use strict';

  var DARK_THEME = {
    backgroundColor: 'transparent',
    textStyle: { color: '#8B949E' },
    title: { textStyle: { color: '#E6EDF3' } },
    legend: { textStyle: { color: '#8B949E' } },
    tooltip: {
      backgroundColor: 'rgba(13,17,23,0.92)',
      borderColor: '#30363D',
      textStyle: { color: '#E6EDF3', fontSize: 12 },
    },
    xAxis: {
      axisLine: { lineStyle: { color: '#30363D' } },
      splitLine: { lineStyle: { color: '#21262D' } },
      axisLabel: { color: '#8B949E' },
    },
    yAxis: {
      axisLine: { lineStyle: { color: '#30363D' } },
      splitLine: { lineStyle: { color: '#21262D' } },
      axisLabel: { color: '#8B949E' },
    },
  };

  var PALETTE = [
    '#3FB950', '#F85149', '#39D2C0', '#D29922',
    '#BC8CFF', '#F0F6FC', '#64B5F6', '#FF7043',
  ];

  var _instances = {};

  function init(domId) {
    var el = document.getElementById(domId);
    if (!el) return null;

    if (_instances[domId]) {
      _instances[domId].dispose();
    }

    var chart = echarts.init(el, null, { renderer: 'canvas' });
    _instances[domId] = chart;
    return chart;
  }

  function setOption(chart, option) {
    if (!chart) return;
    chart.setOption(option, true);
  }

  function resize(domId) {
    var chart = _instances[domId];
    if (chart && !chart.isDisposed()) {
      chart.resize();
    }
  }

  function dispose(domId) {
    var chart = _instances[domId];
    if (chart) {
      chart.dispose();
      delete _instances[domId];
    }
  }

  function disposeAll() {
    for (var id in _instances) {
      if (_instances.hasOwnProperty(id)) {
        _instances[id].dispose();
      }
    }
    _instances = {};
  }

  window.addEventListener('resize', function () {
    for (var id in _instances) {
      if (_instances.hasOwnProperty(id) && !_instances[id].isDisposed()) {
        _instances[id].resize();
      }
    }
  });

  global.EchartsUtils = {
    DARK_THEME: DARK_THEME,
    PALETTE: PALETTE,
    init: init,
    setOption: setOption,
    resize: resize,
    dispose: dispose,
    disposeAll: disposeAll,
  };

  // ============================================================
  // InteractionUtils — zoom, drill-down, cross-highlight, export
  // ============================================================

  var InteractionUtils = (function () {

    // ---- 1. Enable dataZoom (slider + inside scroll/drag) ----

    function enableZoom(chart, opts) {
      if (!chart) return;
      var o = opts || {};
      var current = chart.getOption();
      var xAxis = (current.xAxis && current.xAxis[0]) || {};
      var dataLen = (xAxis.data && xAxis.data.length) || 0;
      if (dataLen <= 10) return;

      var startPct = o.start != null ? o.start : Math.max(0, 100 - Math.min(100, (60 / dataLen) * 100));
      var endPct = o.end != null ? o.end : 100;

      chart.setOption({
        dataZoom: [
          {
            type: 'slider',
            xAxisIndex: o.xAxisIndex || 0,
            start: startPct,
            end: endPct,
            height: 20,
            bottom: 8,
            borderColor: '#30363D',
            backgroundColor: 'rgba(22,27,34,0.6)',
            fillerColor: 'rgba(63,185,80,0.15)',
            handleStyle: { color: '#3FB950', borderColor: '#3FB950' },
            textStyle: { color: '#8B949E', fontSize: 10 },
            dataBackground: {
              lineStyle: { color: '#30363D' },
              areaStyle: { color: 'rgba(63,185,80,0.08)' },
            },
          },
          {
            type: 'inside',
            xAxisIndex: o.xAxisIndex || 0,
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
          },
        ],
      });
    }

    // ---- 2. Drill-down modal ----

    function showDrillDownModal(title, bodyHtml) {
      var overlay = document.getElementById('drilldown-overlay');
      var titleEl = document.getElementById('drilldown-title');
      var bodyEl = document.getElementById('drilldown-body');
      if (!overlay) return;
      if (titleEl) titleEl.textContent = title;
      if (bodyEl) bodyEl.innerHTML = bodyHtml;
      overlay.style.display = 'flex';
    }

    function closeDrillDownModal() {
      var overlay = document.getElementById('drilldown-overlay');
      if (overlay) overlay.style.display = 'none';
    }

    function enableDrillDown(chart, callback) {
      if (!chart || !callback) return;
      chart.on('click', function (params) {
        callback(params);
      });
    }

    // Close on overlay background click
    document.addEventListener('click', function (e) {
      if (e.target && e.target.id === 'drilldown-overlay') {
        closeDrillDownModal();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeDrillDownModal();
    });

    // ---- 3. Zoom controls (buttons injected into container) ----

    function addZoomControls(containerId, chart) {
      if (!chart) return;
      var el = document.getElementById(containerId);
      if (!el) return;
      if (el.querySelector('.chart-zoom-controls')) return;

      var wrapper = document.createElement('div');
      wrapper.className = 'chart-zoom-controls';

      var btnZoomIn = _createZoomBtn('+', '放大', function () {
        var opt = chart.getOption();
        var dz = (opt.dataZoom && opt.dataZoom[0]) || {};
        var s = dz.start || 0;
        var e = dz.end || 100;
        var range = e - s;
        var step = range * 0.2;
        _applyZoom(chart, Math.max(0, s + step), Math.min(100, e - step));
      });

      var btnZoomOut = _createZoomBtn('-', '缩小', function () {
        var opt = chart.getOption();
        var dz = (opt.dataZoom && opt.dataZoom[0]) || {};
        var s = dz.start || 0;
        var e = dz.end || 100;
        var range = e - s;
        var step = range * 0.25;
        _applyZoom(chart, Math.max(0, s - step), Math.min(100, e + step));
      });

      var btnReset = _createZoomBtn('R', '重置', function () {
        _applyZoom(chart, 0, 100);
      });

      var btnExport = _createZoomBtn('S', '保存图片', function () {
        exportChart(chart);
      });

      wrapper.appendChild(btnZoomIn);
      wrapper.appendChild(btnZoomOut);
      wrapper.appendChild(btnReset);
      wrapper.appendChild(btnExport);
      el.style.position = el.style.position || 'relative';
      el.appendChild(wrapper);
    }

    function _createZoomBtn(symbol, title, onClick) {
      var btn = document.createElement('button');
      btn.className = 'chart-zoom-btn';
      btn.textContent = symbol;
      btn.title = title;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        onClick();
      });
      return btn;
    }

    function _applyZoom(chart, start, end) {
      chart.setOption({
        dataZoom: [{ start: start, end: end }],
      });
    }

    // ---- 4. Cross-chart axis highlighting (linked tooltips) ----

    var _linkedCharts = [];
    var _linkHandlerAttached = false;

    function linkCharts(chartIdArray) {
      if (!chartIdArray || chartIdArray.length < 2) return;
      _linkedCharts = chartIdArray;

      if (!_linkHandlerAttached) {
        _linkHandlerAttached = true;
        document.addEventListener('mousemove', function (e) {
          // throttled via chart group dispatch
        });
      }

      // Use ECharts group for axisPointer linking
      for (var i = 0; i < chartIdArray.length; i++) {
        var c = _instances[chartIdArray[i]];
        if (c && !c.isDisposed()) {
          c.group = 'linked_group';
          c.connect('linked_group');
        }
      }
    }

    // ---- 5. Export chart as PNG ----

    function exportChart(chart) {
      if (!chart || chart.isDisposed()) return;
      var url = chart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#0D1117',
      });
      var a = document.createElement('a');
      a.href = url;
      a.download = 'chart_' + Date.now() + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }

    // ---- Public API ----

    return {
      enableZoom: enableZoom,
      showDrillDownModal: showDrillDownModal,
      closeDrillDownModal: closeDrillDownModal,
      enableDrillDown: enableDrillDown,
      addZoomControls: addZoomControls,
      linkCharts: linkCharts,
      exportChart: exportChart,
    };
  })();

  global.InteractionUtils = InteractionUtils;
})(window);
