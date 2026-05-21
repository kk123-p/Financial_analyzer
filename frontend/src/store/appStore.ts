import { create } from 'zustand';

interface AppStore {
  stockCode: string;
  stockName: string;
  activeAnalysis: string | null;
  activeChart: string;
  dataSource: string;
  sidebarCollapsed: boolean;
  dataLoaded: boolean;
  setStock: (code: string, name?: string) => void;
  setActiveAnalysis: (type: string | null) => void;
  setActiveChart: (chart: string) => void;
  setDataSource: (source: string) => void;
  toggleSidebar: () => void;
  setDataLoaded: (loaded: boolean) => void;
}

export const useAppStore = create<AppStore>((set) => ({
  stockCode: '',
  stockName: '',
  activeAnalysis: null,
  activeChart: 'candlestick',
  dataSource: 'tushare',
  sidebarCollapsed: false,
  dataLoaded: false,
  setStock: (code, name) => set({ stockCode: code, stockName: name || '', dataLoaded: false }),
  setActiveAnalysis: (type) => set({ activeAnalysis: type }),
  setActiveChart: (chart) => set({ activeChart: chart }),
  setDataSource: (source) => set({ dataSource: source }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setDataLoaded: (loaded) => set({ dataLoaded: loaded }),
}));

interface DebateStore {
  isConnected: boolean;
  messages: { role: string; content: string }[];
  addMessage: (role: string, content: string) => void;
  clearMessages: () => void;
  setConnected: (connected: boolean) => void;
}

export const useDebateStore = create<DebateStore>((set) => ({
  isConnected: false,
  messages: [],
  addMessage: (role, content) => set((s) => ({ messages: [...s.messages, { role, content }] })),
  clearMessages: () => set({ messages: [] }),
  setConnected: (connected) => set({ isConnected: connected }),
}));
