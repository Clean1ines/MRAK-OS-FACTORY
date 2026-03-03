import React, { useState, useEffect, useCallback } from 'react';
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
import { WorkspaceSidebar } from './components/WorkspaceSidebar';
import { useNodeOperations } from './hooks/useNodeOperations';
import { useEdgeOperations } from './hooks/useEdgeOperations';

export const WorkspacePage: React.FC = () => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [userClosedSidebar, setUserClosedSidebar] = useState(false);

  const { projects } = useProjects();
  const { selectedProjectId } = useSelectedProject(projects);
  const data = useWorkflowsData(selectedProjectId);
  const ui = useWorkflowUI();
  const canvas = useWorkflowCanvas();

  const nodeOps = useNodeOperations(data, canvas, ui);
  const edgeOps = useEdgeOperations(data, canvas, ui);

  // Загрузка деталей текущего воркфлоу
  const { data: workflowDetail } = useQuery<WorkflowDetail>({
    queryKey: ['workflow', ui.currentWorkflowId],
    queryFn: () => workflowApi.get(ui.currentWorkflowId!).then(res => res.data as WorkflowDetail),
    enabled: !!ui.currentWorkflowId,
  });

  // Синхронизация деталей с канвасом и UI-именами
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
            onAddCustomNode={nodeOps.handleAddCustomNode}
            onEditNode={(recordId, promptKey, config) => nodeOps.setEditingNode({ recordId, promptKey, config })}
            onRequestDeleteNode={nodeOps.handleRequestDeleteNode}
            onStartConnection={edgeOps.handleStartConnection}
            onCompleteConnection={edgeOps.handleCompleteConnection}
            onRequestDeleteEdge={edgeOps.handleRequestDeleteEdge}
          />
        </div>

        <NodeListPanel
          visible={canvas.showNodeList}
          onClose={() => canvas.setShowNodeList(false)}
          nodes={canvas.nodes}
          onAddNode={nodeOps.handleAddNodeFromList}
          onUpdateNode={nodeOps.handleUpdateNode}
          onDeleteNode={(recordId, nodeId) => {
            const node = canvas.nodes.find(n => n.node_id === nodeId);
            if (node) {
              nodeOps.handleRequestDeleteNode(recordId, nodeId, node.prompt_key);
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
          onConfirm={nodeOps.handleConfirmAddCustomNode}
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
          isOpen={!!nodeOps.editingNode}
          onClose={() => nodeOps.setEditingNode(null)}
          initialPromptKey={nodeOps.editingNode?.promptKey || ''}
          initialConfig={nodeOps.editingNode?.config || {}}
          onSave={async (promptKey, config) => {
            if (nodeOps.editingNode) {
              await nodeOps.handleUpdateNode(nodeOps.editingNode.recordId, promptKey, config);
              nodeOps.setEditingNode(null);
            }
          }}
          isSaving={data.updateNode.isPending}
        />

        <DeleteConfirmModal
          isOpen={!!nodeOps.deletingNode}
          onClose={() => nodeOps.setDeletingNode(null)}
          onConfirm={nodeOps.confirmDeleteNode}
          itemName={nodeOps.deletingNode?.name || ''}
          itemType="node"
          isPending={data.deleteNode.isPending}
        />

        <DeleteConfirmModal
          isOpen={!!edgeOps.deletingEdge}
          onClose={() => edgeOps.setDeletingEdge(null)}
          onConfirm={edgeOps.confirmDeleteEdge}
          itemName={`edge between ${edgeOps.deletingEdge?.sourceNode.substring(0,6)} and ${edgeOps.deletingEdge?.targetNode.substring(0,6)}`}
          itemType="edge"
          isPending={data.deleteEdge.isPending}
        />
      </div>
    </IOSShell>
  );
};
