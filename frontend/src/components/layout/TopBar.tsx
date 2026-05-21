import { useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { DATA_SOURCES } from '@/lib/constants';
import { Search, RefreshCw } from 'lucide-react';

interface Props {
  onFetch: (code: string, source: string) => void;
  loading: boolean;
}

export function TopBar({ onFetch, loading }: Props) {
  const { stockCode, stockName, dataSource, setStock, setDataSource } = useAppStore();
  const [input, setInput] = useState(stockCode);

  const handleFetch = () => {
    if (input.trim()) {
      setStock(input.trim().toUpperCase());
      onFetch(input.trim().toUpperCase(), dataSource);
    }
  };

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
      <div className="flex items-center gap-2 flex-1">
        <input
          className="glass-input w-40 text-sm font-mono"
          placeholder="股票代码 (000001.SZ)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleFetch()}
        />
        <select
          className="glass-input text-sm"
          value={dataSource}
          onChange={(e) => setDataSource(e.target.value)}
        >
          {DATA_SOURCES.map((s) => (
            <option key={s} value={s}>{s.toUpperCase()}</option>
          ))}
        </select>
        <button
          onClick={handleFetch}
          disabled={loading || !input.trim()}
          className="flex items-center gap-1.5 px-4 py-1.5 bg-[var(--color-accent)] text-white rounded-md text-sm hover:bg-[var(--color-accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          获取数据
        </button>
      </div>
      {stockName && (
        <span className="text-sm text-[var(--color-text-secondary)] font-medium">{stockName}</span>
      )}
      <div className="text-xs text-[var(--color-text-muted)] font-mono">
        {new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
      </div>
    </div>
  );
}
