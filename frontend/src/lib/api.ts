const BASE = '/api/v1';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: 'include',
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as any).error || `HTTP ${res.status}`);
  }
  return res.json();
}

import type { FetchResponse, AnalysisResponse, AiChatResponse, SettingsStatus } from '@/types';

export const api = {
  fetchStockData(stockCode: string, source = 'tushare', startDate = '20240101') {
    return request<FetchResponse>(`${BASE}/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ stock_code: stockCode, source, start_date: startDate }),
    });
  },

  runAnalysis(analysisType: string) {
    return request<AnalysisResponse>(`${BASE}/analyze/${analysisType}`);
  },

  aiChat(question: string, stockCode = '') {
    return request<AiChatResponse>(`${BASE}/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, stock_code: stockCode }),
    });
  },

  getSettings() {
    return request<SettingsStatus>(`${BASE}/settings/status`);
  },

  getAnalysisTypes() {
    return request<{ pipeline_stages: any[]; flat_list: any[] }>(`${BASE}/analysis-types`);
  },

  saveTokens(tushareToken: string, deepseekKey: string) {
    return request<{ success: boolean }>(`${BASE}/settings/tokens`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tushare_token: tushareToken, deepseek_key: deepseekKey }),
    });
  },
};
