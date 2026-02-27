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
        const projects = Array.isArray(data)
          ? data.map((p) => ({
              id: p.id!,
              name: p.name!,
              description: p.description!,
            }))
          : [];
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
        const models = Array.isArray(data)
          ? data.map((m: { id?: string }) => ({ id: m.id! }))
          : [];
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
        const modes = Array.isArray(data)
          ? data.map((m: { id?: string; name?: string; default?: boolean }) => ({
              id: m.id!,
              name: m.name!,
              default: m.default,
            }))
          : [];
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
        const types = Array.isArray(data)
          ? data.map((t: { type?: string; allowed_parents?: string[]; requires_clarification?: boolean; schema?: unknown; icon?: unknown }) => ({
              type: t.type!,
              allowed_parents: t.allowed_parents!,
              requires_clarification: t.requires_clarification!,
              schema: t.schema,
              icon: t.icon,
            }))
          : [];
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
        const artifacts = Array.isArray(data)
          ? data.map((a: { id?: string; type?: string; parent_id?: string | null; content?: unknown; created_at?: string; updated_at?: string; version?: string; status?: string; summary?: string }) => ({
              id: a.id!,
              type: a.type!,
              parent_id: a.parent_id ?? null,
              // #CHANGED: приводим к Record<string, unknown>, так как в сторе ожидается именно такой тип
              content: (a.content ?? {}) as Record<string, unknown>,
              created_at: a.created_at!,
              updated_at: a.updated_at!,
              version: a.version!,
              status: a.status!,
              summary: a.summary,
            }))
          : [];
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
        const messages = Array.isArray(data)
          ? data.map((m: MessageArtifact) => {
              const role = m.content?.role;
              const validRole = (role === 'user' || role === 'assistant')
                ? (role as 'user' | 'assistant')
                : 'assistant';
              return {
                role: validRole,
                content: m.content?.content || '',
                timestamp: new Date(m.created_at || '').getTime(),
              };
            })
          : [];
        setMessages(messages);
      } catch {
        console.warn('Failed to load messages');
      }
    };
    loadMessages();
  }, [currentProjectId, setMessages]);
};
