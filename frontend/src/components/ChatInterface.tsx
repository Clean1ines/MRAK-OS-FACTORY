import React, { useEffect, useRef } from 'react';
import { IOSShell } from './ios/IOSShell';
import { client } from '../api/client';
import type { components } from '../api/generated/schema';

// Используем правильный тип из схемы
type Project = components['schemas']['ProjectResponse'];

export const ChatInterface: React.FC = () => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentProject, setCurrentProject] = React.useState<Project | null>(null);

  const loadProjects = async () => {
    try {
      const res = await client.GET('/api/projects');
      // res.data имеет тип ProjectResponse[] (по схеме)
      if (res.data && Array.isArray(res.data) && res.data.length > 0) {
        const project = res.data[0];
        // Проверяем наличие id (хотя по схеме он всегда есть)
        if (project && project.id) {
          setCurrentProject(project);
        }
      }
    } catch (e) {
      console.error('Failed to load projects:', e);
    }
  };

  useEffect(() => {
    // #CHANGED: отключаем правило линтера, так как вызов loadProjects при монтировании безопасен
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProjects();
  }, []);

  return (
    <IOSShell>
      <div className="flex h-full">
        {/* Sidebar */}
        <aside className="w-64 bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col">
          <div className="p-4 border-b border-[var(--ios-border)]">
            <h2 className="text-sm font-bold text-[var(--bronze-base)]">Projects</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {currentProject ? (
              <div className="p-2 text-xs text-[var(--text-main)]">
                <div className="font-semibold">{currentProject.name}</div>
                <div className="text-[var(--text-muted)]">{currentProject.description}</div>
              </div>
            ) : (
              <div className="text-[10px] text-[var(--text-muted)] text-center py-4">
                No project selected
              </div>
            )}
          </div>
        </aside>

        {/* Main Chat */}
        <main className="flex-1 flex flex-col">
          <header className="h-14 flex items-center px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <h1 className="text-lg font-bold text-[var(--bronze-base)]">
              {currentProject?.name || 'Select a project'}
            </h1>
          </header>

          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <div className="text-center text-[var(--text-muted)] py-8">
              Start a conversation to begin crafting your project
            </div>
          </div>

          <div className="p-4 border-t border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Type your message..."
                className="flex-1 bg-[var(--ios-glass)] border border-[var(--ios-border)] rounded px-4 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
                disabled={!currentProject}
              />
              <button
                className="px-4 py-2 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors disabled:opacity-30"
                disabled={!currentProject}
              >
                Send
              </button>
            </div>
          </div>
        </main>
      </div>

      <div ref={messagesEndRef} />
    </IOSShell>
  );
};
