import type { KpiData } from '@/types';
import { KpiCard } from './KpiCard';

interface Props {
  kpis: KpiData | null;
}

export function KpiCardGrid({ kpis }: Props) {
  if (!kpis) {
    return (
      <div className="flex gap-3 px-4 py-2 overflow-x-auto">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="glass-card p-3 min-w-[140px] animate-pulse">
            <div className="h-3 bg-[var(--color-bg-tertiary)] rounded w-12 mb-2" />
            <div className="h-5 bg-[var(--color-bg-tertiary)] rounded w-20" />
          </div>
        ))}
      </div>
    );
  }

  const trend = kpis.change_pct != null ? (kpis.change_pct >= 0 ? 'up' as const : 'down' as const) : null;

  return (
    <div className="flex gap-3 px-4 py-2 overflow-x-auto">
      <KpiCard label="股票名称" value={kpis.stock_name || kpis.stock_code || '--'} />
      <KpiCard label="当前价格" value={kpis.price != null ? `${kpis.price.toFixed(2)}` : '--'} />
      <KpiCard label="涨跌幅" value={kpis.change_pct != null ? `${kpis.change_pct > 0 ? '+' : ''}${kpis.change_pct.toFixed(2)}%` : '--'} trend={trend} />
      <KpiCard label="成交量" value={kpis.volume || '--'} />
      <KpiCard label="市盈率 PE" value={kpis.pe != null ? kpis.pe.toFixed(2) : '--'} />
      <KpiCard label="总市值" value={kpis.market_cap || '--'} sub={kpis.pb != null ? `PB ${kpis.pb.toFixed(2)}` : undefined} />
    </div>
  );
}
