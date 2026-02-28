import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useNotification } from './useNotifications';
import { useStreaming } from './useStreaming';

export const useSendMessage = () => {
  const [inputValue, setInputValue] = useState('');
  const { showNotification } = useNotification();
  const addMessage = useAppStore((s) => s.addMessage);
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const selectedModel = useAppStore((s) => s.selectedModel);
  const mode = '01_CORE';

  const { isStreaming, startStream } = useStreaming();

  const sendMessage = async (text: string) => {
    if (!currentProjectId) {
      showNotification('Сначала выберите проект', 'error');
      return;
    }
    if (!text.trim()) return;

    addMessage({ role: 'user', content: text, timestamp: Date.now() });
    setInputValue('');

    await startStream(
      { prompt: text, mode, model: selectedModel || undefined, project_id: currentProjectId },
      {
        // #CHANGED: removed unused parameter
        onChunk: () => {},
        onFinish: (fullText) => {
          addMessage({ role: 'assistant', content: fullText, timestamp: Date.now() });
        },
        onError: (err) => {
          const message = err instanceof Error ? err.message : String(err);
          showNotification('Ошибка: ' + message, 'error');
        },
      }
    );
  };

  return { sendMessage, isStreaming, inputValue, setInputValue };
};
