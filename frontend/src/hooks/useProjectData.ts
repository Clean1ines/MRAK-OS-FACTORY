import { useModels } from './useModels';
import { useModes } from './useModes';
import { useArtifactTypes } from './useArtifactTypes';
import { useArtifacts } from './useArtifacts';
import { useMessages } from './useMessages';

/**
 * Хук-агрегатор для инициализации всех данных проекта.
 * Вызывает хуки загрузки моделей, режимов, типов артефактов,
 * а также артефактов и сообщений для текущего проекта.
 * 
 * Используется в ProtectedLayout для предварительной загрузки данных.
 */
export const useProjectData = () => {
  // Загружаем статические данные
  useModels();
  useModes();
  useArtifactTypes();

  // Загружаем динамические данные для текущего проекта
  useArtifacts();
  useMessages();

  // Ничего не возвращаем, данные автоматически попадают в store
};
