import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { api, ProjectResponse } from '../../api/client';
import { IOSShell } from './IOSShell';
import { IOSCanvas } from './IOSCanvas';
import { NodeListPanel } from './NodeListPanel';
import { NodeModal } from './NodeModal';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import { HamburgerMenu } from '../layout/HamburgerMenu';
import { useWorkflows } from '../../hooks/useWorkflows';
import { useSelectedProject } from '../../hooks/useSelectedProject';
import { CreateWorkflowModal } from './CreateWorkflowModal';
import { EditWorkflowModal } from './EditWorkflowModal';
import { DeleteConfirmModal } from '../common/DeleteConfirmModal';
import { EditNodeModal } from './EditNodeModal';
import { SIDEBAR_HAMBURGER_WIDTH } from '../../constants/canvas';

export const WorkspacePage: React.FC = () => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [userClosedSidebar, setUserClosedSidebar] = useState(false);

  const { selectedProjectId } = useSelectedProject(projects);
  const workflowsHook = useWorkflows(selectedProjectId);

  const [editingNode, setEditingNode] = useState<{ recordId: string; promptKey: string; config: Record<string, unknown> } | null>(null);
  const [deletingNode, setDeletingNode] = useState<{ recordId?: string; nodeId: string; name: string } | null>(null);

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

  const handleRequestDeleteNode = (recordId: string | undefined, nodeId: string, name: string) => {
    setDeletingNode({ recordId, nodeId, name });
  };

  const confirmDeleteNode = async () => {
    if (!deletingNode) return;
    if (deletingNode.recordId) {
      await workflowsHook.deleteNode(deletingNode.recordId);
    } else {
      workflowsHook.setNodes(prev => prev.filter(n => n.node_id !== deletingNode.nodeId));
      workflowsHook.setEdges(prev => prev.filter(e => e.source_node !== deletingNode.nodeId && e.target_node !== deletingNode.nodeId));
      toast.success('Node removed');
    }
    setDeletingNode(null);
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
              ) : workflowsHook.workflows.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] text-center py-4">
                  No workflows
                </div>
              ) : (
                workflowsHook.workflows.map((wf) => (
                  <div
                    key={wf.id}
                    className={`w-full text-left px-3 py-2 rounded mb-1 text-xs flex items-center justify-between cursor-pointer ${
                      workflowsHook.currentWorkflowId === wf.id
                        ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'
                    }`}
                    onClick={() => workflowsHook.setCurrentWorkflowId(wf.id!)}
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
                        onClick={() => workflowsHook.openEditModal(wf)}
                        className="text-[var(--text-muted)] hover:text-[var(--bronze-base)] transition-colors p-1"
                        title="Edit workflow"
                      >
                        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M17 3L21 7L7 21H3V17L17 3Z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => workflowsHook.openDeleteModal(wf)}
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
                onClick={() => workflowsHook.setShowCreateWorkflowModal(true)}
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
                  onClick={() => workflowsHook.setShowNodeList(true)}
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
                {workflowsHook.workflows.length} workflow{workflowsHook.workflows.length !== 1 ? 's' : ''}
              </div>
            </div>
          </aside>
        )}

        <div className="flex-1 flex flex-col">
          <div className="h-12 flex items-center border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <div style={{ width: !sidebarOpen ? SIDEBAR_HAMBURGER_WIDTH : 0 }} className="transition-all" />
            <div className="flex-1 flex justify-center items-center">
              <h2 className="text-sm font-semibold text-[var(--text-main)]">
                {workflowsHook.workflowName || 'Untitled Workflow'}
              </h2>
            </div>
            <div style={{ width: !sidebarOpen ? SIDEBAR_HAMBURGER_WIDTH : 0 }} className="transition-all" />
          </div>
          <IOSCanvas
            nodes={workflowsHook.nodes}
            edges={workflowsHook.edges}
            onNodesChange={workflowsHook.setNodes}
            onEdgesChange={workflowsHook.setEdges}
            onAddCustomNode={workflowsHook.handleAddCustomNode}
            onEditNode={(recordId, promptKey, config) => setEditingNode({ recordId, promptKey, config })}
            onRequestDeleteNode={handleRequestDeleteNode}
          />
        </div>

        <NodeListPanel
          visible={workflowsHook.showNodeList}
          onClose={() => workflowsHook.setShowNodeList(false)}
          nodes={workflowsHook.nodes}
          onAddNode={workflowsHook.addNodeFromList}
          onUpdateNode={async (recordId, promptKey, config) => {
            await workflowsHook.updateNode(recordId, promptKey, config);
          }}
          onDeleteNode={(recordId, nodeId) => {
            const node = workflowsHook.nodes.find(n => n.node_id === nodeId);
            if (node) {
              handleRequestDeleteNode(recordId, nodeId, node.prompt_key);
            }
          }}
          currentWorkflowId={workflowsHook.currentWorkflowId}
        />
        <NodeModal
          visible={workflowsHook.showNodeModal}
          onClose={() => workflowsHook.setShowNodeModal(false)}
          title={workflowsHook.newNodeTitle}
          onTitleChange={workflowsHook.setNewNodeTitle}
          prompt={workflowsHook.newNodePrompt}
          onPromptChange={workflowsHook.setNewNodePrompt}
          onConfirm={workflowsHook.confirmAddCustomNode}
          validationError={workflowsHook.newNodeTitle.trim() ? workflowsHook.validateNodeUnique(workflowsHook.newNodeTitle.trim(), workflowsHook.newNodePrompt) : null}
        />

        <CreateWorkflowModal
          isOpen={workflowsHook.showCreateWorkflowModal}
          onClose={() => workflowsHook.setShowCreateWorkflowModal(false)}
          onCreate={async (name, description) => {
            await workflowsHook.handleCreateWorkflow(name, description);
          }}
          isPending={workflowsHook.isCreatingWorkflow}
        />

        <EditWorkflowModal
          isOpen={!!workflowsHook.editingWorkflow}
          onClose={workflowsHook.closeEditModal}
          initialName={workflowsHook.editingWorkflow?.name || ''}
          initialDescription={workflowsHook.editingWorkflow?.description || ''}
          onSave={async (name, description) => {
            if (workflowsHook.editingWorkflow) {
              await workflowsHook.updateWorkflowMetadata(
                workflowsHook.editingWorkflow.id,
                name,
                description
              );
              workflowsHook.closeEditModal();
            }
          }}
          isSaving={workflowsHook.loading}
        />

        <DeleteConfirmModal
          isOpen={!!workflowsHook.deletingWorkflow}
          onClose={workflowsHook.closeDeleteModal}
          onConfirm={async () => {
            if (workflowsHook.deletingWorkflow) {
              await workflowsHook.handleDelete(workflowsHook.deletingWorkflow.id);
            }
          }}
          itemName={workflowsHook.deletingWorkflow?.name || ''}
          itemType="workflow"
          isPending={workflowsHook.isDeletingWorkflow}
        />

        <EditNodeModal
          isOpen={!!editingNode}
          onClose={() => setEditingNode(null)}
          initialPromptKey={editingNode?.promptKey || ''}
          initialConfig={editingNode?.config || {}}
          onSave={async (promptKey, config) => {
            if (editingNode) {
              await workflowsHook.updateNode(editingNode.recordId, promptKey, config);
              setEditingNode(null);
            }
          }}
          isSaving={workflowsHook.isUpdatingNode}
        />

        <DeleteConfirmModal
          isOpen={!!deletingNode}
          onClose={() => setDeletingNode(null)}
          onConfirm={confirmDeleteNode}
          itemName={deletingNode?.name || ''}
          itemType="node"
          isPending={workflowsHook.isDeletingNode}
        />
      </div>
    </IOSShell>
  );
};
