import { useState, useCallback } from 'react';

export const useWorkflowUI = () => {
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<{ id: string; name: string; description: string } | null>(null);
  const [deletingWorkflow, setDeletingWorkflow] = useState<{ id: string; name: string } | null>(null);

  const openEditModal = useCallback((wf: { id: string; name: string; description: string }) => {
    setEditingWorkflow(wf);
  }, []);

  const closeEditModal = useCallback(() => {
    setEditingWorkflow(null);
  }, []);

  const openDeleteModal = useCallback((wf: { id: string; name: string }) => {
    setDeletingWorkflow(wf);
  }, []);

  const closeDeleteModal = useCallback(() => {
    setDeletingWorkflow(null);
  }, []);

  return {
    currentWorkflowId,
    setCurrentWorkflowId,
    workflowName,
    setWorkflowName,
    workflowDescription,
    setWorkflowDescription,
    showCreateModal,
    setShowCreateModal,
    editingWorkflow,
    openEditModal,
    closeEditModal,
    deletingWorkflow,
    openDeleteModal,
    closeDeleteModal,
  };
};
