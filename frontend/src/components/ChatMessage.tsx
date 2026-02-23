import React, { useEffect, useRef } from 'react';
import { marked } from 'marked';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ role, content, isStreaming }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  if (role === 'user') {
    return (
      <div className="border-l-2 border-zinc-800 pl-6 text-sm text-zinc-400" ref={ref}>
        {content}
      </div>
    );
  }

  return (
    <div className="markdown-body" ref={ref}>
      <div dangerouslySetInnerHTML={{ __html: marked.parse(content) as string }} />
      {isStreaming && <span className="inline-block w-2 h-4 bg-cyan-400 animate-pulse ml-1" />}
    </div>
  );
};
