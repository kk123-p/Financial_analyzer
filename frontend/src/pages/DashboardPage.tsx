import { useStockData } from '@/hooks/useStockData';
import { useAppStore } from '@/store/appStore';
import { KpiCardGrid } from '@/components/dashboard/KpiCardGrid';
import { TopBar } from '@/components/layout/TopBar';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, ShieldCheck, MessageSquare, BarChart3 } from 'lucide-react';

export function DashboardPage() {
  const mutation = useStockData();
  const { dataLoaded, stockCode } = useAppStore();
  const navigate = useNavigate();

  const kpis = mutation.data?.kpis || null;

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <TopBar onFetch={(code, source) => mutation.mutate({ code, source })} loading={mutation.isPending} />
      <KpiCardGrid kpis={kpis} />

      {mutation.isError && (
        <div className="mx-4 mt-2 p-3 bg-red-900/20 border border-red-800 rounded-lg text-sm text-red-400">
          {mutation.error?.message || '数据获取失败'}
        </div>
      )}

      <div className="flex-1 flex items-center justify-center">
        {!dataLoaded ? (
          <div className="text-center text-[var(--color-text-muted)]">
            <BarChart3 className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p className="text-lg">输入股票代码开始分析</p>
            <p className="text-sm mt-1">例如: 000001.SZ, 600519.SH, AAPL</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 max-w-lg">
            {[
              { key: 'comprehensive', label: '综合投资评级', icon: TrendingUp, desc: '金字塔7维评分' },
              { key: 'ratio_analysis', label: '财务比率分析', icon: ShieldCheck, desc: '五类核心比率' },
              { key: 'dupont', label: '杜邦深度分析', icon: BarChart3, desc: '三因子+五因子' },
            ].map(({ key, label, icon: Icon, desc }) => (
              <button
                key={key}
                onClick={() => navigate(`/analyze/${key}`)}
                className="glass-card p-5 text-left hover:border-[var(--color-accent)] transition-all group"
              >
                <Icon className="w-6 h-6 text-[var(--color-accent)] mb-2 group-hover:scale-110 transition-transform" />
                <div className="font-medium text-sm text-[var(--color-text-primary)]">{label}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">{desc}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
