import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function StatusBar() {
  const { data } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
    refetchInterval: 30000,
  });

  return (
    <div className="flex items-center justify-between px-4 py-1 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] text-xs text-[var(--color-text-muted)]">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-positive)]" />
          FA Pro v10.6
        </span>
        <span>数据源: {data?.active_source || '--'}</span>
        <span>Tushare: {data?.has_tushare ? '✓' : '✗'}</span>
        <span>DeepSeek: {data?.has_deepseek ? '✓' : '✗'}</span>
      </div>
      <div className="font-mono">
        {new Date().toLocaleTimeString('zh-CN')}
      </div>
    </div>
  );
}
