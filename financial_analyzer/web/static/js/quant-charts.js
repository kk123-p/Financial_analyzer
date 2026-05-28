/**
 * Quant backtest ECharts rendering functions.
 * Depends on: echarts (global), EchartsUtils (echarts-utils.js)
 */
(function (global) {
  'use strict';

  var CHART_IDS = {
    equity: 'bt-chart-equity',
    drawdown: 'bt-chart-drawdown',
    heatmap: 'bt-chart-heatmap',
    trades: 'bt-chart-trades',
  };

  // ---- 1. Equity curve ----

  function renderEquityCurve(snapshots, initialCapital) {
    var domId = CHART_IDS.equity;
    var el = document.getElementById(domId);
    if (!el || !snapshots || snapshots.length === 0) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var dates = [];
    var navValues = [];
    var capital = initialCapital || 5000;

    for (var i = 0; i < snapshots.length; i++) {
      var s = snapshots[i];
      dates.push(formatDate(s.date));
      navValues.push(+(s.total_value / capital).toFixed(4));
    }

    var option = {
      tooltip: {
        trigger: 'axis',
        formatter: function (params) {
          var p = params[0];
          return p.axisValue + '<br/>净值: <b>' + p.value.toFixed(4) + '</b>';
        },
      },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: '#8B949E',
          fontSize: 10,
          formatter: function (v) { return v.toFixed(2); },
        },
        splitLine: { lineStyle: { color: '#21262D' } },
      },
      series: [{
        type: 'line',
        data: navValues,
        smooth: 0.3,
        symbol: 'none',
        lineStyle: { width: 2, color: '#3FB950' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(63,185,80,0.25)' },
              { offset: 1, color: 'rgba(63,185,80,0.02)' },
            ],
          },
        },
      }],
    };

    EchartsUtils.setOption(chart, option);

    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 2. Drawdown curve ----

  function renderDrawdownCurve(snapshots, initialCapital) {
    var domId = CHART_IDS.drawdown;
    var el = document.getElementById(domId);
    if (!el || !snapshots || snapshots.length === 0) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var dates = [];
    var ddValues = [];
    var capital = initialCapital || 5000;
    var peak = 0;

    for (var i = 0; i < snapshots.length; i++) {
      var nav = snapshots[i].total_value / capital;
      if (nav > peak) peak = nav;
      var dd = peak > 0 ? (nav - peak) / peak : 0;
      dates.push(formatDate(snapshots[i].date));
      ddValues.push(+(dd * 100).toFixed(2));
    }

    var option = {
      tooltip: {
        trigger: 'axis',
        formatter: function (params) {
          var p = params[0];
          return p.axisValue + '<br/>回撤: <b>' + p.value.toFixed(2) + '%</b>';
        },
      },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: '#8B949E',
          fontSize: 10,
          formatter: function (v) { return v.toFixed(1) + '%'; },
        },
        splitLine: { lineStyle: { color: '#21262D' } },
      },
      series: [{
        type: 'line',
        data: ddValues,
        smooth: 0.3,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#F85149' },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(248,81,73,0.35)' },
              { offset: 1, color: 'rgba(248,81,73,0.02)' },
            ],
          },
        },
      }],
    };

    EchartsUtils.setOption(chart, option);

    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 3. Monthly returns heatmap ----

  function renderMonthlyHeatmap(monthlyReturns, snapshots) {
    var domId = CHART_IDS.heatmap;
    var el = document.getElementById(domId);
    if (!el || !monthlyReturns || monthlyReturns.length === 0) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    // Build year-month grid
    var yearMonthMap = {};
    var years = [];
    for (var i = 0; i < monthlyReturns.length; i++) {
      var snapIdx = Math.min(i + 1, snapshots.length - 1);
      var dt = snapshots[snapIdx] ? snapshots[snapIdx].date : '';
      var year = dt.substring(0, 4);
      var month = parseInt(dt.substring(4, 6), 10);
      if (!year || !month) continue;

      if (!yearMonthMap[year]) {
        yearMonthMap[year] = {};
        years.push(year);
      }
      yearMonthMap[year][month] = monthlyReturns[i];
    }

    years.sort();

    var data = [];
    var monthNames = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
    var maxAbs = 0;

    for (var yi = 0; yi < years.length; yi++) {
      for (var m = 1; m <= 12; m++) {
        var val = yearMonthMap[years[yi]][m];
        if (val !== undefined && val !== null) {
          var absVal = Math.abs(val);
          if (absVal > maxAbs) maxAbs = absVal;
          data.push([m - 1, yi, +(val * 100).toFixed(2)]);
        }
      }
    }

    if (maxAbs === 0) maxAbs = 1;

    var option = {
      tooltip: {
        formatter: function (params) {
          return years[params.value[1]] + ' ' + monthNames[params.value[0]] +
            '<br/>收益率: <b>' + params.value[2] + '%</b>';
        },
      },
      grid: { left: 60, right: 20, top: 10, bottom: 40 },
      xAxis: {
        type: 'category',
        data: monthNames,
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      yAxis: {
        type: 'category',
        data: years,
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      visualMap: {
        min: -maxAbs * 100,
        max: maxAbs * 100,
        calculable: false,
        show: false,
        inRange: {
          color: ['#F85149', '#21262D', '#3FB950'],
        },
      },
      series: [{
        type: 'heatmap',
        data: data,
        label: {
          show: true,
          fontSize: 10,
          color: '#E6EDF3',
          formatter: function (params) {
            return params.value[2] + '%';
          },
        },
        emphasis: {
          itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.4)' },
        },
      }],
    };

    EchartsUtils.setOption(chart, option);

    InteractionUtils.enableDrillDown(chart, function (params) {
      if (!params || !params.value) return;
      var monthIdx = params.value[0];
      var yearIdx = params.value[1];
      var ret = params.value[2];
      var year = years[yearIdx];
      var month = monthNames[monthIdx];
      var color = ret >= 0 ? '#3FB950' : '#F85149';
      var html = '<div style="text-align:center;padding:20px;">' +
        '<div style="font-size:2rem;font-weight:700;color:' + color + ';">' + ret + '%</div>' +
        '<div style="color:var(--text-muted);margin-top:8px;">' + year + ' ' + month + ' 月度收益率</div>' +
        '</div>';
      InteractionUtils.showDrillDownModal(year + ' ' + month + ' 详情', html);
    });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 4. Trade action distribution ----

  function renderTradeDistribution(trades) {
    var domId = CHART_IDS.trades;
    var el = document.getElementById(domId);
    if (!el || !trades || trades.length === 0) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var counts = { buy: 0, sell: 0, hold: 0 };
    var weightByDate = [];

    for (var i = 0; i < trades.length; i++) {
      var period = trades[i];
      var buyW = 0, sellW = 0;
      for (var j = 0; j < period.signals.length; j++) {
        var sig = period.signals[j];
        if (sig.action === 'buy') { counts.buy++; buyW += sig.weight; }
        else if (sig.action === 'sell') { counts.sell++; sellW += sig.weight; }
        else { counts.hold++; }
      }
      weightByDate.push({
        date: formatDate(period.date),
        buyWeight: +(buyW * 100).toFixed(1),
        sellWeight: +(sellW * 100).toFixed(1),
      });
    }

    var pieData = [
      { value: counts.buy, name: '买入', itemStyle: { color: '#3FB950' } },
      { value: counts.sell, name: '卖出', itemStyle: { color: '#F85149' } },
      { value: counts.hold, name: '持有', itemStyle: { color: '#64B5F6' } },
    ];

    var option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        bottom: 0,
        textStyle: { color: '#8B949E', fontSize: 11 },
      },
      series: [{
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '45%'],
        data: pieData,
        label: {
          color: '#E6EDF3',
          fontSize: 11,
          formatter: '{b}\n{c} ({d}%)',
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
        },
      }],
    };

    EchartsUtils.setOption(chart, option);

    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- Helper ----

  function formatDate(dt) {
    if (!dt) return '';
    var s = String(dt).replace(/-/g, '');
    if (s.length >= 8) return s.substring(0, 4) + '-' + s.substring(4, 6) + '-' + s.substring(6, 8);
    return s;
  }

  // ---- 5. Link all backtest charts for cross-highlighting ----

  function linkAllCharts() {
    InteractionUtils.linkCharts([
      CHART_IDS.equity,
      CHART_IDS.drawdown,
    ]);
  }

  // ---- Resize all backtest charts ----

  function resizeAll() {
    for (var key in CHART_IDS) {
      if (CHART_IDS.hasOwnProperty(key)) {
        EchartsUtils.resize(CHART_IDS[key]);
      }
    }
  }

  global.QuantCharts = {
    CHART_IDS: CHART_IDS,
    renderEquityCurve: renderEquityCurve,
    renderDrawdownCurve: renderDrawdownCurve,
    renderMonthlyHeatmap: renderMonthlyHeatmap,
    renderTradeDistribution: renderTradeDistribution,
    linkAllCharts: linkAllCharts,
    resizeAll: resizeAll,
  };
})(window);
