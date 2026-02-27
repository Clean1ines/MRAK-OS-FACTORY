import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore, Project } from '../../store/useAppStore'; // #CHANGED импортируем Project
import { useProjects } from '../../hooks/useProjects';

// Простые UI-компоненты (заменить на импорты из UI-библиотеки при наличии)
const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = (props) => (
  <button {...props} className={`px-3 py-1 rounded ${props.className || ''}`} />
);

const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = (props) => (
  <input {...props} className={`border rounded px-2 py-1 w-full ${props.className || ''}`} />
);

const Modal: React.FC<{ isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode }> = ({
  isOpen,
  onClose,
  title,
  children,
}) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded p-6 w-96">
        <h2 className="text-xl font-bold mb-4">{title}</h2>
        {children}
        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={onClose} className="bg-gray-300">Cancel</Button>
        </div>
      </div>
    </div>
  );
};

/**
 * Компонент боковой панели со списком проектов
 */
export const ProjectsSidebar: React.FC = () => {
  const navigate = useNavigate();
  const { currentProjectId, setCurrentProjectId } = useAppStore();
  const {
    projects,
    isCreateOpen,
    isEditOpen,
    isDeleteOpen,
    editingProject,
    deletingProject,
    openCreateModal: originalOpenCreateModal,
    openEditModal: originalOpenEditModal,
    openDeleteConfirm,
    closeModals: originalCloseModals,
    createProject,
    updateProject,
    deleteProject,
  } = useProjects();

  // Локальные состояния для форм
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [editProjectName, setEditProjectName] = useState('');
  const [editProjectDescription, setEditProjectDescription] = useState('');

  // --- Локальные обработчики открытия/закрытия с управлением формой ---
  const handleOpenCreate = () => {
    // Сбрасываем поля формы перед открытием
    setNewProjectName('');
    setNewProjectDescription('');
    originalOpenCreateModal();
  };

  const handleOpenEdit = (project: Project) => {
    // Заполняем поля данными редактируемого проекта
    setEditProjectName(project.name);
    setEditProjectDescription(project.description);
    originalOpenEditModal(project);
  };

  const handleCloseModals = () => {
    // Закрываем модалки и сбрасываем поля форм
    originalCloseModals();
    setNewProjectName('');
    setNewProjectDescription('');
    setEditProjectName('');
    setEditProjectDescription('');
  };

  // --- Обработчики отправки форм ---
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await createProject({
      name: newProjectName,
      description: newProjectDescription,
    });
    if (success) {
      // Поля сбросятся в handleCloseModals, но можно и здесь
      setNewProjectName('');
      setNewProjectDescription('');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject) return;
    const success = await updateProject({
      id: editingProject.id,
      name: editProjectName,
      description: editProjectDescription,
    });
    if (success) {
      // Поля сбросятся в handleCloseModals
      setEditProjectName('');
      setEditProjectDescription('');
    }
  };

  const handleDelete = async () => {
    if (!deletingProject) return;
    await deleteProject(deletingProject.id);
  };

  // --- Навигация при клике на проект ---
  const handleProjectClick = (projectId: string) => {
    setCurrentProjectId(projectId);
    navigate('/workspace');
  };

  return (
    <aside className="w-64 h-full bg-gray-100 border-r flex flex-col">
      {/* Заголовок и кнопка создания */}
      <div className="p-4 border-b">
        <Button onClick={handleOpenCreate} className="w-full bg-blue-500 text-white hover:bg-blue-600">
          + New Project
        </Button>
      </div>

      {/* Список проектов */}
      <div className="flex-1 overflow-y-auto p-2">
        {projects.map((project) => (
          <div
            key={project.id}
            className={`p-2 mb-1 rounded cursor-pointer flex items-center justify-between hover:bg-gray-200 ${
              currentProjectId === project.id ? 'bg-blue-100' : ''
            }`}
            onClick={() => handleProjectClick(project.id)}
          >
            <span className="truncate flex-1">{project.name}</span>
            <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => handleOpenEdit(project)}
                className="text-gray-600 hover:text-blue-600"
                title="Edit"
              >
                ✎
              </button>
              <button
                onClick={() => openDeleteConfirm(project)}
                className="text-gray-600 hover:text-red-600"
                title="Delete"
              >
                🗑
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Счётчик проектов */}
      <div className="p-3 border-t text-sm text-gray-600">
        {projects.length} {projects.length === 1 ? 'project' : 'projects'}
      </div>

      {/* Модальное окно создания проекта */}
      <Modal isOpen={isCreateOpen} onClose={handleCloseModals} title="Create New Project">
        <form onSubmit={handleCreate}>
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Project Name *</label>
            <Input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              required
              maxLength={100}
              autoFocus
            />
          </div>
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Description</label>
            <Input
              type="text"
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" onClick={handleCloseModals} className="bg-gray-300">
              Cancel
            </Button>
            <Button type="submit" className="bg-blue-500 text-white">
              Create
            </Button>
          </div>
        </form>
      </Modal>

      {/* Модальное окно редактирования проекта */}
      <Modal isOpen={isEditOpen} onClose={handleCloseModals} title="Edit Project">
        <form onSubmit={handleUpdate}>
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Project Name *</label>
            <Input
              type="text"
              value={editProjectName}
              onChange={(e) => setEditProjectName(e.target.value)}
              required
              maxLength={100}
              autoFocus
            />
          </div>
          <div className="mb-3">
            <label className="block text-sm font-medium mb-1">Description</label>
            <Input
              type="text"
              value={editProjectDescription}
              onChange={(e) => setEditProjectDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" onClick={handleCloseModals} className="bg-gray-300">
              Cancel
            </Button>
            <Button type="submit" className="bg-blue-500 text-white">
              Save
            </Button>
          </div>
        </form>
      </Modal>

      {/* Модальное окно подтверждения удаления */}
      <Modal isOpen={isDeleteOpen} onClose={handleCloseModals} title="Delete Project">
        <p className="mb-4">
          Are you sure you want to delete project "{deletingProject?.name}"? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button onClick={handleCloseModals} className="bg-gray-300">
            Cancel
          </Button>
          <Button onClick={handleDelete} className="bg-red-500 text-white">
            Delete
          </Button>
        </div>
      </Modal>
    </aside>
  );
};
