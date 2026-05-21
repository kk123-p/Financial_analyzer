import { useParams, useNavigate } from 'react-router-dom';
import { useAnalysis } from '@/hooks/useAnalysis';
import { useAppStore } from '@/store/appStore';
import { ArrowLeft } from 'lucide-react';

export function AnalysisPage() {
  const { type } = useParams<{ type: string }>();
  const { data, isLoading, error } = useAnalysis(type || null);
  const { dataLoaded } = useAppStore();
  const navigate = useNavigate();

  if (!dataLoaded) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-muted)]">
        请先获取股票数据
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full animate-fade-in">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[var(--color-border)]">
        <button onClick={() => navigate(-1)} className="p-1 hover:text-[var(--color-accent)]">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <span className="text-sm text-[var(--color-text-secondary)]">
          分析结果: <span className="text-[var(--color-accent)] font-mono">{type}</span>
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-4 bg-[var(--color-bg-tertiary)] rounded animate-pulse" style={{ width: `${60 + Math.random() * 40}%` }} />
            ))}
          </div>
        ) : error ? (
          <div className="text-[var(--color-negative)]">{error.message}</div>
        ) : data?.result_html ? (
          <div
            className="text-sm leading-relaxed font-mono whitespace-pre-wrap text-[var(--color-text-primary)]"
            dangerouslySetInnerHTML={{ __html: data.result_html }}
          />
        ) : data?.result_text ? (
          <pre className="text-sm leading-relaxed font-mono whitespace-pre-wrap text-[var(--color-text-primary)]">
            {data.result_text}
          </pre>
        ) : null}
      </div>
    </div>
  );
}
