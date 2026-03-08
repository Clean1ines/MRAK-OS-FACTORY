import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
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
import { useWorkflowStore } from '@/entities/workflow/store/workflowStore';
import { useLoadWorkflow } from '@/entities/workflow/store/useLoadWorkflow';
import { WorkspaceSidebar } from './components/WorkspaceSidebar';

interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
}

export const WorkspacePage: React.FC = () => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [userClosedSidebar, setUserClosedSidebar] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const workflowIdFromUrl = searchParams.get('workflowId');

  const { projects } = useProjects();
  const { selectedProjectId } = useSelectedProject(projects);
  const store = useWorkflowStore();
  const { workflows, currentWorkflowId } = store.ui;

  const { data: workflowsList, isLoading: isLoadingWorkflows } = useQuery({
    queryKey: ['workflows', selectedProjectId],
    queryFn: async () => {
      console.log('[WorkspacePage] fetching workflows for project', selectedProjectId);
      if (!selectedProjectId) return [];
      const { data } = await api.workflows.list(selectedProjectId);
      console.log('[WorkspacePage] workflows loaded:', (data as WorkflowSummary[] | undefined)?.length);
      return (data as WorkflowSummary[]) || [];
    },
    enabled: !!selectedProjectId,
  });

  useEffect(() => {
    if (workflowsList) {
      console.log('[WorkspacePage] setting workflows to store, count:', workflowsList.length);
      useWorkflowStore.getState().setWorkflows(workflowsList);
    }
  }, [workflowsList]);

  const { isLoading: isLoadingWorkflow } = useLoadWorkflow(workflowIdFromUrl);

  useEffect(() => {
    console.log('[WorkspacePage] URL workflowId:', workflowIdFromUrl, 'store currentWorkflowId:', currentWorkflowId);
    if (workflowIdFromUrl && workflowIdFromUrl !== currentWorkflowId) {
      console.log('[WorkspacePage] setting store workflow from URL to', workflowIdFromUrl);
      store.selectWorkflow(workflowIdFromUrl);
    }
  }, [workflowIdFromUrl, currentWorkflowId, store]);

  useEffect(() => {
    if (workflows.length > 0 && !currentWorkflowId && !workflowIdFromUrl) {
      const firstId = workflows[0].id;
      console.log('[WorkspacePage] no workflow selected, selecting first:', firstId);
      store.selectWorkflow(firstId);
      setSearchParams({ projectId: selectedProjectId || '', workflowId: firstId });
    }
  }, [workflows, currentWorkflowId, workflowIdFromUrl, selectedProjectId, store, setSearchParams]);

  const handleSelectWorkflow = useCallback((id: string) => {
    console.log('[WorkspacePage] handleSelectWorkflow:', id);
    store.selectWorkflow(id);
    setSearchParams({ projectId: selectedProjectId || '', workflowId: id });
  }, [store, selectedProjectId, setSearchParams]);

  const sidebarOpen = !isMobile && !userClosedSidebar;
  const handleCloseSidebar = () => setUserClosedSidebar(true);
  const handleOpenSidebar = () => setUserClosedSidebar(false);

  const currentProject = projects.find(p => p.id === selectedProjectId);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<{ id: string; name: string; description: string } | null>(null);
  const [deletingWorkflow, setDeletingWorkflow] = useState<{ id: string; name: string } | null>(null);
  const [showNodeList, setShowNodeList] = useState(false);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [editingNode, setEditingNode] = useState<{ id: string; promptKey: string; config: Record<string, unknown> } | null>(null);
  const [deletingNode, setDeletingNode] = useState<{ id: string; name: string } | null>(null);
  const [deletingEdge, setDeletingEdge] = useState<{ edgeId: string; source: string; target: string } | null>(null);

  const [nodeTitle, setNodeTitle] = useState('');
  const [nodePrompt, setNodePrompt] = useState('');
  const [nodePosition, setNodePosition] = useState<{ x: number; y: number } | null>(null);

  const handleCreateWorkflow = useCallback(async (name: string, description: string) => {
    console.log('[WorkspacePage] handleCreateWorkflow', { name, description, projectId: selectedProjectId });
    if (!name.trim() || !selectedProjectId) return;
    try {
      const { data } = await api.workflows.create({
        name,
        description,
        project_id: selectedProjectId,
        is_default: false,
      });
      if (data) {
        console.log('[WorkspacePage] workflow created:', data);
        store.setWorkflows([...workflows, { id: (data as { id: string }).id, name, description }]);
        setShowCreateModal(false);
      }
    } catch (error) {
      console.error(error);
    }
  }, [selectedProjectId, workflows, store]);

  const handleUpdateWorkflow = useCallback(async (id: string, name: string, description: string) => {
    console.log('[WorkspacePage] handleUpdateWorkflow', { id, name, description });
    try {
      await api.workflows.update(id, { name, description });
      store.setWorkflows(workflows.map(w => w.id === id ? { ...w, name, description } : w));
      setEditingWorkflow(null);
    } catch (error) {
      console.error(error);
    }
  }, [workflows, store]);

  const handleDeleteWorkflow = useCallback(async (id: string) => {
    console.log('[WorkspacePage] handleDeleteWorkflow', id);
    try {
      await api.workflows.delete(id);
      store.setWorkflows(workflows.filter(w => w.id !== id));
      if (currentWorkflowId === id) {
        store.selectWorkflow(null);
      }
      setDeletingWorkflow(null);
    } catch (error) {
      console.error(error);
    }
  }, [workflows, store, currentWorkflowId]);

  const handleLogout = useCallback(async () => {
    try {
      await api.auth.logout();
      window.location.href = '/login';
    } catch (e) {
      console.error(e);
    }
  }, []);

  const handleOpenCreateModal = useCallback((x: number, y: number) => {
    console.log('[WorkspacePage] open create modal at', { x, y });
    setNodeTitle('');
    setNodePrompt('');
    setNodePosition({ x, y });
    setShowNodeModal(true);
  }, []);

  const handleCreateNode = useCallback(() => {
    console.log('[WorkspacePage] handleCreateNode, currentWorkflowId:', currentWorkflowId);
    if (!currentWorkflowId) {
      console.warn('Cannot create node: no workflow selected');
      return;
    }
    const title = nodeTitle.trim() || 'New Node';
    const position = nodePosition || { x: 100, y: 100 };
    console.log('[WorkspacePage] creating node with title:', title, 'position:', position);
    store.addNode(
      { type: 'prompt', promptKey: title, config: { custom_prompt: nodePrompt } },
      position
    );
    setShowNodeModal(false);
    setNodePosition(null);
  }, [currentWorkflowId, nodeTitle, nodePrompt, nodePosition, store]);

  const handleOpenEditModal = useCallback((nodeId: string) => {
    console.log('[WorkspacePage] open edit modal for node:', nodeId);
    const node = store.graph.nodes.find(n => n.id === nodeId);
    if (node) {
      setEditingNode({ id: node.id, promptKey: node.promptKey, config: node.config });
    }
  }, [store.graph.nodes]);

  const handleRequestDeleteNode = useCallback((nodeId: string) => {
    const node = store.graph.nodes.find(n => n.id === nodeId);
    if (node) {
      setDeletingNode({ id: node.id, name: node.promptKey });
    }
  }, [store.graph.nodes]);

  const handleRequestDeleteEdge = useCallback((edgeId: string) => {
    const edge = store.graph.edges.find(e => e.id === edgeId);
    if (edge) {
      setDeletingEdge({ edgeId, source: edge.source, target: edge.target });
    }
  }, [store.graph.edges]);

  if (isLoadingWorkflows || isLoadingWorkflow) {
    console.log('[WorkspacePage] loading...');
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

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
          workflows={workflows}
          currentWorkflowId={currentWorkflowId}
          onSelectWorkflow={handleSelectWorkflow}
          onEditWorkflow={(wf) => setEditingWorkflow({ id: wf.id, name: wf.name, description: wf.description || '' })}
          onDeleteWorkflow={(wf) => setDeletingWorkflow({ id: wf.id, name: wf.name })}
          onCreateWorkflow={() => setShowCreateModal(true)}
          onOpenNodeList={() => setShowNodeList(true)}
          onLogout={handleLogout}
        />

        <div className="flex-1 flex flex-col">
          <div className="h-12 flex items-center border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <div style={{ width: !sidebarOpen ? SIDEBAR_HAMBURGER_WIDTH : 0 }} className="transition-all" />
            <div className="flex-1 flex justify-center items-center">
              <h2 className="text-sm font-semibold text-[var(--text-main)]">
                {workflows.find(w => w.id === currentWorkflowId)?.name || 'Untitled Workflow'}
              </h2>
            </div>
            <div style={{ width: !sidebarOpen ? SIDEBAR_HAMBURGER_WIDTH : 0 }} className="transition-all" />
          </div>
          <IOSCanvas
            onOpenCreateModal={handleOpenCreateModal}
            onOpenEditModal={handleOpenEditModal}
            onRequestDeleteNode={handleRequestDeleteNode}
            onRequestDeleteEdge={handleRequestDeleteEdge}
          />
        </div>

        <NodeListPanel
          visible={showNodeList}
          onClose={() => setShowNodeList(false)}
          nodes={store.graph.nodes}
          onAddNode={(nodeData, position) => {
            store.addNode({
              type: 'prompt',
              promptKey: nodeData.promptKey,
              config: nodeData.config || {},
            }, position);
          }}
          onUpdateNode={async (recordId, promptKey, config) => {
            store.updateNodeConfig(recordId, { promptKey, config });
          }}
          onDeleteNode={(nodeId) => {
            const node = store.graph.nodes.find(n => n.id === nodeId);
            if (node) {
              setDeletingNode({ id: node.id, name: node.promptKey });
            }
          }}
          currentWorkflowId={currentWorkflowId}
        />

        <NodeModal
          visible={showNodeModal}
          onClose={() => setShowNodeModal(false)}
          title={nodeTitle}
          onTitleChange={setNodeTitle}
          prompt={nodePrompt}
          onPromptChange={setNodePrompt}
          onConfirm={handleCreateNode}
          validationError={
            nodeTitle.trim() ? null : 'Node title cannot be empty'
          }
        />

        <CreateWorkflowModal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateWorkflow}
          isPending={false}
        />

        <EditWorkflowModal
          isOpen={!!editingWorkflow}
          onClose={() => setEditingWorkflow(null)}
          initialName={editingWorkflow?.name || ''}
          initialDescription={editingWorkflow?.description || ''}
          onSave={async (name, description) => {
            if (editingWorkflow) {
              await handleUpdateWorkflow(editingWorkflow.id, name, description);
            }
          }}
          isSaving={false}
        />

        <DeleteConfirmModal
          isOpen={!!deletingWorkflow}
          onClose={() => setDeletingWorkflow(null)}
          onConfirm={async () => await handleDeleteWorkflow(deletingWorkflow!.id)}
          itemName={deletingWorkflow?.name || ''}
          itemType="workflow"
          isPending={false}
        />

        <EditNodeModal
          isOpen={!!editingNode}
          onClose={() => setEditingNode(null)}
          initialPromptKey={editingNode?.promptKey || ''}
          initialConfig={editingNode?.config || {}}
          onSave={async (promptKey, config) => {
            if (editingNode) {
              store.updateNodeConfig(editingNode.id, { promptKey, config });
              setEditingNode(null);
            }
          }}
          isSaving={false}
        />

        <DeleteConfirmModal
          isOpen={!!deletingNode}
          onClose={() => setDeletingNode(null)}
          onConfirm={async () => {
            if (deletingNode) {
              store.removeNode(deletingNode.id);
              setDeletingNode(null);
            }
          }}
          itemName={deletingNode?.name || ''}
          itemType="node"
          isPending={false}
        />

        <DeleteConfirmModal
          isOpen={!!deletingEdge}
          onClose={() => setDeletingEdge(null)}
          onConfirm={async () => {
            if (deletingEdge) {
              store.removeEdge(deletingEdge.edgeId);
              setDeletingEdge(null);
            }
          }}
          itemName={`edge`}
          itemType="edge"
          isPending={false}
        />
      </div>
    </IOSShell>
  );
};