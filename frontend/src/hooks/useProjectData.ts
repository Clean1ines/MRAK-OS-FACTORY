import { useEffect } from 'react';
import { useAppStore } from '../store/useAppStore';
import { useNotification } from './useNotifications';
import { api } from '../api/client';

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
      } catch (e) {
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
      } catch (e) {
        console.warn('Failed to load models', e);
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
      } catch (e) {
        console.warn('Failed to load modes', e);
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
      } catch (e) {
        console.warn('Failed to load artifact types', e);
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
      } catch (e) {
        console.warn('Failed to load artifacts', e);
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
        const messages = (data || []).map((m: any) => ({
          role: m.content?.role || 'assistant',
          content: m.content?.content || '',
          timestamp: new Date(m.created_at).getTime(),
        }));
        setMessages(messages);
      } catch (e) {
        console.warn('Failed to load messages', e);
      }
    };
    loadMessages();
  }, [currentProjectId, setMessages]);
};