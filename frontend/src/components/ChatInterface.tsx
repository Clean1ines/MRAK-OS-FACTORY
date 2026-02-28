import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';
import { useProjects } from '../hooks/useProjects';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { IOSShell } from './ios/IOSShell';
import { ChatCanvas } from './ChatCanvas';

export const ChatInterface: React.FC = () => {
  const navigate = useNavigate();
  const { currentProjectId, models, selectedModel, setSelectedModel } = useAppStore();
  const { projects } = useProjects();
  const isMobile = useMediaQuery('(max-width: 768px)');

  const currentProject = projects.find(p => p.id === currentProjectId);

  return (
    <IOSShell>
      <div className="flex h-full w-full min-w-0 overflow-hidden">
        <main className="flex-1 flex flex-col w-full min-w-0 overflow-x-hidden">
          <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <h1 className="text-lg font-bold text-[var(--bronze-base)] truncate">
                {currentProject?.name || 'Select a project'}
              </h1>
              {models.length > 0 && (
                <select
                  value={selectedModel || ''}
                  onChange={(e) => setSelectedModel(e.target.value || null)}
                  className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-2 py-1 text-xs text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
                >
                  <option value="" disabled>Select model</option>
                  {models.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <button
              onClick={() => navigate('/workspace')}
              className="px-4 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors whitespace-nowrap ml-2"
            >
              Manage Workflows
            </button>
          </header>

          <ChatCanvas />
        </main>
      </div>
    </IOSShell>
  );
};
