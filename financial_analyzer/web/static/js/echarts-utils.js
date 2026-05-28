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
})(window);
