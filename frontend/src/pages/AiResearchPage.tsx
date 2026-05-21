import { useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { useDebateWebSocket } from '@/hooks/useDebateWebSocket';
import { api } from '@/lib/api';
import { Send, Play, Square } from 'lucide-react';

const ANALYST_COLORS: Record<string, string> = {
  value: '#3B82F6',
  growth: '#10B981',
  risk: '#EF4444',
  consensus: '#F59E0B',
  _meta: '#64748B',
  _error: '#EF4444',
};

const ANALYST_NAMES: Record<string, string> = {
  value: '价值投资者',
  growth: '成长投资者',
  risk: '风险控制师',
  consensus: '综合共识',
  _meta: '系统',
  _error: '错误',
};

export function AiResearchPage() {
  const { stockCode, dataLoaded } = useAppStore();
  const [tab, setTab] = useState<'chat' | 'debate'>('chat');
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const { connect, disconnect, isConnected, grouped } = useDebateWebSocket();

  const handleChat = async () => {
    if (!question.trim()) return;
    setChatHistory((h) => [...h, { role: 'user', content: question }]);
    setChatLoading(true);
    try {
      const res = await api.aiChat(question, stockCode);
      setChatHistory((h) => [...h, { role: 'ai', content: res.content || res.error || '无响应' }]);
    } catch (e: any) {
      setChatHistory((h) => [...h, { role: 'ai', content: e.message }]);
    }
    setChatLoading(false);
    setQuestion('');
  };

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* Tabs */}
      <div className="flex gap-1 px-4 py-2 border-b border-[var(--color-border)]">
        {[
          ['chat', 'AI 智能分析'],
          ['debate', '三方辩论'],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key as 'chat' | 'debate')}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors ${
              tab === key ? 'bg-[var(--color-accent)] text-white' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!dataLoaded && (
          <div className="text-center text-[var(--color-text-muted)] py-8">请先获取股票数据</div>
        )}

        {tab === 'chat' && (
          <>
            {chatHistory.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] px-4 py-2 rounded-lg text-sm ${
                  msg.role === 'user'
                    ? 'bg-[var(--color-accent)] text-white'
                    : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)]'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="text-sm text-[var(--color-text-muted)] animate-pulse">分析中...</div>
            )}
          </>
        )}

        {tab === 'debate' && (
          <>
            <div className="flex gap-2">
              <button
                onClick={() => connect(stockCode)}
                disabled={isConnected || !stockCode}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-[var(--color-positive)] text-white rounded-md text-sm disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" /> 开始辩论
              </button>
              <button
                onClick={disconnect}
                disabled={!isConnected}
                className="flex items-center gap-1.5 px-4 py-1.5 bg-[var(--color-negative)] text-white rounded-md text-sm disabled:opacity-50"
              >
                <Square className="w-3.5 h-3.5" /> 停止
              </button>
              {isConnected && <span className="text-xs text-[var(--color-positive)] self-center">辩论进行中...</span>}
            </div>
            {grouped.map((g, i) => (
              <div key={i} className="glass-card p-3">
                {g.role !== '_meta' && (
                  <div className="text-xs font-medium mb-1" style={{ color: ANALYST_COLORS[g.role] || '#64748B' }}>
                    {ANALYST_NAMES[g.role] || g.role}
                  </div>
                )}
                <div className="text-sm whitespace-pre-wrap text-[var(--color-text-primary)]">{g.text}</div>
              </div>
            ))}
            {grouped.length === 0 && !isConnected && (
              <div className="text-center text-[var(--color-text-muted)] py-8">点击"开始辩论"启动三方分析师辩论</div>
            )}
          </>
        )}
      </div>

      {tab === 'chat' && dataLoaded && (
        <div className="flex gap-2 px-4 py-2 border-t border-[var(--color-border)]">
          <input
            className="glass-input flex-1 text-sm"
            placeholder="输入财务分析问题..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleChat()}
          />
          <button
            onClick={handleChat}
            disabled={chatLoading || !question.trim()}
            className="p-2 bg-[var(--color-accent)] text-white rounded-md disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
