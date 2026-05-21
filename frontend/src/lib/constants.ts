import type { PipelineStage, AnalysisType } from '@/types';

export const PIPELINE_STAGES: PipelineStage[] = [
  {
    stage: "1. 数据概览",
    entry: "market_overview",
    items: [
      { key: "market_overview", label: "行情概览" },
      { key: "price_trend", label: "价格趋势" },
      { key: "technical", label: "技术指标" },
      { key: "combined", label: "量价结合" },
    ],
  },
  {
    stage: "2. 财务体检",
    entry: "ratio_analysis",
    items: [
      { key: "ratio_analysis", label: "财务比率分析" },
      { key: "textbook_ratios", label: "13项核心比率 (Ch5)" },
      { key: "trend_score", label: "趋势评分 (Ch6)" },
      { key: "cashflow_portrait", label: "现金流画像 (Ch8)" },
      { key: "income_statement", label: "利润表" },
      { key: "balance_sheet", label: "资产负债表" },
      { key: "cashflow", label: "现金流量表" },
      { key: "profitability", label: "盈利能力" },
      { key: "operational", label: "营运能力" },
      { key: "solvency", label: "偿债能力" },
      { key: "growth", label: "成长能力" },
    ],
  },
  {
    stage: "3. 深度诊断",
    entry: "dupont",
    items: [
      { key: "dupont", label: "杜邦分析" },
      { key: "dupont_roic", label: "增强杜邦+ROIC (Ch9)" },
      { key: "fcf", label: "自由现金流" },
      { key: "quadrant", label: "现金流象限" },
      { key: "moat", label: "护城河评估" },
      { key: "deep_comprehensive", label: "综合深度报告" },
      { key: "pe_valuation", label: "PE估值分析" },
      { key: "pe_percentile", label: "PE历史分位" },
      { key: "pb_roe", label: "PB-ROE模型" },
      { key: "ev_ebitda", label: "EV/EBITDA" },
    ],
  },
  {
    stage: "4. 风险审查",
    entry: "audit_full",
    items: [
      { key: "audit_full", label: "综合审计报告" },
      { key: "fraud_ml", label: "ML舞弊检测 (Ch12-13)" },
      { key: "audit_asset", label: "资产端信号" },
      { key: "audit_profit", label: "利润端信号" },
      { key: "audit_cashflow", label: "现金流信号" },
      { key: "audit_cross", label: "勾稽关系验证" },
      { key: "risk", label: "风险评估" },
      { key: "zscore", label: "Z-score" },
      { key: "fscore", label: "F-score" },
      { key: "mscore", label: "M-score" },
    ],
  },
  {
    stage: "5. 估值评级",
    entry: "comprehensive",
    items: [
      { key: "comprehensive", label: "综合投资评级" },
      { key: "pe_valuation", label: "PE估值分析" },
      { key: "pe_percentile", label: "PE历史分位" },
      { key: "pb_roe", label: "PB-ROE模型" },
      { key: "ev_ebitda", label: "EV/EBITDA" },
      { key: "shareholder_return", label: "股东回报" },
      { key: "quality", label: "财报质量" },
    ],
  },
];

export const CHART_TYPES = [
  { key: "candlestick", label: "K线图" },
  { key: "ma", label: "均线图" },
  { key: "bar", label: "涨跌柱" },
  { key: "dupont", label: "杜邦瀑布" },
  { key: "fscore", label: "F-score雷达" },
] as const;

export const DATA_SOURCES = ["tushare", "akshare", "sina", "yfinance"] as const;
