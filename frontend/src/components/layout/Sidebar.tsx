import { useAppStore } from '@/store/appStore';
import { PIPELINE_STAGES } from '@/lib/constants';
import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ChevronDown, ChevronRight, BarChart3, Menu } from 'lucide-react';

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, activeAnalysis, setActiveAnalysis, dataLoaded } = useAppStore();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ "1": true });
  const navigate = useNavigate();
  const location = useLocation();

  const currentType = location.pathname.startsWith('/analyze/')
    ? location.pathname.replace('/analyze/', '')
    : null;

  return (
    <aside className={`flex flex-col bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] transition-all duration-200 ${sidebarCollapsed ? 'w-14' : 'w-64'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-[var(--color-border)]">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[var(--color-accent)]" />
            <span className="font-semibold text-sm text-[var(--color-text-primary)]">FA Pro</span>
          </div>
        )}
        <button onClick={toggleSidebar} className="p-1 rounded hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]">
          <Menu className="w-4 h-4" />
        </button>
      </div>

      {/* Nav Sections */}
      <nav className="flex-1 overflow-y-auto py-2">
        {PIPELINE_STAGES.map((stage, i) => {
          const stageKey = String(i);
          const isExpanded = expanded[stageKey];
          return (
            <div key={stage.stage}>
              <button
                onClick={() => setExpanded((e) => ({ ...e, [stageKey]: !isExpanded }))}
                className="w-full flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              >
                {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                {!sidebarCollapsed && stage.stage}
              </button>
              {isExpanded && stage.items.map((item) => (
                <button
                  key={item.key}
                  disabled={!dataLoaded}
                  onClick={() => { setActiveAnalysis(item.key); navigate(`/analyze/${item.key}`); }}
                  className={`w-full text-left px-6 py-1 text-sm transition-colors truncate ${
                    (currentType || activeAnalysis) === item.key
                      ? 'text-[var(--color-accent)] bg-[var(--color-bg-tertiary)] border-r-2 border-[var(--color-accent)]'
                      : dataLoaded
                        ? 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]'
                        : 'text-[var(--color-text-muted)] cursor-not-allowed'
                  }`}
                >
                  {sidebarCollapsed ? item.label.slice(0, 2) : item.label}
                </button>
              ))}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
