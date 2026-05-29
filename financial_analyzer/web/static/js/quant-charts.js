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
    optWeight: 'opt-weight-chart',
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
    var domId = 'paper-chart-pnl';
    var el = document.getElementById(domId);
    if (!el || !snapshots || snapshots.length === 0) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var dates = snapshots.map(function(s) { return formatDate(s.date); });
    var values = snapshots.map(function(s) { return s.total_value; });

    var option = {
      tooltip: {
        trigger: 'axis',
        formatter: function (params) {
          var p = params[0];
          return p.axisValue + '<br/>资产: <b>¥' + p.value.toFixed(2) + '</b>';
        },
      },
      grid: { left: 60, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { color: '#8B949E', fontSize: 10 },
        axisLine: { lineStyle: { color: '#30363D' } },
      },
      yAxis: {
        type: 'value',
        name: '资产 (¥)',
        axisLabel: { color: '#8B949E', fontSize: 10 },
        splitLine: { lineStyle: { color: '#21262D' } },
      },
      series: [{
        type: 'line',
        data: values,
        smooth: 0.3,
        symbol: 'none',
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(63,185,80,0.25)' },
              { offset: 1, color: 'rgba(63,185,80,0.02)' },
            ],
          },
        },
        lineStyle: { width: 2, color: '#3FB950' },
        markLine: { data: [{ yAxis: initialCapital, name: '初始资金', lineStyle: { type: 'dashed', color: '#8B949E' } }] },
      }],
    };

    EchartsUtils.setOption(chart, option);

    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 9. Paper trading allocation pie ----

  function renderPaperAllocationPie(holdings, cash) {
    var domId = 'paper-chart-allocation';
    var el = document.getElementById(domId);
    if (!el) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var data = [{ name: '现金', value: cash, itemStyle: { color: '#3FB950' } }];
    for (var i = 0; i < holdings.length; i++) {
      data.push({
        name: holdings[i].name || holdings[i].code,
        value: holdings[i].market_value,
        itemStyle: { color: EchartsUtils.PALETTE[(i + 1) % EchartsUtils.PALETTE.length] },
      });
    }

    var option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: ¥{c} ({d}%)',
      },
      legend: {
        bottom: 0,
        textStyle: { color: '#8B949E', fontSize: 11 },
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: data,
        label: {
          color: '#E6EDF3',
          fontSize: 11,
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
        },
      }],
    };

    EchartsUtils.setOption(chart, option);

    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 10. IC Timeseries ----

  function renderICTimeseries(timeseries) {
    var domId = 'fa-chart-ic';
    var el = document.getElementById(domId);
    if (!el || !timeseries) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var factors = Object.keys(timeseries);
    if (factors.length === 0) return;

    // Build date axis from first factor
    var dates = (timeseries[factors[0]] || []).map(function(r) { return r.date; });
    var series = [];
    var palette = ['#3FB950', '#F85149', '#64B5F6', '#D29922', '#BC8CFF', '#39D2C0', '#FF7043'];

    for (var i = 0; i < Math.min(factors.length, 8); i++) {
      var fname = factors[i];
      var records = timeseries[fname] || [];
      series.push({
        name: fname,
        type: 'line',
        data: records.map(function(r) { return r.ic !== null ? r.ic : null; }),
        smooth: 0.2,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 1.5, color: palette[i % palette.length] },
        itemStyle: { color: palette[i % palette.length] },
      });
    }

    EchartsUtils.setOption(chart, {
      tooltip: { trigger: 'axis' },
      legend: { data: factors.slice(0, 8), textStyle: { color: '#8B949E', fontSize: 10 }, top: 0, type: 'scroll' },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#8B949E', fontSize: 10 }, axisLine: { lineStyle: { color: '#30363D' } } },
      yAxis: { type: 'value', name: 'IC', axisLabel: { color: '#8B949E', fontSize: 10 }, splitLine: { lineStyle: { color: '#21262D' } } },
      series: series,
    });

    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 11. Correlation Heatmap ----

  function renderCorrelationHeatmap(correlation) {
    var domId = 'fa-chart-corr';
    var el = document.getElementById(domId);
    if (!el || !correlation || !correlation.labels) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var labels = correlation.labels || [];
    var matrix = correlation.matrix || [];
    var n = labels.length;
    if (n === 0) return;

    var data = [];
    for (var i = 0; i < n; i++) {
      for (var j = 0; j < n; j++) {
        var v = matrix[i] && matrix[i][j] != null ? matrix[i][j] : 0;
        data.push([j, i, +v.toFixed(3)]);
      }
    }

    EchartsUtils.setOption(chart, {
      tooltip: {
        formatter: function (params) {
          return labels[params.value[1]] + ' × ' + labels[params.value[0]] + '<br/>相关系数: <b>' + params.value[2] + '</b>';
        },
      },
      grid: { left: 100, right: 40, top: 10, bottom: 80 },
      xAxis: { type: 'category', data: labels, axisLabel: { color: '#8B949E', fontSize: 9, rotate: 45 }, axisLine: { lineStyle: { color: '#30363D' } } },
      yAxis: { type: 'category', data: labels, axisLabel: { color: '#8B949E', fontSize: 9 }, axisLine: { lineStyle: { color: '#30363D' } } },
      visualMap: { min: -1, max: 1, calculable: false, orient: 'vertical', right: 0, top: 'center', inRange: { color: ['#F85149', '#21262D', '#3FB950'] }, textStyle: { color: '#8B949E', fontSize: 10 } },
      series: [{
        type: 'heatmap',
        data: data,
        label: { show: n <= 15, fontSize: 9, color: '#E6EDF3', formatter: function (p) { return p.value[2]; } },
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.4)' } },
      }],
    });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 12. Decay Curve ----

  function renderDecayCurve(decayCurves) {
    var domId = 'fa-chart-decay';
    var el = document.getElementById(domId);
    if (!el || !decayCurves) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var factors = Object.keys(decayCurves);
    if (factors.length === 0) return;

    var horizons = (decayCurves[factors[0]] || {}).horizons || [1, 2, 3, 6, 12];
    var palette = ['#3FB950', '#F85149', '#64B5F6', '#D29922', '#BC8CFF', '#39D2C0', '#FF7043'];
    var series = [];

    for (var i = 0; i < Math.min(factors.length, 6); i++) {
      var fname = factors[i];
      var dc = decayCurves[fname];
      series.push({
        name: fname,
        type: 'line',
        data: dc.mean_ic || [],
        smooth: 0.2,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: palette[i % palette.length] },
        itemStyle: { color: palette[i % palette.length] },
      });
    }

    EchartsUtils.setOption(chart, {
      tooltip: { trigger: 'axis' },
      legend: { data: factors.slice(0, 6), textStyle: { color: '#8B949E', fontSize: 10 }, top: 0 },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: horizons.map(function(h) { return h + '月'; }), name: '持仓周期', nameTextStyle: { color: '#8B949E' }, axisLabel: { color: '#8B949E' }, axisLine: { lineStyle: { color: '#30363D' } } },
      yAxis: { type: 'value', name: '平均 IC', axisLabel: { color: '#8B949E' }, splitLine: { lineStyle: { color: '#21262D' } } },
      series: series,
    });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 13. Composite Score Bar ----

  function renderCompositeScore(composite) {
    var domId = 'fa-chart-composite';
    var el = document.getElementById(domId);
    if (!el || !composite || composite.length === 0) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var labels = composite.map(function(c) { return c.factor; });
    var scores = composite.map(function(c) { return +c.score.toFixed(4); });

    EchartsUtils.setOption(chart, {
      tooltip: {
        trigger: 'axis',
        formatter: function (params) {
          var idx = params[0].dataIndex;
          var c = composite[idx];
          return c.factor + '<br/>评分: <b>' + c.score.toFixed(4) + '</b><br/>IC: ' + c.ic_mean.toFixed(4) + ' | IR: ' + c.ir.toFixed(3);
        },
      },
      grid: { left: 100, right: 20, top: 10, bottom: 30 },
      xAxis: { type: 'value', name: '综合评分', axisLabel: { color: '#8B949E' }, splitLine: { lineStyle: { color: '#21262D' } } },
      yAxis: { type: 'category', data: labels, axisLabel: { color: '#8B949E', fontSize: 10 }, axisLine: { lineStyle: { color: '#30363D' } } },
      series: [{
        type: 'bar',
        data: scores,
        itemStyle: {
          color: function (params) {
            var v = params.value;
            return v >= 0.3 ? '#3FB950' : v >= 0.1 ? '#D29922' : '#F85149';
          },
        },
        label: { show: true, position: 'right', color: '#E6EDF3', fontSize: 10, formatter: function (p) { return p.value.toFixed(3); } },
      }],
    });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 14. Benchmark Comparison ----

  function renderBenchmarkComparison(data) {
    var domId = 'bt-chart-benchmark';
    var el = document.getElementById(domId);
    if (!el) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var snapshots = data.snapshots || [];
    var benchmarkReturns = data.benchmark_returns || [];
    var excessReturns = data.excess_returns || [];
    var capital = data.initial_capital || 5000;

    // Build cumulative returns
    var dates = [];
    var portCum = [0];
    var benchCum = [0];
    var excessCum = [0];

    for (var i = 0; i < snapshots.length; i++) {
      dates.push(formatDate(snapshots[i].date));
    }

    var monthlyReturns = (data.metrics || {}).monthly_returns || [];
    for (var j = 0; j < Math.max(monthlyReturns.length, benchmarkReturns.length); j++) {
      portCum.push((portCum[portCum.length - 1] || 0) + (monthlyReturns[j] || 0));
      benchCum.push((benchCum[benchCum.length - 1] || 0) + (benchmarkReturns[j] || 0));
      excessCum.push((excessCum[excessCum.length - 1] || 0) + (excessReturns[j] || 0));
    }

    // Trim dates to match
    var chartDates = dates.slice(0, Math.min(dates.length, portCum.length));

    EchartsUtils.setOption(chart, {
      tooltip: { trigger: 'axis', formatter: function (params) {
        var s = params[0].axisValue + '<br/>';
        params.forEach(function (p) { s += p.marker + ' ' + p.seriesName + ': <b>' + (p.value * 100).toFixed(2) + '%</b><br/>'; });
        return s;
      }},
      legend: { data: ['组合', '基准', '超额'], textStyle: { color: '#8B949E' }, top: 0 },
      grid: { left: 50, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: chartDates, axisLabel: { color: '#8B949E', fontSize: 10 }, axisLine: { lineStyle: { color: '#30363D' } } },
      yAxis: { type: 'value', name: '累计收益', axisLabel: { color: '#8B949E', formatter: function (v) { return (v * 100).toFixed(0) + '%'; } }, splitLine: { lineStyle: { color: '#21262D' } } },
      series: [
        { name: '组合', type: 'line', data: portCum, smooth: 0.2, symbol: 'none', lineStyle: { width: 2, color: '#3FB950' } },
        { name: '基准', type: 'line', data: benchCum, smooth: 0.2, symbol: 'none', lineStyle: { width: 2, color: '#64B5F6' } },
        { name: '超额', type: 'line', data: excessCum, smooth: 0.2, symbol: 'none', lineStyle: { width: 1.5, color: '#D29922', type: 'dashed' } },
      ],
    });
    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 15. Rolling Sharpe ----

  function renderRollingSharpe(data) {
    var domId = 'bt-chart-rolling-sharpe';
    var el = document.getElementById(domId);
    if (!el) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var rollingSharpe = data.rolling_sharpe || [];
    if (rollingSharpe.length === 0) return;

    // Build date labels
    var snapshots = data.snapshots || [];
    var startIdx = snapshots.length - rollingSharpe.length;
    var dates = [];
    for (var i = startIdx; i < snapshots.length; i++) {
      dates.push(formatDate(snapshots[i] ? snapshots[i].date : ''));
    }

    EchartsUtils.setOption(chart, {
      tooltip: { trigger: 'axis' },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#8B949E', fontSize: 10 }, axisLine: { lineStyle: { color: '#30363D' } } },
      yAxis: { type: 'value', name: 'Sharpe', axisLabel: { color: '#8B949E' }, splitLine: { lineStyle: { color: '#21262D' } } },
      series: [{
        type: 'line',
        data: rollingSharpe,
        smooth: 0.2,
        symbol: 'none',
        lineStyle: { width: 2, color: '#64B5F6' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(100,181,246,0.2)' }, { offset: 1, color: 'rgba(100,181,246,0.02)' }] } },
        markLine: { data: [{ yAxis: 0, lineStyle: { type: 'dashed', color: '#8B949E' } }] },
      }],
    });
    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // ---- 16. Rolling Alpha/Beta ----

  function renderRollingAlphaBeta(data) {
    var domId = 'bt-chart-rolling-alpha';
    var el = document.getElementById(domId);
    if (!el) return;

    var chart = EchartsUtils.init(domId);
    if (!chart) return;

    var rollingAlpha = data.rolling_alpha || [];
    var rollingBeta = data.rolling_beta || [];
    if (rollingAlpha.length === 0 && rollingBeta.length === 0) return;

    var snapshots = data.snapshots || [];
    var maxLen = Math.max(rollingAlpha.length, rollingBeta.length);
    var startIdx = snapshots.length - maxLen;
    var dates = [];
    for (var i = startIdx; i < snapshots.length; i++) {
      dates.push(formatDate(snapshots[i] ? snapshots[i].date : ''));
    }

    EchartsUtils.setOption(chart, {
      tooltip: { trigger: 'axis' },
      legend: { data: ['Alpha (年化)', 'Beta'], textStyle: { color: '#8B949E' }, top: 0 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#8B949E', fontSize: 10 }, axisLine: { lineStyle: { color: '#30363D' } } },
      yAxis: [
        { type: 'value', name: 'Alpha', axisLabel: { color: '#8B949E', formatter: function (v) { return (v * 100).toFixed(0) + '%'; } }, splitLine: { lineStyle: { color: '#21262D' } } },
        { type: 'value', name: 'Beta', position: 'right', axisLabel: { color: '#8B949E' }, splitLine: { show: false } },
      ],
      series: [
        { name: 'Alpha (年化)', type: 'line', data: rollingAlpha, smooth: 0.2, symbol: 'none', lineStyle: { width: 2, color: '#3FB950' } },
        { name: 'Beta', type: 'line', data: rollingBeta, smooth: 0.2, symbol: 'none', yAxisIndex: 1, lineStyle: { width: 2, color: '#BC8CFF' } },
      ],
    });
    InteractionUtils.enableZoom(chart, { start: 0, end: 100 });
    InteractionUtils.addZoomControls(domId, chart);
  }

  // Update CHART_IDS
  CHART_IDS.faIC = 'fa-chart-ic';
  CHART_IDS.faCorr = 'fa-chart-corr';
  CHART_IDS.faDecay = 'fa-chart-decay';
  CHART_IDS.faComposite = 'fa-chart-composite';
  CHART_IDS.btBenchmark = 'bt-chart-benchmark';
  CHART_IDS.btRollingSharpe = 'bt-chart-rolling-sharpe';
  CHART_IDS.btRollingAlpha = 'bt-chart-rolling-alpha';

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
    renderICTimeseries: renderICTimeseries,
    renderCorrelationHeatmap: renderCorrelationHeatmap,
    renderDecayCurve: renderDecayCurve,
    renderCompositeScore: renderCompositeScore,
    renderBenchmarkComparison: renderBenchmarkComparison,
    renderRollingSharpe: renderRollingSharpe,
    renderRollingAlphaBeta: renderRollingAlphaBeta,
  };
})(window);
