import { useState, lazy, Suspense } from 'react';
import { useParams } from 'react-router-dom';
import { useAppStore } from '@/store/appStore';
import { CHART_TYPES } from '@/lib/constants';

const Plot = lazy(() => import('react-plotly.js'));

export function ChartsPage() {
  const { chartType } = useParams<{ chartType: string }>();
  const { dataLoaded, stockCode } = useAppStore();
  const [activeType, setActiveType] = useState(chartType || 'candlestick');
  const [figure, setFigure] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchChart = async (type: string) => {
    setActiveType(type);
    if (type === 'dupont' || type === 'fscore') {
      setFigure(null);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/chart/${type}?days=250`);
      const json = await res.json();
      setFigure(json);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  if (!dataLoaded) {
    return <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">请先获取股票数据</div>;
  }

  const isImage = activeType === 'dupont' || activeType === 'fscore';

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <div className="flex gap-1 px-4 py-2 border-b border-[var(--color-border)] overflow-x-auto">
        {CHART_TYPES.map((ct) => (
          <button
            key={ct.key}
            onClick={() => fetchChart(ct.key)}
            className={`px-3 py-1 text-xs rounded-md transition-colors whitespace-nowrap ${
              activeType === ct.key
                ? 'bg-[var(--color-accent)] text-white'
                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'
            }`}
          >
            {ct.label}
          </button>
        ))}
      </div>
      <div className="flex-1 flex items-center justify-center p-2">
        {loading ? (
          <div className="text-[var(--color-text-muted)]">加载中...</div>
        ) : isImage ? (
          <img
            src={`/chart/img/${activeType}`}
            alt={activeType}
            className="max-w-full max-h-full object-contain"
          />
        ) : figure ? (
          <Suspense fallback={<div className="text-[var(--color-text-muted)]">加载图表...</div>}>
            <Plot
              data={figure.data}
              layout={{ ...figure.layout, paper_bgcolor: '#06080E', plot_bgcolor: '#06080E', font: { color: '#94A3B8' } }}
              useResizeHandler
              style={{ width: '100%', height: '100%' }}
              config={{ responsive: true, displayModeBar: false }}
            />
          </Suspense>
        ) : (
          <div className="text-[var(--color-text-muted)]">点击上方选择图表类型</div>
        )}
      </div>
    </div>
  );
}
