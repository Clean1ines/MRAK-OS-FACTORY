import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { useQuery } from '@tanstack/react-query';
import { api, ProjectResponse } from '@shared/api';
import { IOSShell } from '@/widgets/workflow-shell/ui/IOSShell';
import { IOSCanvas } from '@/widgets/workflow-editor/ui/IOSCanvas';
import { NodeListPanel } from '@/widgets/node-picker/ui/NodeListPanel';
import { NodeModal } from '@/features/node/view-details/ui/NodeModal';
import { useMediaQuery } from '@/shared/lib/hooks/useMediaQuery';
import { HamburgerMenu } from '@/widgets/header/ui/HamburgerMenu';
import { useSelectedProject } from '@/entities/project/api/useSelectedProject';
import { CreateWorkflowModal } from '@/features/workflow/create/ui/CreateWorkflowModal';
import { EditWorkflowModal } from '@/features/workflow/edit/ui/EditWorkflowModal';
import { DeleteConfirmModal } from '@shared/ui';
import { EditNodeModal } from '@/features/node/edit-content/ui/EditNodeModal';
import { SIDEBAR_HAMBURGER_WIDTH } from '@/shared/lib/constants/canvas';

// Новые хуки
import { useWorkflowsData, WorkflowDetail } from '@/entities/workflow/api/useWorkflowsData';
import { useWorkflowUI } from '@/features/workflow/model/useWorkflowUI';
import { useWorkflowCanvas } from '@/widgets/workflow-editor/lib/useWorkflowCanvas';
import { workflowApi } from '@/entities/workflow/api/workflowApi';

import { NodeData } from '@shared/lib';

