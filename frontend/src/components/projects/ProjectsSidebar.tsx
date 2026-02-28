import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore, Project } from '../../store/useAppStore';
import { useProjects } from '../../hooks/useProjects';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { HamburgerMenu } from '../layout/HamburgerMenu';

const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ className, ...props }) => (
  <button
    {...props}
    className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${className || ''}`}
  />
);

const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = ({ className, ...props }) => (
  <input
    {...props}
    className={`w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)] transition-colors ${className || ''}`}
  />
);

const Modal: React.FC<{ isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode }> = ({
  isOpen,
  onClose,
  title,
  children,
}) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 backdrop-blur-[2px]">
      <div className="w-full max-w-md bg-[var(--ios-glass-dark)] backdrop-blur-[var(--blur-std)] border border-[var(--ios-border)] rounded-2xl shadow-[var(--shadow-heavy)] p-6">
        <h2 className="text-xl font-bold text-[var(--bronze-base)] mb-4">{title}</h2>
        {children}
        <div className="flex justify-end gap-2 mt-6">
          <Button onClick={onClose} className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] text-[var(--text-main)] hover:bg-[var(--ios-glass-bright)]">
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
};

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

  const isMobile = useMediaQuery('(max-width: 768px)');
  const [isSidebarOpen, setIsSidebarOpen] = useState(!isMobile);

  // Синхронизируем состояние при изменении размера экрана
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsSidebarOpen(!isMobile);
    
  }, [isMobile]);

  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [editProjectName, setEditProjectName] = useState('');
  const [editProjectDescription, setEditProjectDescription] = useState('');

  const handleOpenCreate = () => {
    setNewProjectName('');
    setNewProjectDescription('');
    originalOpenCreateModal();
  };

  const handleOpenEdit = (project: Project) => {
    setEditProjectName(project.name);
    setEditProjectDescription(project.description);
    originalOpenEditModal(project);
  };

  const handleCloseModals = () => {
    originalCloseModals();
    setNewProjectName('');
    setNewProjectDescription('');
    setEditProjectName('');
    setEditProjectDescription('');
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await createProject({
      name: newProjectName,
      description: newProjectDescription,
    });
    if (success) {
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
      setEditProjectName('');
      setEditProjectDescription('');
    }
  };

  const handleDelete = async () => {
    if (!deletingProject) return;
    await deleteProject(deletingProject.id);
  };

  const handleProjectClick = (projectId: string) => {
    setCurrentProjectId(projectId);
    navigate(`/workspace?projectId=${projectId}`);
  };

  const handleCloseSidebar = () => setIsSidebarOpen(false);
  const handleOpenSidebar = () => setIsSidebarOpen(true);

  if (!isSidebarOpen) {
    return <HamburgerMenu onOpenSidebar={handleOpenSidebar} showHomeIcon={false} />;
  }

  const sidebarClasses = isMobile
    ? 'fixed top-0 left-0 h-full z-50 shadow-2xl'
    : 'w-64 h-full';

  return (
    <aside className={`${sidebarClasses} bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col text-[var(--text-main)]`}>
      {/* Кнопка закрытия панели */}
      <div className="flex justify-end p-2">
        <button
          onClick={handleCloseSidebar}
          className="p-1 text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors"
          aria-label="Close sidebar"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="p-4 border-b border-[var(--ios-border)]">
        <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
          Current Project
        </label>
        <select
          value={currentProjectId || ''}
          onChange={(e) => setCurrentProjectId(e.target.value || null)}
          className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
        >
          <option value="" disabled>Select a project</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {projects.map((project) => (
          <div
            key={project.id}
            className={`p-2 rounded cursor-pointer flex items-center justify-between transition-colors ${
              currentProjectId === project.id
                ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]'
                : 'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'
            }`}
            onClick={() => handleProjectClick(project.id)}
          >
            <span className="truncate flex-1 text-sm">{project.name}</span>
            <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => handleOpenEdit(project)}
                className="text-[var(--text-muted)] hover:text-[var(--bronze-base)] transition-colors p-1"
                title="Edit"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 3L21 7L7 21H3V17L17 3Z" />
                </svg>
              </button>
              <button
                onClick={() => openDeleteConfirm(project)}
                className="text-[var(--text-muted)] hover:text-[var(--accent-danger)] transition-colors p-1"
                title="Delete"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6H21M19 6V20C19 21.1046 18.1046 22 17 22H7C5.89543 22 5 21.1046 5 20V6M8 6V4C8 2.89543 8.89543 2 10 2H14C15.1046 2 16 2.89543 16 4V6" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-[var(--ios-border)] space-y-2">
        <Button
          onClick={handleOpenCreate}
          className="w-full bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black"
        >
          + New Project
        </Button>
        <div className="text-xs text-[var(--text-muted)] text-center">
          {projects.length} {projects.length === 1 ? 'project' : 'projects'}
        </div>
      </div>

      {/* Модальные окна */}
      <Modal isOpen={isCreateOpen} onClose={handleCloseModals} title="Create New Project">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
              Project Name *
            </label>
            <Input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              required
              maxLength={100}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
              Description
            </label>
            <Input
              type="text"
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" onClick={handleCloseModals} className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] text-[var(--text-main)] hover:bg-[var(--ios-glass-bright)]">
              Cancel
            </Button>
            <Button type="submit" className="bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)]">
              Create
            </Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={isEditOpen} onClose={handleCloseModals} title="Edit Project">
        <form onSubmit={handleUpdate} className="space-y-4">
          <div>
            <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
              Project Name *
            </label>
            <Input
              type="text"
              value={editProjectName}
              onChange={(e) => setEditProjectName(e.target.value)}
              required
              maxLength={100}
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
              Description
            </label>
            <Input
              type="text"
              value={editProjectDescription}
              onChange={(e) => setEditProjectDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" onClick={handleCloseModals} className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] text-[var(--text-main)] hover:bg-[var(--ios-glass-bright)]">
              Cancel
            </Button>
            <Button type="submit" className="bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)]">
              Save
            </Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={isDeleteOpen} onClose={handleCloseModals} title="Delete Project">
        <p className="text-[var(--text-main)] mb-4">
          Are you sure you want to delete project <span className="font-semibold text-[var(--bronze-base)]">"{deletingProject?.name}"</span>? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <Button onClick={handleCloseModals} className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] text-[var(--text-main)] hover:bg-[var(--ios-glass-bright)]">
            Cancel
          </Button>
          <Button onClick={handleDelete} className="bg-[var(--accent-danger)] text-white hover:bg-[#ff6961]">
            Delete
          </Button>
        </div>
      </Modal>
    </aside>
  );
};
