import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../store/useAppStore';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { IOSShell } from './ios/IOSShell';

// Компонент расширяющегося textarea с ограничением по высоте и кнопкой отправки внутри
const ExpandingTextarea: React.FC<{
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onSend: () => void;
  disabled: boolean;
  placeholder: string;
  isMobile: boolean;
}> = ({ value, onChange, onKeyDown, onSend, disabled, placeholder, isMobile }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineHeight = 24; // приблизительная высота строки
  const maxRows = isMobile ? 5 : 15;
  const maxHeight = lineHeight * maxRows;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, maxHeight);
      textareaRef.current.style.height = `${newHeight}px`;
      textareaRef.current.style.overflowY = textareaRef.current.scrollHeight > maxHeight ? 'auto' : 'hidden';
    }
  }, [value, maxHeight]);

  return (
    <div className={`relative w-full ${isMobile ? 'max-w-full' : 'max-w-[40%]'} mx-auto`}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="w-full bg-[var(--ios-glass)] border border-[var(--ios-border)] rounded-lg px-4 py-3 pr-16 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)] resize-none overflow-hidden"
        style={{ minHeight: '48px' }}
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="absolute bottom-2 right-2 px-3 py-1 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </div>
  );
};

export const ChatInterface: React.FC = () => {
  const navigate = useNavigate();
  const { currentProjectId } = useAppStore();
  const messages = useAppStore(s => s.messages);
  const [message, setMessage] = useState('');
  const isMobile = useMediaQuery('(max-width: 768px)');

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

  const showMrakBrand = messages.length === 0;

  return (
    <IOSShell>
      <div className="flex h-full w-full min-w-0 overflow-hidden">
        <main className="flex-1 flex flex-col w-full min-w-0 overflow-x-hidden">
          <header className="h-14 flex items-center justify-end px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <button
              onClick={() => navigate('/workspace')}
              className="px-4 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors whitespace-nowrap"
            >
              Manage Workflows
            </button>
          </header>

          <div className="flex-1 overflow-y-auto p-6 space-y-4 w-full min-w-0 relative">
            {showMrakBrand ? (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-6xl font-bold text-[var(--bronze-base)] opacity-[0.03] select-none">
                  MADE IN MRAK
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Сообщения будут рендериться здесь */}
              </div>
            )}
          </div>

          <div className="p-4 border-t border-[var(--ios-border)] bg-[var(--ios-glass-dark)] w-full min-w-0">
            <ExpandingTextarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onSend={handleSend}
              disabled={!currentProjectId}
              placeholder={currentProjectId ? "Type your message..." : "Select a project first"}
              isMobile={isMobile}
            />
          </div>
        </main>
      </div>
    </IOSShell>
  );
};
