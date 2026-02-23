import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useNotification } from './useNotifications';
import { useStreaming } from './useStreaming';

export const useSendMessage = () => {
  const [inputValue, setInputValue] = useState('');
  const { showNotification } = useNotification();
  const addMessage = useAppStore((s) => s.addMessage);
  const setTokens = useAppStore((s) => s.setTokens);
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const selectedModel = useAppStore((s) => s.selectedModel);
  // Можно добавить выбор mode из стора
  const mode = '01_CORE'; // пока хардкод

  const { isStreaming, startStream } = useStreaming();

  const sendMessage = async (text: string) => {
    if (!currentProjectId) {
      showNotification('Сначала выберите проект', 'error');
      return;
    }
    if (!text.trim()) return;

    // Добавляем сообщение пользователя
    addMessage({ role: 'user', content: text, timestamp: Date.now() });

    // Очищаем поле ввода
    setInputValue('');

    // Создаём временное сообщение ассистента, которое будем обновлять
    let assistantMessageId: string | null = null;
    let accumulated = '';

    await startStream(
      { prompt: text, mode, model: selectedModel || undefined, project_id: currentProjectId },
      {
        onChunk: (chunk) => {
          accumulated += chunk;
          // Если у нас ещё нет сообщения ассистента, создаём его
          if (!assistantMessageId) {
            // Временно добавим пустое сообщение, затем будем обновлять последнее
            // Но проще: в сторе нет ID, поэтому будем удалять последнее ассистентское и добавлять новое
            // Для простоты реализуем так: каждый раз при чанке заменяем последнее сообщение, если оно ассистентское
            // Но это не оптимально. Лучше хранить буфер в локальном стейте компонента чата, а по окончании добавлять в стор.
            // Пока для простоты сделаем так: будем использовать локальный стейт в компоненте чата, а здесь просто вызовем коллбэк.
            // Но мы не можем здесь менять стейт компонента. Значит, нужен другой подход.
            // Вместо этого я сделаю так, что useSendMessage будет возвращать только функцию отправки, а компонент сам будет управлять временным сообщением.
          }
        },
        onFinish: (fullText) => {
          addMessage({ role: 'assistant', content: fullText, timestamp: Date.now() });
        },
        onError: (err) => {
          showNotification('Ошибка: ' + err.message, 'error');
        },
      }
    );
  };

  return { sendMessage, isStreaming, inputValue, setInputValue };
};
