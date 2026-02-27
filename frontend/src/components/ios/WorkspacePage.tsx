import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { NodeData, EdgeData } from '../../hooks/useCanvasEngine';
import { IOSShell } from './IOSShell';
import { IOSCanvas } from './IOSCanvas';
import { client } from '../../api/client';
import { api, ProjectResponse } from '../../api/client';
import { validateWorkflowAcyclic } from '../../utils/graphUtils';
import { NodeListPanel } from './NodeListPanel';
import { NodeModal } from './NodeModal';
import { useNodeValidation } from './useNodeValidation';

declare global {
  interface Window {
    _newNodePosition?: { x: number; y: number };
  }
}

interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface WorkflowNode {
  id: string;
  workflow_id: string;
  node_id: string;
  prompt_key: string;
  config?: Record<string, unknown>;
  position_x: number;
  position_y: number;
  created_at?: string;
  updated_at?: string;
}

interface WorkflowEdge {
  id: string;
  workflow_id: string;
  source_node: string;
  target_node: string;
  source_output?: string;
  target_input?: string;
  created_at?: string;
}

interface WorkflowDetail {
  workflow: WorkflowSummary;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export const WorkspacePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlProjectId = searchParams.get('projectId');

  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workflowName, setWorkflowName] = useState('');
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showNodeList, setShowNodeList] = useState(false);
  const [newNodePrompt, setNewNodePrompt] = useState('');
  const [newNodeTitle, setNewNodeTitle] = useState('');
  const { validateNodeUnique } = useNodeValidation(nodes);

  // Загрузка проектов при монтировании
  const loadProjects = useCallback(async () => {
    try {
      const { data, error } = await api.projects.list();
      if (error) {
        console.error('Failed to load projects:', error);
        return;
      }
      if (data && Array.isArray(data)) {
        setProjects(data);
        // Если проекты загружены и нет выбранного, но есть projectId в URL – используем его
        if (data.length > 0 && !selectedProjectId) {
          if (urlProjectId && data.some(p => p.id === urlProjectId)) {
            setSelectedProjectId(urlProjectId);
          } else if (!urlProjectId && localStorage.getItem('workspace_selected_project')) {
            // Fallback: если в localStorage есть старый выбор, используем его
            const stored = localStorage.getItem('workspace_selected_project');
            if (stored && data.some(p => p.id === stored)) {
              setSelectedProjectId(stored);
            } else {
              setSelectedProjectId(data[0].id!);
            }
          } else if (!urlProjectId) {
            // Ничего нет – выбираем первый проект
            setSelectedProjectId(data[0].id!);
          }
        }
      } else {
        setProjects([]);
      }
    } catch (e: unknown) {
      console.error('Error loading projects:', e);
    }
  }, [selectedProjectId, urlProjectId]);

  // Загрузка воркфлоу для выбранного проекта
  const loadWorkflows = useCallback(async () => {
    if (!selectedProjectId) return;
    try {
      const response = (await client.GET('/api/workflows')) as {
        data?: WorkflowSummary[];
        error?: unknown;
      };
      if (response.error) {
        console.error('Failed to load workflows:', response.error);
        return;
      }
      if (response.data && Array.isArray(response.data)) {
        setWorkflows(response.data);
      } else {
        setWorkflows([]);
      }
    } catch (e: unknown) {
      console.error('Error loading workflows:', e);
    }
  }, [selectedProjectId]);

  // Загрузка конкретного воркфлоу
  const loadWorkflow = useCallback(async (id: string) => {
    try {
      const r = await client.GET('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } }
      });
      if (r.error) {
        console.error('Failed to load workflow:', r.error);
        return;
      }
      const detail = r.data as WorkflowDetail;
      if (detail) {
        setNodes((detail.nodes || []).map((n: WorkflowNode) => ({
          id: n.node_id || crypto.randomUUID(),
          node_id: n.node_id!,
          prompt_key: n.prompt_key || 'UNKNOWN',
          position_x: n.position_x || 100,
          position_y: n.position_y || 100,
          config: n.config || {}
        })));
        setEdges((detail.edges || []).map((e: WorkflowEdge) => ({
          id: e.id || crypto.randomUUID(),
          source_node: e.source_node!,
          target_node: e.target_node!
        })));
        setCurrentWorkflowId(id);
        setWorkflowName(detail.workflow?.name || '');
      }
    } catch (e: unknown) {
      console.error('Error loading workflow:', e);
    }
  }, []);

  // При монтировании загружаем проекты
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // При изменении selectedProjectId загружаем воркфлоу и обновляем URL
  useEffect(() => {
    if (selectedProjectId) {
      localStorage.setItem('workspace_selected_project', selectedProjectId);
      // Обновляем URL, если он не совпадает
      if (searchParams.get('projectId') !== selectedProjectId) {
        setSearchParams({ projectId: selectedProjectId });
      }
      loadWorkflows();
    }
  }, [selectedProjectId, loadWorkflows, searchParams, setSearchParams]);

  // При изменении URL (projectId) синхронизируем selectedProjectId
  useEffect(() => {
    if (urlProjectId && urlProjectId !== selectedProjectId) {
      setSelectedProjectId(urlProjectId);
    } else if (!urlProjectId && !selectedProjectId) {
      // Если в URL нет projectId и у нас нет выбранного, пытаемся взять из localStorage
      const stored = localStorage.getItem('workspace_selected_project');
      if (stored) {
        setSelectedProjectId(stored);
      }
    }
  }, [urlProjectId, selectedProjectId]);

  // При изменении currentWorkflowId загружаем детали воркфлоу
  useEffect(() => {
    if (currentWorkflowId) {
      loadWorkflow(currentWorkflowId);
    } else {
      // Если нет выбранного воркфлоу, очищаем холст
      setNodes([]);
      setEdges([]);
      setWorkflowName('');
    }
  }, [currentWorkflowId, loadWorkflow]);

  const handleSave = async () => {
    if (!workflowName.trim() || !selectedProjectId) {
      toast.error('⚠️ Заполните обязательные поля');
      return;
    }
    if (!validateWorkflowAcyclic(nodes, edges).valid) {
      toast.error('⚠️ Обнаружен цикл – удалите круговые соединения');
      return;
    }
    setLoading(true);
    try {
      const url = currentWorkflowId
        ? `/api/workflows/${currentWorkflowId}`
        : '/api/workflows';
      const res = await fetch(url, {
        method: currentWorkflowId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: workflowName,
          description: 'Created in workspace editor',
          project_id: selectedProjectId,
          nodes: nodes.map(n => ({
            node_id: n.node_id,
            prompt_key: n.prompt_key,
            position_x: n.position_x,
            position_y: n.position_y,
            config: n.config
          })),
          edges: edges.map(e => ({
            source_node: e.source_node,
            target_node: e.target_node
          }))
        })
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }
      if (!currentWorkflowId) await loadWorkflows();
      toast.success(`✅ Workflow ${currentWorkflowId ? 'обновлён' : 'сохранён'}!`);
    } catch (e: unknown) {
      console.error('Save error:', e);
      toast.error('❌ Ошибка при сохранении: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!currentWorkflowId || !confirm(`Удалить "${workflowName}"?`)) return;
    try {
      const r = await client.DELETE('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: currentWorkflowId } }
      });
      if (r.error) {
        console.error('Delete error:', r.error);
        return;
      }
      setNodes([]);
      setEdges([]);
      setCurrentWorkflowId(null);
      setWorkflowName('New Workflow');
      await loadWorkflows();
      toast.success('✅ Удалено');
    } catch (e: unknown) {
      console.error('Delete exception:', e);
      toast.error('❌ Ошибка при удалении');
    }
  };

  const handleAddCustomNode = (x: number, y: number) => {
    setNewNodeTitle('');
    setNewNodePrompt('');
    setShowNodeModal(true);
    window._newNodePosition = { x, y };
  };

  const confirmAddCustomNode = async () => {
    if (!newNodePrompt.trim()) {
      toast.error('Введите промпт');
      return;
    }
    const title = newNodeTitle.trim() || 'CUSTOM_PROMPT';
    const err = validateNodeUnique(title, newNodePrompt);
    if (err) {
      toast.error(`⚠️ ${err}`);
      return;
    }
    const pos = window._newNodePosition;
    if (pos) {
      setNodes(prev => [...prev, {
        id: crypto.randomUUID(),
        node_id: crypto.randomUUID(),
        prompt_key: title,
        position_x: pos.x,
        position_y: pos.y,
        config: { custom_prompt: newNodePrompt }
      }]);
    }
    setShowNodeModal(false);
    setNewNodePrompt('');
    setNewNodeTitle('');
  };

  const addNodeFromList = (node: NodeData) => {
    setNodes(prev => [...prev, node]);
    setShowNodeList(false);
  };

  const handleLogout = async () => {
    try {
      await api.auth.logout();
      window.location.href = '/login';
    } catch (e) {
      console.error(e);
    }
  };

  const handleProjectChange = (projectId: string | null) => {
    setSelectedProjectId(projectId);
    // Принудительно сбрасываем текущий воркфлоу
    setCurrentWorkflowId(null);
  };

  return (
    <IOSShell>
      <div className="flex h-full">
        {sidebarOpen && (
          <aside className="w-64 bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col z-50">
            <div className="p-3 border-b border-[var(--ios-border)]">
              <label className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider block mb-1">Project</label>
              <select
                value={selectedProjectId || ''}
                onChange={(e) => handleProjectChange(e.target.value || null)}
                className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-2 py-1.5 text-xs text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
              >
                <option value="">-- Select Project --</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {!selectedProjectId ? (
                <div className="text-[10px] text-[var(--accent-warning)] text-center py-4">⚠️ Select project</div>
              ) : workflows.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] text-center py-4">No workflows</div>
              ) : (
                workflows.map(wf => (
                  <button
                    key={wf.id}
                    onClick={() => setCurrentWorkflowId(wf.id!)}
                    className={`w-full text-left px-3 py-2 rounded mb-1 text-xs ${
                      currentWorkflowId === wf.id
                        ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'
                    }`}
                  >
                    <div className="font-semibold truncate">{wf.name}</div>
                    <div className="text-[9px] opacity-60 truncate">{wf.description || 'No description'}</div>
                  </button>
                ))
              )}
            </div>

            <div className="p-3 border-t border-[var(--ios-border)] space-y-2">
              <button
                onClick={() => {
                  setNodes([]);
                  setEdges([]);
                  setCurrentWorkflowId(null);
                  setWorkflowName('New Workflow');
                  setShowNodeModal(true);
                }}
                disabled={!selectedProjectId}
                className="w-full px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors flex items-center justify-center gap-2 disabled:opacity-30"
              >
                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                New Workflow
              </button>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleSave}
                  disabled={!selectedProjectId || !workflowName.trim() || loading}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                >
                  Save
                </button>
                <button
                  onClick={() => setShowNodeList(true)}
                  disabled={!selectedProjectId}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                >
                  Nodes
                </button>
                <button
                  onClick={handleDelete}
                  disabled={!currentWorkflowId}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors disabled:opacity-30"
                >
                  Delete
                </button>
                <button
                  onClick={handleLogout}
                  className="px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors"
                >
                  Logout
                </button>
              </div>

              <div className="text-[9px] text-[var(--text-muted)] text-center pt-2">
                {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
              </div>
            </div>
          </aside>
        )}

        <div className="flex-1 flex flex-col">
          <div className="h-12 flex items-center justify-between px-4 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)]">
            <div className="flex items-center gap-2">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="text-[var(--text-muted)] hover:text-[var(--text-main)]"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                  </svg>
                </button>
              )}
              <h2 className="text-sm font-semibold text-[var(--text-main)]">
                {workflowName || 'Untitled Workflow'}
              </h2>
            </div>
          </div>
          <IOSCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={setNodes}
            onEdgesChange={setEdges}
            onAddCustomNode={handleAddCustomNode}
          />
        </div>

        <NodeListPanel
          visible={showNodeList}
          onClose={() => setShowNodeList(false)}
          nodes={nodes}
          onAddNode={addNodeFromList}
        />
        <NodeModal
          visible={showNodeModal}
          onClose={() => setShowNodeModal(false)}
          title={newNodeTitle}
          onTitleChange={setNewNodeTitle}
          prompt={newNodePrompt}
          onPromptChange={setNewNodePrompt}
          onConfirm={confirmAddCustomNode}
          validationError={newNodeTitle.trim() ? validateNodeUnique(newNodeTitle.trim(), newNodePrompt) : null}
        />
      </div>
    </IOSShell>
  );
};
