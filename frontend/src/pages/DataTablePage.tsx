import { useState, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { Download } from 'lucide-react';

const DATA_TYPES = ['daily', 'income', 'balance', 'cashflow', 'financial'];

export function DataTablePage() {
  const { stockCode, dataLoaded } = useAppStore();
  const [activeType, setActiveType] = useState('daily');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!dataLoaded) return;
    setLoading(true);
    fetch(`/fetch/data-table`, { credentials: 'include' })
      .then((r) => r.text())
      .then((html) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const table = doc.querySelector('table');
        if (table) {
          const rows = Array.from(table.querySelectorAll('tr'));
          const headers = Array.from(rows[0]?.querySelectorAll('th') || []).map((h) => h.textContent || '');
          const body = rows.slice(1).map((row) =>
            Array.from(row.querySelectorAll('td')).map((td) => td.textContent || '')
          );
          setData([headers, ...body]);
        }
      })
      .finally(() => setLoading(false));
  }, [dataLoaded, activeType]);

  if (!dataLoaded) {
    return <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">请先获取股票数据</div>;
  }

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <div className="flex items-center gap-4 px-4 py-2 border-b border-[var(--color-border)]">
        <div className="flex gap-1">
          {DATA_TYPES.map((dt) => (
            <button
              key={dt}
              onClick={() => setActiveType(dt)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                activeType === dt
                  ? 'bg-[var(--color-accent)] text-white'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'
              }`}
            >
              {dt}
            </button>
          ))}
        </div>
        <div className="flex gap-2 ml-auto">
          {['csv', 'xlsx', 'json'].map((fmt) => (
            <a
              key={fmt}
              href={`/export/${fmt}?stock_code=${stockCode}`}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors"
            >
              <Download className="w-3 h-3" />
              {fmt.toUpperCase()}
            </a>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        {loading ? (
          <div className="text-center text-[var(--color-text-muted)] py-8">加载数据...</div>
        ) : data.length > 0 ? (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                {data[0]?.map((h: string, i: number) => (
                  <th key={i} className="text-left px-3 py-2 text-[var(--color-text-muted)] font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.slice(1).map((row, ri) => (
                <tr key={ri} className="border-b border-[var(--color-border)]/50 hover:bg-[var(--color-bg-tertiary)]">
                  {row.map((cell: string, ci: number) => (
                    <td key={ci} className="px-3 py-1.5 text-[var(--color-text-secondary)] font-mono whitespace-nowrap">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center text-[var(--color-text-muted)] py-8">选择数据类型查看</div>
        )}
      </div>
    </div>
  );
}
