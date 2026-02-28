import React, { useState, useEffect } from 'react';
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
import { SIDEBAR_HAMBURGER_WIDTH } from '../../constants/canvas';

export const WorkspacePage: React.FC = () => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [userClosedSidebar, setUserClosedSidebar] = useState(false);

  const { selectedProjectId } = useSelectedProject(projects);
  const workflowsHook = useWorkflows(selectedProjectId);

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
                  <button
                    key={wf.id}
                    onClick={() => workflowsHook.setCurrentWorkflowId(wf.id!)}
                    className={`w-full text-left px-3 py-2 rounded mb-1 text-xs ${
                      workflowsHook.currentWorkflowId === wf.id
                        ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'
                    }`}
                    data-testid="workflow-item"
                  >
                    <div className="font-semibold truncate">{wf.name}</div>
                    <div className="text-[9px] opacity-60 truncate">
                      {wf.description || 'No description'}
                    </div>
                  </button>
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
                  onClick={workflowsHook.handleSave}
                  disabled={!selectedProjectId || !workflowsHook.workflowName.trim() || workflowsHook.loading}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                  data-testid="save-workflow"
                >
                  Save
                </button>
                <button
                  onClick={() => workflowsHook.setShowNodeList(true)}
                  disabled={!selectedProjectId}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                  data-testid="nodes-button"
                >
                  Nodes
                </button>
                <button
                  onClick={workflowsHook.handleDelete}
                  disabled={!workflowsHook.currentWorkflowId}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                  data-testid="delete-workflow"
                >
                  Delete
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
            <div className="flex-1 flex justify-center">
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
          />
        </div>

        <NodeListPanel
          visible={workflowsHook.showNodeList}
          onClose={() => workflowsHook.setShowNodeList(false)}
          nodes={workflowsHook.nodes}
          onAddNode={workflowsHook.addNodeFromList}
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
      </div>
    </IOSShell>
  );
};
