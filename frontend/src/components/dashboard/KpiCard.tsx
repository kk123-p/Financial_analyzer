interface Props {
  label: string;
  value: string;
  sub?: string;
  trend?: 'up' | 'down' | null;
}

export function KpiCard({ label, value, sub, trend }: Props) {
  return (
    <div className="glass-card p-3 flex flex-col justify-between min-w-[140px] animate-fade-in">
      <span className="text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className={`text-lg font-mono font-semibold mt-1 ${
        trend === 'up' ? 'text-[var(--color-positive)]' :
        trend === 'down' ? 'text-[var(--color-negative)]' :
        'text-[var(--color-text-primary)]'
      }`}>
        {value || '--'}
      </span>
      {sub && <span className="text-xs text-[var(--color-text-muted)] mt-0.5">{sub}</span>}
    </div>
  );
}
