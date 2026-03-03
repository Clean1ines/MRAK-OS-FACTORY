import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';
import { useQuery } from '@tanstack/react-query';
import { api } from '@shared/api';
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
import { useProjects } from '@/entities/project/api/useProjects';

// Новые хуки
import { useWorkflowsData, WorkflowDetail } from '@/entities/workflow/api/useWorkflowsData';
import { useWorkflowUI } from '@/features/workflow/model/useWorkflowUI';
import { useWorkflowCanvas } from '@/widgets/workflow-editor/lib/useWorkflowCanvas';
import { workflowApi } from '@/entities/workflow/api/workflowApi';
import { NodeData } from '@shared/lib';
import { WorkspaceSidebar } from './components/WorkspaceSidebar';

export const WorkspacePage: React.FC = () => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [userClosedSidebar, setUserClosedSidebar] = useState(false);

  const { projects } = useProjects();
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

  const handleLogout = useCallback(async () => {
    try {
      await api.auth.logout();
      window.location.href = '/login';
    } catch (e) {
      console.error(e);
    }
  }, []);

  return (
    <IOSShell>
      <div className="flex h-full">
        {!sidebarOpen && (
          <HamburgerMenu onOpenSidebar={handleOpenSidebar} showHomeIcon={true} />
        )}

        <WorkspaceSidebar
          isMobile={isMobile}
          sidebarOpen={sidebarOpen}
          onCloseSidebar={handleCloseSidebar}
          onOpenSidebar={handleOpenSidebar}
          selectedProjectId={selectedProjectId}
          currentProjectName={currentProject?.name || ''}
          workflows={data.workflows}
          currentWorkflowId={ui.currentWorkflowId}
          onSelectWorkflow={ui.setCurrentWorkflowId}
          onEditWorkflow={(wf) => ui.openEditModal({ id: wf.id!, name: wf.name, description: wf.description || '' })}
          onDeleteWorkflow={ui.openDeleteModal}
          onCreateWorkflow={() => ui.setShowCreateModal(true)}
          onOpenNodeList={() => canvas.setShowNodeList(true)}
          onLogout={handleLogout}
        />

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
          onAddNode={handleAddNodeFromList}
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
