// KPI 数据
export interface KpiData {
  stock_name: string;
  stock_code: string;
  price: number | null;
  change_pct: number | null;
  volume: string;
  pe: number | null;
  pb: number | null;
  market_cap: string;
}

// API 响应
export interface FetchResponse {
  success: boolean;
  error?: string;
  stock_code?: string;
  kpis?: KpiData;
  data_types?: string[];
  financial_ready?: boolean;
}

export interface AnalysisResponse {
  success: boolean;
  error?: string;
  analysis_type?: string;
  result_text?: string;
  result_html?: string;
}

export interface AiChatResponse {
  success: boolean;
  error?: string;
  content?: string;
}

export interface SettingsStatus {
  sources: string[];
  active_source: string;
  has_tushare: boolean;
  has_deepseek: boolean;
}

export interface AnalysisType {
  key: string;
  label: string;
}

export interface PipelineStage {
  stage: string;
  entry: string;
  items: AnalysisType[];
}

// WebSocket 辩论
export interface WsMetaMessage {
  type: "meta";
  content: string;
  info?: string;
}

export interface WsChunkMessage {
  type: "chunk";
  role: "value" | "growth" | "risk" | "consensus";
  content: string;
  done: boolean;
}

export interface WsDoneMessage {
  type: "done";
  content: string;
}

export interface WsErrorMessage {
  type: "error";
  content: string;
}

export type WsMessage = WsMetaMessage | WsChunkMessage | WsDoneMessage | WsErrorMessage;

// 应用状态
export interface AppState {
  stockCode: string;
  activeAnalysis: string | null;
  activeChart: string;
  dataSource: string;
  sidebarCollapsed: boolean;
}
