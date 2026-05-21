import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from '@/components/layout/Sidebar';
import { StatusBar } from '@/components/layout/StatusBar';
import { DashboardPage } from '@/pages/DashboardPage';
import { AnalysisPage } from '@/pages/AnalysisPage';
import { ChartsPage } from '@/pages/ChartsPage';
import { AiResearchPage } from '@/pages/AiResearchPage';
import { DataTablePage } from '@/pages/DataTablePage';
import { useState } from 'react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

const NAV_ITEMS = [
  { path: '/', label: '总览' },
  { path: '/charts/candlestick', label: '图表' },
  { path: '/ai', label: 'AI' },
  { path: '/data', label: '数据' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('/');

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex h-screen bg-[var(--color-bg-primary)]">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            {/* Tab bar for top-level navigation */}
            <div className="flex border-b border-[var(--color-border)] px-2">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.path}
                  href={item.path}
                  onClick={(e) => {
                    e.preventDefault();
                    setActiveTab(item.path);
                    window.history.pushState({}, '', item.path);
                    window.dispatchEvent(new PopStateEvent('popstate'));
                  }}
                  className={`px-4 py-2 text-sm border-b-2 transition-colors -mb-[1px] ${
                    activeTab === item.path || (item.path !== '/' && window.location.pathname.startsWith(item.path))
                      ? 'border-[var(--color-accent)] text-[var(--color-accent)]'
                      : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
                  }`}
                >
                  {item.label}
                </a>
              ))}
            </div>
            <div className="flex-1 overflow-hidden">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/analyze/:type" element={<AnalysisPage />} />
                <Route path="/charts/:chartType" element={<ChartsPage />} />
                <Route path="/ai" element={<AiResearchPage />} />
                <Route path="/data" element={<DataTablePage />} />
              </Routes>
            </div>
            <StatusBar />
          </div>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
