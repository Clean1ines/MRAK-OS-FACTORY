import { useState, useCallback } from 'react';
import { client } from '../api/client';

export const useStreaming = () => {
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = useCallback(
    async (
      body: { prompt: string; mode?: string; model?: string; project_id?: string },
      callbacks: {
        onChunk: (chunk: string) => void;
        onFinish: (fullText: string) => void;
        // #CHANGED: any -> unknown
        onError?: (err: unknown) => void;
      }
    ) => {
      setIsStreaming(true);
      try {
        const response = await client.POST('/api/analyze', {
          body,
          parseAs: 'stream',
        });
        if (!response.data || !(response.data instanceof ReadableStream)) {
          throw new Error('Не удалось получить поток');
        }
        const reader = response.data.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          fullText += chunk;
          callbacks.onChunk(chunk);
        }
        callbacks.onFinish(fullText);
      } catch (err) {
        if (callbacks.onError) callbacks.onError(err);
        else console.error(err);
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  return { isStreaming, startStream };
};
