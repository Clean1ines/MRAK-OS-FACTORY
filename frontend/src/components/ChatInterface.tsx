import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';
import { useProjects } from '../hooks/useProjects';
import { IOSShell } from './ios/IOSShell';

export const ChatInterface: React.FC = () => {
  const navigate = useNavigate();
  const { currentProjectId } = useAppStore();
  const { projects } = useProjects();
  const [message, setMessage] = useState('');

  const currentProject = projects.find(p => p.id === currentProjectId);

  const handleSend = () => {
    if (!message.trim() || !currentProjectId) return;
    console.log('Sending message:', message, 'for project:', currentProjectId);
    setMessage('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <IOSShell>
      <div className="flex h-full w-full min-w-0 overflow-hidden">
        <main className="flex-1 flex flex-col w-full min-w-0 overflow-x-hidden">
          <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <h1 className="text-lg font-bold text-[var(--bronze-base)] truncate max-w-full">
              {currentProject?.name || 'Select a project'}
            </h1>
            <button
              onClick={() => navigate('/workspace')}
              className="px-4 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors whitespace-nowrap"
            >
              Manage Workflows
            </button>
          </header>

          <div className="flex-1 overflow-y-auto p-6 space-y-4 w-full min-w-0">
            <div className="text-center text-[var(--text-muted)] py-8">
              Start a conversation to begin crafting your project
            </div>
          </div>

          <div className="p-4 border-t border-[var(--ios-border)] bg-[var(--ios-glass-dark)] w-full min-w-0">
            <div className="flex gap-2 w-full min-w-0">
              <input
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message..."
                className="flex-1 min-w-0 max-w-full bg-[var(--ios-glass)] border border-[var(--ios-border)] rounded px-4 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
                disabled={!currentProjectId}
              />
              <button
                onClick={handleSend}
                disabled={!currentProjectId || !message.trim()}
                className="px-4 py-2 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed whitespace-nowrap"
              >
                Send
              </button>
            </div>
          </div>
        </main>
      </div>
    </IOSShell>
  );
};
