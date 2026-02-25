import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useNotification } from './useNotifications';
import { api } from '../api/client';

// #ADDED: Local type for message artifacts (since schema has empty content)
interface MessageArtifact {
  id?: string;
  type?: string;
  parent_id?: string | null;
  content?: {
    role?: string;
    content?: string;
  };
  created_at?: string;
  updated_at?: string;
  version?: string;
  status?: string;
  summary?: string;
}

export const useProjectData = () => {
  const setProjects = useAppStore((s) => s.setProjects);
  const setModels = useAppStore((s) => s.setModels);
  const setModes = useAppStore((s) => s.setModes);
  const setArtifactTypes = useAppStore((s) => s.setArtifactTypes);
  const setArtifacts = useAppStore((s) => s.setArtifacts);
  const setMessages = useAppStore((s) => s.setMessages);
  const currentProjectId = useAppStore((s) => s.currentProjectId);
  const { showNotification } = useNotification();

  // Загрузка проектов
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const { data, error } = await api.projects.list();
        if (error) throw error;
        const projects = (data || []).map((p) => ({
          id: p.id!,
          name: p.name!,
          description: p.description!,
        }));
        setProjects(projects);
      } catch {
        showNotification('Ошибка загрузки проектов', 'error');
      }
    };
    loadProjects();
  }, [setProjects, showNotification]);

  // Загрузка моделей
  useEffect(() => {
    const loadModels = async () => {
      try {
        const { data, error } = await api.models.list();
        if (error) throw error;
        const models = (data || []).map((m) => ({ id: m.id! }));
        setModels(models);
      } catch {
        console.warn('Failed to load models');
      }
    };
    loadModels();
  }, [setModels]);

  // Загрузка режимов
  useEffect(() => {
    const loadModes = async () => {
      try {
        const { data, error } = await api.modes.list();
        if (error) throw error;
        const modes = (data || []).map((m) => ({
          id: m.id!,
          name: m.name!,
          default: m.default,
        }));
        setModes(modes);
      } catch {
        console.warn('Failed to load modes');
      }
    };
    loadModes();
  }, [setModes]);

  // Загрузка типов артефактов
  useEffect(() => {
    const loadArtifactTypes = async () => {
      try {
        const { data, error } = await api.artifactTypes.list();
        if (error) throw error;
        const types = (data || []).map((t) => ({
          type: t.type!,
          allowed_parents: t.allowed_parents!,
          requires_clarification: t.requires_clarification!,
          schema: t.schema,
          icon: t.icon,
        }));
        setArtifactTypes(types);
      } catch {
        console.warn('Failed to load artifact types');
      }
    };
    loadArtifactTypes();
  }, [setArtifactTypes]);

  // Загрузка артефактов при смене проекта
  useEffect(() => {
    const loadArtifacts = async () => {
      if (!currentProjectId) {
        setArtifacts([]);
        return;
      }
      try {
        const { data, error } = await api.artifacts.list(currentProjectId);
        if (error) throw error;
        const artifacts = (data || []).map((a) => ({
          id: a.id!,
          type: a.type!,
          parent_id: a.parent_id ?? null,
          content: a.content ?? {},
          created_at: a.created_at!,
          updated_at: a.updated_at!,
          version: a.version!,
          status: a.status!,
          summary: a.summary,
        }));
        setArtifacts(artifacts);
      } catch {
        console.warn('Failed to load artifacts');
      }
    };
    loadArtifacts();
  }, [currentProjectId, setArtifacts]);

  // Загрузка сообщений при смене проекта
  useEffect(() => {
    const loadMessages = async () => {
      if (!currentProjectId) {
        setMessages([]);
        return;
      }
      try {
        const { data, error } = await api.messages.list(currentProjectId);
        if (error) throw error;
        const messages = (data || []).map((m: MessageArtifact) => {
          const role = m.content?.role;
          // #CHANGED: explicit cast to union type
          const validRole = (role === 'user' || role === 'assistant')
            ? (role as 'user' | 'assistant')
            : 'assistant';
          return {
            role: validRole,
            content: m.content?.content || '',
            timestamp: new Date(m.created_at || '').getTime(),
          };
        });
        setMessages(messages);
      } catch {
        console.warn('Failed to load messages');
      }
    };
    loadMessages();
  }, [currentProjectId, setMessages]);
};
