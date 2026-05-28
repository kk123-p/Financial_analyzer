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
    sensitivity: 'sens-chart-heatmap',
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
      var snapIdx = i + 1;
      if (snapIdx >= snapshots.length) continue;
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
      var esc = InteractionUtils.escapeHtml;
      var color = ret >= 0 ? '#3FB950' : '#F85149';
      var html = '<div style="text-align:center;padding:20px;">' +
        '<div style="font-size:2rem;font-weight:700;color:' + color + ';">' + esc(ret) + '%</div>' +
        '<div style="color:var(--text-muted);margin-top:8px;">' + esc(year) + ' ' + esc(month) + ' 月度收益率</div>' +
        '</div>';
      InteractionUtils.showDrillDownModal(esc(year) + ' ' + esc(month) + ' 详情', html);
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

  // ---- 5. Sensitivity heatmap ----

  function renderSensitivityHeatmap(data) {
    var domId = 'sens-chart-heatmap';
    var el = document.getElementById(domId);
    if (!el || !data || !data.grid) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var xRange = data.x_range || [];
    var yRange = data.y_range || [];
    var grid = data.grid || [];
    var fxLabel = (data.factor_x && data.factor_x.label) || 'Factor X';
    var fyLabel = (data.factor_y && data.factor_y.label) || 'Factor Y';
    var bl = data.baseline || {};

    var heatData = [];
    var minVal = Infinity, maxVal = -Infinity;
    for (var yi = 0; yi < grid.length; yi++) {
      for (var xi = 0; xi < grid[yi].length; xi++) {
        var v = grid[yi][xi];
        heatData.push([xi, yi, v]);
        if (v < minVal) minVal = v;
        if (v > maxVal) maxVal = v;
      }
    }

    // Baseline markPoint
    var baselineMarkData = [];
    if (bl.x_weight != null && bl.y_weight != null) {
      var blXi = -1, blYi = -1;
      for (var i = 0; i < xRange.length; i++) {
        if (Math.abs(xRange[i] - bl.x_weight) < 0.001) { blXi = i; break; }
      }
      for (var j = 0; j < yRange.length; j++) {
        if (Math.abs(yRange[j] - bl.y_weight) < 0.001) { blYi = j; break; }
      }
      if (blXi >= 0 && blYi >= 0) {
        baselineMarkData.push({
          name: '基准',
          coord: [blXi, blYi],
          itemStyle: { color: '#D29922', borderColor: '#F0F6FC', borderWidth: 2 },
          symbol: 'diamond',
          symbolSize: 16,
          label: { show: true, formatter: '基准', color: '#F0F6FC', fontSize: 11, position: 'top' },
        });
      }
    }

    var xLabels = xRange.map(function(v) { return v.toFixed(2); });
    var yLabels = yRange.map(function(v) { return v.toFixed(2); });

    if (minVal === maxVal) { minVal -= 1; maxVal += 1; }

    var option = {
      tooltip: {
        formatter: function (params) {
          var xi = params.value[0], yi = params.value[1];
          return fxLabel + ' 权重: <b>' + xLabels[xi] + '</b><br/>' +
            fyLabel + ' 权重: <b>' + yLabels[yi] + '</b><br/>' +
            '指标值: <b>' + params.value[2].toFixed(4) + '</b>';
        },
      },
      grid: { left: 80, right: 40, top: 20, bottom: 60 },
      xAxis: {
        type: 'category',
        data: xLabels,
        name: fxLabel + ' 权重',
        nameLocation: 'center',
        nameGap: 36,
        nameTextStyle: { color: '#8B949E', fontSize: 12 },
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      yAxis: {
        type: 'category',
        data: yLabels,
        name: fyLabel + ' 权重',
        nameLocation: 'center',
        nameGap: 50,
        nameTextStyle: { color: '#8B949E', fontSize: 12 },
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        calculable: false,
        orient: 'vertical',
        right: 0,
        top: 'center',
        inRange: {
          color: ['#F85149', '#21262D', '#3FB950'],
        },
        textStyle: { color: '#8B949E', fontSize: 10 },
      },
      series: [{
        type: 'heatmap',
        data: heatData,
        label: {
          show: true,
          fontSize: 10,
          color: '#E6EDF3',
          formatter: function (params) {
            return params.value[2].toFixed(2);
          },
        },
        emphasis: {
          itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.4)' },
        },
        markPoint: baselineMarkData.length > 0 ? { data: baselineMarkData } : undefined,
      }],
    };

    EchartsUtils.setOption(chart, option);
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 6. Link all backtest charts for cross-highlighting ----

  function linkAllCharts() {
    InteractionUtils.linkCharts([
      CHART_IDS.equity,
      CHART_IDS.drawdown,
    ]);
  }

  // ---- 7. Resize all backtest charts ----

  function resizeAll() {
    for (var key in CHART_IDS) {
      if (CHART_IDS.hasOwnProperty(key)) {
        EchartsUtils.resize(CHART_IDS[key]);
      }
    }
  }

  // ---- 8. Paper trading PnL curve ----

  function renderPaperPnlCurve(snapshots, initialCapital) {
    if (!snapshots.length) return;
    var dom = document.getElementById('paper-chart-pnl');
    if (!dom) return;
    var chart = EchartsUtils.init(dom);
    var dates = snapshots.map(function(s) { return s.date; });
    var values = snapshots.map(function(s) { return s.total_value; });
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates },
      yAxis: { type: 'value', name: '资产 (¥)' },
      series: [{
        type: 'line',
        data: values,
        areaStyle: { opacity: 0.15 },
        lineStyle: { width: 2 },
        markLine: { data: [{ yAxis: initialCapital, name: '初始资金', lineStyle: { type: 'dashed', color: '#8B949E' } }] }
      }]
    });
  }

  // ---- 9. Paper trading allocation pie ----

  function renderPaperAllocationPie(holdings, cash) {
    var dom = document.getElementById('paper-chart-allocation');
    if (!dom) return;
    var chart = EchartsUtils.init(dom);
    var data = [{ name: '现金', value: cash }];
    for (var i = 0; i < holdings.length; i++) {
      data.push({ name: holdings[i].name || holdings[i].code, value: holdings[i].market_value });
    }
    chart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: data,
        label: { show: true, formatter: '{b}\n{d}%' }
      }]
    });
  }

  global.QuantCharts = {
    CHART_IDS: CHART_IDS,
    renderEquityCurve: renderEquityCurve,
    renderDrawdownCurve: renderDrawdownCurve,
    renderMonthlyHeatmap: renderMonthlyHeatmap,
    renderTradeDistribution: renderTradeDistribution,
    renderSensitivityHeatmap: renderSensitivityHeatmap,
    linkAllCharts: linkAllCharts,
    resizeAll: resizeAll,
    renderPaperPnlCurve: renderPaperPnlCurve,
    renderPaperAllocationPie: renderPaperAllocationPie,
  };
})(window);
