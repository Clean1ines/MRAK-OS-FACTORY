import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { client } from '../api/client';
import { useAppStore } from '../store/useAppStore';
import { useNotification } from './useNotifications';

export const useProjectData = () => {
  const { showNotification } = useNotification();
  const setProjects = useAppStore(s => s.setProjects);
  const setModels = useAppStore(s => s.setModels);
  const setArtifactTypes = useAppStore(s => s.setArtifactTypes);
  const currentProjectId = useAppStore(s => s.currentProjectId);
  const setArtifacts = useAppStore(s => s.setArtifacts);
  const setMessages = useAppStore(s => s.setMessages);

  // Загрузка проектов
  const { data: projects, error: projectsError } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await client.GET('/api/projects');
      if (res.error) throw res.error;
      return res.data;
    },
  });
  useEffect(() => {
    if (projects) setProjects(projects);
    if (projectsError) showNotification('Ошибка загрузки проектов', 'error');
  }, [projects, projectsError, setProjects, showNotification]);

  // Загрузка моделей
  const { data: models, error: modelsError } = useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const res = await client.GET('/api/models');
      if (res.error) throw res.error;
      return res.data;
    },
  });
  useEffect(() => {
    if (models) setModels(models);
    if (modelsError) showNotification('Ошибка загрузки моделей', 'error');
  }, [models, modelsError, setModels, showNotification]);

  // Загрузка типов артефактов
  const { data: artifactTypes, error: typesError } = useQuery({
    queryKey: ['artifactTypes'],
    queryFn: async () => {
      const res = await client.GET('/api/artifact-types');
      if (res.error) throw res.error;
      return res.data;
    },
  });
  useEffect(() => {
    if (artifactTypes) setArtifactTypes(artifactTypes);
    if (typesError) showNotification('Ошибка загрузки типов артефактов', 'error');
  }, [artifactTypes, typesError, setArtifactTypes, showNotification]);

  // Загрузка артефактов при смене проекта
  const { data: artifacts, refetch: refetchArtifacts } = useQuery({
    queryKey: ['artifacts', currentProjectId],
    queryFn: async () => {
      if (!currentProjectId) return [];
      const res = await client.GET('/api/projects/{project_id}/artifacts', {
        params: { path: { project_id: currentProjectId } },
      });
      if (res.error) throw res.error;
      return res.data;
    },
    enabled: !!currentProjectId,
  });
  useEffect(() => {
    if (artifacts) setArtifacts(artifacts);
  }, [artifacts, setArtifacts]);

  // Загрузка сообщений при смене проекта
  const { data: messages } = useQuery({
    queryKey: ['messages', currentProjectId],
    queryFn: async () => {
      if (!currentProjectId) return [];
      const res = await client.GET('/api/projects/{project_id}/messages', {
        params: { path: { project_id: currentProjectId } },
      });
      if (res.error) throw res.error;
      return res.data;
    },
    enabled: !!currentProjectId,
  });
  useEffect(() => {
    if (messages) {
      // преобразуем артефакты LLMResponse в простые сообщения
      const msgs: { role: 'user' | 'assistant'; content: string; timestamp: number }[] = [];
      messages.forEach((msg: any) => {
        if (msg.content?.user_input) {
          msgs.push({ role: 'user', content: msg.content.user_input, timestamp: Date.parse(msg.created_at) });
        }
        if (msg.content?.response) {
          msgs.push({ role: 'assistant', content: msg.content.response, timestamp: Date.parse(msg.created_at) });
        }
      });
      setMessages(msgs);
    }
  }, [messages, setMessages]);

  return { refetchArtifacts };
};
