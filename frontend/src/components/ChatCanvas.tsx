import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useStreaming } from '../hooks/useStreaming';
import { useNotification } from '../hooks/useNotifications';
import { ChatMessage } from './ChatMessage';

export const ChatCanvas: React.FC = () => {
  const [input, setInput] = useState('');
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const messages = useAppStore(s => s.messages);
  const addMessage = useAppStore(s => s.addMessage);
  const currentProjectId = useAppStore(s => s.currentProjectId);
  const selectedModel = useAppStore(s => s.selectedModel);
  const showNotification = useNotification().showNotification;

  const { isStreaming, startStream } = useStreaming();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!input.trim()) return;
    if (!currentProjectId) {
      showNotification('Сначала выберите проект', 'error');
      return;
    }

    const userMsg = { role: 'user' as const, content: input, timestamp: Date.now() };
    addMessage(userMsg);
    setInput('');
    setStreamingContent('');

    await startStream(
      {
        prompt: userMsg.content,
        mode: '01_CORE', // временно
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
          // #CHANGED: handle unknown error
          const message = err instanceof Error ? err.message : String(err);
          showNotification('Ошибка: ' + message, 'error');
          setStreamingContent(null);
        },
      }
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} role={msg.role} content={msg.content} />
        ))}
        {streamingContent !== null && (
          <ChatMessage role="assistant" content={streamingContent} isStreaming />
        )}
      </div>
      <div className="p-4 border-t border-white/10">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Введите запрос..."
            rows={1}
            className="flex-1 bg-black/50 border border-cyan-800/50 rounded p-2 text-cyan-100 resize-none outline-none focus:border-cyan-500"
          />
          <button
            onClick={handleSend}
            disabled={isStreaming}
            className="px-4 py-2 bg-cyan-600/20 text-cyan-400 border border-cyan-600/50 rounded hover:bg-cyan-600/40 disabled:opacity-50"
          >
            Отправить
          </button>
        </div>
      </div>
    </div>
  );
};
