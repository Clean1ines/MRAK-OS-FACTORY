import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useStreaming } from '../hooks/useStreaming';
import { useNotification } from '../hooks/useNotifications';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { ChatMessage } from './ChatMessage';

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

export const ChatCanvas: React.FC = () => {
  const [message, setMessage] = useState('');
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const messages = useAppStore(s => s.messages);
  const addMessage = useAppStore(s => s.addMessage);
  const currentProjectId = useAppStore(s => s.currentProjectId);
  const selectedModel = useAppStore(s => s.selectedModel);
  const showNotification = useNotification().showNotification;

  const { startStream } = useStreaming(); // #CHANGED: removed unused isStreaming
  const scrollRef = useRef<HTMLDivElement>(null);
  const isMobile = useMediaQuery('(max-width: 768px)');

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!message.trim()) return;
    if (!currentProjectId) {
      showNotification('Сначала выберите проект', 'error');
      return;
    }

    const userMsg = { role: 'user' as const, content: message, timestamp: Date.now() };
    addMessage(userMsg);
    setMessage('');
    setStreamingContent('');

    await startStream(
      {
        prompt: userMsg.content,
        mode: '01_CORE',
        model: selectedModel || undefined,
        project_id: currentProjectId,
      },
      {
        onChunk: (chunk) => {
          setStreamingContent((prev) => (prev || '') + chunk);
        },
        onFinish: (fullText) => {
          addMessage({ role: 'assistant', content: fullText, timestamp: Date.now() });
          setStreamingContent(null);
        },
        onError: (err) => {
          const messageErr = err instanceof Error ? err.message : String(err);
          showNotification('Ошибка: ' + messageErr, 'error');
          setStreamingContent(null);
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const showMrakBrand = messages.length === 0 && !streamingContent;

  return (
    <div className="flex-1 flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 p-4 relative">
        {showMrakBrand && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-6xl font-bold text-[var(--bronze-base)] opacity-[0.03] select-none">
              MADE IN MRAK
            </div>
          </div>
        )}
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} role={msg.role} content={msg.content} />
        ))}
        {streamingContent !== null && (
          <ChatMessage role="assistant" content={streamingContent} isStreaming />
        )}
      </div>
      <div className="p-4 border-t border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
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
    </div>
  );
};