export const WorkspacePage: React.FC = () => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [userClosedSidebar, setUserClosedSidebar] = useState(false);

  const { selectedProjectId } = useSelectedProject(projects);
  const data = useWorkflowsData(selectedProjectId);
  const ui = useWorkflowUI();
  const canvas = useWorkflowCanvas();

  // Загрузка деталей текущего воркфлоу
  const { data: workflowDetail } = useQuery<WorkflowDetail>({
    queryKey: ['workflow', ui.currentWorkflowId],
    queryFn: () => workflowApi.get(ui.currentWorkflowId!).then(res => res.data as WorkflowDetail),
    enabled: !!ui.currentWorkflowId,
  });

  // Синхронизация деталей с канвасом и UI-именами
  useEffect(() => {
    if (workflowDetail) {
      const nodes = (workflowDetail.nodes || []).map((n) => ({
        id: crypto.randomUUID(),
        node_id: n.node_id!,
        prompt_key: n.prompt_key || 'UNKNOWN',
        position_x: n.position_x || 100,
        position_y: n.position_y || 100,
        config: n.config || {},
        recordId: n.id,
      }));
      const edges = (workflowDetail.edges || []).map((e) => ({
        id: e.id || crypto.randomUUID(),
        source_node: e.source_node!,
        target_node: e.target_node!,
      }));
      canvas.setNodes(nodes);
      canvas.setEdges(edges);
      ui.setWorkflowName(workflowDetail.workflow?.name || '');
      ui.setWorkflowDescription(workflowDetail.workflow?.description || '');
    } else {
      canvas.setNodes([]);
      canvas.setEdges([]);
      ui.setWorkflowName('');
      ui.setWorkflowDescription('');
    }
  }, [workflowDetail]);

  const [editingNode, setEditingNode] = useState<{ recordId: string; promptKey: string; config: Record<string, unknown> } | null>(null);
  const [deletingNode, setDeletingNode] = useState<{ recordId?: string; nodeId: string; name: string } | null>(null);
  const [deletingEdge, setDeletingEdge] = useState<{ edgeId: string; sourceNode: string; targetNode: string } | null>(null);

  const sidebarOpen = !isMobile && !userClosedSidebar;

  const handleCloseSidebar = () => setUserClosedSidebar(true);
  const handleOpenSidebar = () => setUserClosedSidebar(false);

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const { data, error } = await api.projects.list();
        if (error) {
          console.error('Failed to load projects:', error);
          return;
        }
        if (data && Array.isArray(data)) {
          setProjects(data);
        } else {
          setProjects([]);
        }
      } catch (e) {
        console.error('Error loading projects:', e);
      }
    };
    loadProjects();
  }, []);

  const currentProject = projects.find(p => p.id === selectedProjectId);

  const handleCreateWorkflow = useCallback(async (name: string, description: string): Promise<void> => {
    if (!name.trim() || !selectedProjectId) return;
    try {
      await data.createWorkflow.mutateAsync({ name, description, projectId: selectedProjectId });
      ui.setShowCreateModal(false);
    } catch {
      // ошибка уже обработана в мутации
    }
  }, [data, selectedProjectId, ui]);

  const handleDeleteWorkflow = useCallback(async (id: string): Promise<void> => {
    try {
      await data.deleteWorkflow.mutateAsync(id);
      ui.closeDeleteModal();
    } catch {
      // ошибка уже обработана
    }
  }, [data, ui]);

  const handleAddCustomNode = useCallback((x: number, y: number) => {
    canvas.handleAddCustomNode(x, y);
  }, [canvas]);

  const handleConfirmAddCustomNode = useCallback(async () => {
    const newNode = await canvas.confirmAddCustomNode();
    if (!newNode || !ui.currentWorkflowId) return;
    try {
      const result = await data.createNode.mutateAsync({
        workflowId: ui.currentWorkflowId,
        nodeId: newNode.node_id,
        promptKey: newNode.prompt_key,
        config: newNode.config || {},
        positionX: newNode.position_x,
        positionY: newNode.position_y,
      });
      // Обновляем recordId в локальном узле
      canvas.setNodes(prev =>
        prev.map(n => (n.node_id === newNode.node_id ? { ...n, recordId: result.id } : n))
      );
    } catch (err) {
      console.error('Failed to create node:', err);
    }
  }, [canvas, data, ui.currentWorkflowId]);

  // Обработчик добавления узла из списка (с сохранением на сервере)
  const handleAddNodeFromList = useCallback(async (node: NodeData) => {
    if (!ui.currentWorkflowId) return;
    // Сначала добавляем локально для мгновенного UI
    canvas.addNodeFromList(node);
    try {
      const result = await data.createNode.mutateAsync({
        workflowId: ui.currentWorkflowId,
        nodeId: node.node_id,
        promptKey: node.prompt_key,
        config: node.config || {},
        positionX: node.position_x,
        positionY: node.position_y,
      });
      // Обновляем recordId после успешного создания на сервере
      canvas.setNodes(prev =>
        prev.map(n => (n.node_id === node.node_id ? { ...n, recordId: result.id } : n))
      );
    } catch (err) {
      console.error('Failed to create node from list:', err);
      // Можно откатить локальное добавление, но для простоты оставим как есть
      // (пользователь увидит ошибку и узел останется без recordId)
    }
  }, [canvas, data, ui.currentWorkflowId]);

  const handleUpdateNode = useCallback(async (recordId: string, promptKey: string, config: Record<string, unknown>) => {
    try {
      await data.updateNode.mutateAsync({ recordId, prompt_key: promptKey, config });
    } catch (err) {
      console.error('Failed to update node:', err);
    }
  }, [data]);

  const handleDeleteNode = useCallback(async (recordId: string) => {
    try {
      await data.deleteNode.mutateAsync(recordId);
      canvas.setNodes(prev => prev.filter(n => n.recordId !== recordId));
      canvas.setEdges(prev => prev.filter(e => e.source_node !== recordId && e.target_node !== recordId));
    } catch (err) {
      console.error('Failed to delete node:', err);
    }
  }, [data, canvas]);

  const handleStartConnection = useCallback((nodeId: string) => {
    canvas.handleStartConnection(nodeId);
  }, [canvas]);

  const handleCompleteConnection = useCallback(async (targetNodeId: string) => {
    const sourceNodeId = canvas.connectingNode;
    if (!sourceNodeId || !ui.currentWorkflowId) return;

    // Проверяем, что исходный узел уже сохранён на сервере (имеет recordId)
    const sourceNode = canvas.nodes.find(n => n.node_id === sourceNodeId);
    if (!sourceNode) {
      toast.error('Source node not found');
      return;
    }
    // Если у узла нет recordId, значит он ещё не сохранён – ждём или просим подождать
    if (!sourceNode.recordId) {
      toast.error('Please wait for node to be saved before connecting');
      return;
    }

    try {
      await data.createEdge.mutateAsync({
        workflowId: ui.currentWorkflowId,
        sourceNode: sourceNodeId,
        targetNode: targetNodeId,
      });
      canvas.handleCompleteConnection(targetNodeId);
    } catch (err) {
      console.error('Failed to create edge:', err);
    }
  }, [canvas, data, ui.currentWorkflowId]);

  const handleDeleteEdge = useCallback(async (edgeId: string) => {
    try {
      await data.deleteEdge.mutateAsync(edgeId);
      canvas.setEdges(prev => prev.filter(e => e.id !== edgeId));
    } catch (err) {
      console.error('Failed to delete edge:', err);
    }
  }, [data, canvas]);

  const handleRequestDeleteNode = (recordId: string | undefined, nodeId: string, name: string) => {
    setDeletingNode({ recordId, nodeId, name });
  };

  const confirmDeleteNode = async () => {
    if (!deletingNode) return;
    if (deletingNode.recordId) {
      await handleDeleteNode(deletingNode.recordId);
    } else {
      canvas.setNodes(prev => prev.filter(n => n.node_id !== deletingNode.nodeId));
      canvas.setEdges(prev => prev.filter(e => e.source_node !== deletingNode.nodeId && e.target_node !== deletingNode.nodeId));
      toast.success('Node removed');
    }
    setDeletingNode(null);
  };

  const handleRequestDeleteEdge = (edgeId: string, sourceNode: string, targetNode: string) => {
    setDeletingEdge({ edgeId, sourceNode, targetNode });
  };

  const confirmDeleteEdge = async () => {
    if (!deletingEdge) return;
    await handleDeleteEdge(deletingEdge.edgeId);
    setDeletingEdge(null);
  };

  return (
    <IOSShell>
      <div className="flex h-full">
        {!sidebarOpen && (
          <HamburgerMenu onOpenSidebar={handleOpenSidebar} showHomeIcon={true} />
        )}

        {sidebarOpen && (
          <aside
            className={`${
              isMobile ? 'fixed top-0 left-0 h-full z-50 shadow-2xl' : 'w-64'
            } bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col`}
            data-testid="sidebar"
          >
            <div className="flex justify-end p-2">
              <button
                onClick={handleCloseSidebar}
                className="p-1 text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors"
                aria-label="Close sidebar"
                data-testid="close-sidebar"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="p-3 border-b border-[var(--ios-border)]">
              <label className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider block mb-1">
                Current Project
              </label>
              <div className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-2 py-1.5 text-xs text-[var(--text-main)]">
                {currentProject?.name || '—'}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {!selectedProjectId ? (
                <div className="text-[10px] text-[var(--accent-warning)] text-center py-4">
                  ⚠️ Select project on home page
                </div>
              ) : data.workflows.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] text-center py-4">
                  No workflows
                </div>
              ) : (
                data.workflows.map((wf) => (
                  <div
                    key={wf.id}
                    className={`w-full text-left px-3 py-2 rounded mb-1 text-xs flex items-center justify-between cursor-pointer ${
                      ui.currentWorkflowId === wf.id
                        ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'
                    }`}
                    onClick={() => ui.setCurrentWorkflowId(wf.id!)}
                    data-testid="workflow-item"
                  >
                    <div className="flex-1">
                      <div className="font-semibold truncate">{wf.name}</div>
                      <div className="text-[9px] opacity-60 truncate">
                        {wf.description || 'No description'}
                      </div>
                    </div>
                    <div className="flex gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => ui.openEditModal({ id: wf.id!, name: wf.name, description: wf.description || '' })}
                        className="text-[var(--text-muted)] hover:text-[var(--bronze-base)] transition-colors p-1"
                        title="Edit workflow"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M17 3L21 7L7 21H3V17L17 3Z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => ui.openDeleteModal(wf)}
                        className="text-[var(--text-muted)] hover:text-[var(--accent-danger)] transition-colors p-1"
                        title="Delete workflow"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M3 6H21M19 6V20C19 21.1046 18.1046 22 17 22H7C5.89543 22 5 21.1046 5 20V6M8 6V4C8 2.89543 8.89543 2 10 2H14C15.1046 2 16 2.89543 16 4V6" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="p-3 border-t border-[var(--ios-border)] space-y-2">
              <button
                onClick={() => ui.setShowCreateModal(true)}
                disabled={!selectedProjectId}
                className="w-full px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors flex items-center justify-center gap-2 disabled:opacity-30"
                data-testid="new-workflow-button"
              >
                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                New Workflow
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => canvas.setShowNodeList(true)}
                  disabled={!selectedProjectId}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                  data-testid="nodes-button"
                >
                  Nodes
                </button>
                <button
                  onClick={async () => {
                    try {
                      await api.auth.logout();
                      window.location.href = '/login';
                    } catch (e) {
                      console.error(e);
                    }
                  }}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors"
                  data-testid="logout-button"
                >
                  Logout
                </button>
              </div>

              <div className="text-[9px] text-[var(--text-muted)] text-center pt-2">
                {data.workflows.length} workflow{data.workflows.length !== 1 ? 's' : ''}
              </div>
            </div>
          </aside>
        )}

        <div className="flex-1 flex flex-col">
          <div className="h-12 flex items-center border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <div style={{ width: !sidebarOpen ? SIDEBAR_HAMBURGER_WIDTH : 0 }} className="transition-all" />
            <div className="flex-1 flex justify-center items-center">
              <h2 className="text-sm font-semibold text-[var(--text-main)]">
                {ui.workflowName || 'Untitled Workflow'}
              </h2>
            </div>
            <div style={{ width: !sidebarOpen ? SIDEBAR_HAMBURGER_WIDTH : 0 }} className="transition-all" />
          </div>
          <IOSCanvas
            nodes={canvas.nodes}
            edges={canvas.edges}
            onNodesChange={canvas.setNodes}
            onEdgesChange={canvas.setEdges}
            onAddCustomNode={handleAddCustomNode}
            onEditNode={(recordId, promptKey, config) => setEditingNode({ recordId, promptKey, config })}
            onRequestDeleteNode={handleRequestDeleteNode}
            onStartConnection={handleStartConnection}
            onCompleteConnection={handleCompleteConnection}
            onRequestDeleteEdge={handleRequestDeleteEdge}
          />
        </div>

        <NodeListPanel
          visible={canvas.showNodeList}
          onClose={() => canvas.setShowNodeList(false)}
          nodes={canvas.nodes}
          onAddNode={handleAddNodeFromList}  // ← используем обёртку с сохранением
          onUpdateNode={handleUpdateNode}
          onDeleteNode={(recordId, nodeId) => {
            const node = canvas.nodes.find(n => n.node_id === nodeId);
            if (node) {
              handleRequestDeleteNode(recordId, nodeId, node.prompt_key);
            }
          }}
          currentWorkflowId={ui.currentWorkflowId}
        />

        <NodeModal
          visible={canvas.showNodeModal}
          onClose={() => canvas.setShowNodeModal(false)}
          title={canvas.newNodeTitle}
          onTitleChange={canvas.setNewNodeTitle}
          prompt={canvas.newNodePrompt}
          onPromptChange={canvas.setNewNodePrompt}
          onConfirm={handleConfirmAddCustomNode}
          validationError={
            canvas.newNodeTitle.trim()
              ? canvas.validateNodeUnique(canvas.newNodeTitle.trim(), canvas.newNodePrompt)
              : null
          }
        />

        <CreateWorkflowModal
          isOpen={ui.showCreateModal}
          onClose={() => ui.setShowCreateModal(false)}
          onCreate={handleCreateWorkflow}
          isPending={data.createWorkflow.isPending}
        />

        <EditWorkflowModal
          isOpen={!!ui.editingWorkflow}
          onClose={ui.closeEditModal}
          initialName={ui.editingWorkflow?.name || ''}
          initialDescription={ui.editingWorkflow?.description || ''}
          onSave={async (name, description) => {
            if (ui.editingWorkflow) {
              await data.updateWorkflow.mutateAsync({
                id: ui.editingWorkflow.id,
                name,
                description,
              });
              ui.closeEditModal();
            }
          }}
          isSaving={data.updateWorkflow.isPending}
        />

        <DeleteConfirmModal
          isOpen={!!ui.deletingWorkflow}
          onClose={ui.closeDeleteModal}
          onConfirm={() => handleDeleteWorkflow(ui.deletingWorkflow!.id)}
          itemName={ui.deletingWorkflow?.name || ''}
          itemType="workflow"
          isPending={data.deleteWorkflow.isPending}
        />

        <EditNodeModal
          isOpen={!!editingNode}
          onClose={() => setEditingNode(null)}
          initialPromptKey={editingNode?.promptKey || ''}
          initialConfig={editingNode?.config || {}}
          onSave={async (promptKey, config) => {
            if (editingNode) {
              await handleUpdateNode(editingNode.recordId, promptKey, config);
              setEditingNode(null);
            }
          }}
          isSaving={data.updateNode.isPending}
        />

        <DeleteConfirmModal
          isOpen={!!deletingNode}
          onClose={() => setDeletingNode(null)}
          onConfirm={confirmDeleteNode}
          itemName={deletingNode?.name || ''}
          itemType="node"
          isPending={data.deleteNode.isPending}
        />

        <DeleteConfirmModal
          isOpen={!!deletingEdge}
          onClose={() => setDeletingEdge(null)}
          onConfirm={confirmDeleteEdge}
          itemName={`edge between ${deletingEdge?.sourceNode.substring(0,6)} and ${deletingEdge?.targetNode.substring(0,6)}`}
          itemType="edge"
          isPending={data.deleteEdge.isPending}
        />
      </div>
    </IOSShell>
  );
};
