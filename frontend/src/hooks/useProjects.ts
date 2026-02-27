import { useState, useCallback } from 'react';
import { useAppStore, Project } from '../store/useAppStore';
import { useNotification } from './useNotifications';
import { api, getErrorMessage } from '../api/client';

interface CreateProjectParams {
  name: string;
  description?: string;
}

interface UpdateProjectParams {
  id: string;
  name: string;
  description?: string;
}

export const useProjects = () => {
  const { projects, addProject, updateProject, removeProject } = useAppStore();
  const { showNotification } = useNotification();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);

  const validateName = (name: string): string | null => {
    if (!name.trim()) return 'Project name cannot be empty';
    if (name.length > 100) return 'Project name must not exceed 100 characters';
    return null;
  };

  const createProject = useCallback(
    async ({ name, description = '' }: CreateProjectParams) => {
      const validationError = validateName(name);
      if (validationError) {
        showNotification(validationError, 'error');
        return false;
      }

      try {
        const { data, error } = await api.projects.create({ name, description });
        if (error) {
          const message = getErrorMessage(error);
          showNotification(message, 'error');
          return false;
        }

        if (data && data.id && data.name) {
          addProject({
            id: data.id,
            name: data.name,
            description: data.description || '',
          });
          showNotification(`Project "${name}" created`, 'success');
          setIsCreateOpen(false);
          return true;
        }
        return false;
      } catch (err) {
        const message = getErrorMessage(err);
        showNotification(message, 'error');
        return false;
      }
    },
    [addProject, showNotification]
  );

  const updateProjectHandler = useCallback(
    async ({ id, name, description = '' }: UpdateProjectParams) => {
      const validationError = validateName(name);
      if (validationError) {
        showNotification(validationError, 'error');
        return false;
      }

      try {
        const { data, error } = await api.projects.update(id, { name, description });
        if (error) {
          const message = getErrorMessage(error);
          showNotification(message, 'error');
          return false;
        }

        if (data && data.id && data.name) {
          updateProject(id, { name, description });
          showNotification(`Project updated`, 'success');
          setIsEditOpen(false);
          setEditingProject(null);
          return true;
        }
        return false;
      } catch (err) {
        const message = getErrorMessage(err);
        showNotification(message, 'error');
        return false;
      }
    },
    [updateProject, showNotification]
  );

  const deleteProjectHandler = useCallback(
    async (id: string) => {
      try {
        const { error } = await api.projects.delete(id);
        if (error) {
          const message = getErrorMessage(error);
          showNotification(message, 'error');
          return false;
        }

        removeProject(id);
        showNotification('Project deleted', 'success');
        setIsDeleteOpen(false);
        setDeletingProject(null);
        return true;
      } catch (err) {
        const message = getErrorMessage(err);
        showNotification(message, 'error');
        return false;
      }
    },
    [removeProject, showNotification]
  );

  const openEditModal = useCallback((project: Project) => {
    setEditingProject(project);
    setIsEditOpen(true);
  }, []);

  const openDeleteConfirm = useCallback((project: Project) => {
    setDeletingProject(project);
    setIsDeleteOpen(true);
  }, []);

  const closeModals = useCallback(() => {
    setIsCreateOpen(false);
    setIsEditOpen(false);
    setIsDeleteOpen(false);
    setEditingProject(null);
    setDeletingProject(null);
  }, []);

  return {
    projects,
    isCreateOpen,
    isEditOpen,
    isDeleteOpen,
    editingProject,
    deletingProject,
    openCreateModal: () => setIsCreateOpen(true),
    openEditModal,
    openDeleteConfirm,
    closeModals,
    createProject,
    updateProject: updateProjectHandler,
    deleteProject: deleteProjectHandler,
  };
};
