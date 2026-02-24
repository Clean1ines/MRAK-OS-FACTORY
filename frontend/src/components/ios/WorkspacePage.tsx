// frontend/src/components/ios/WorkspacePage.tsx
import React, { useState, useEffect } from 'react';
import type { NodeData, EdgeData } from '../../hooks/useCanvasEngine';
import { IOSShell } from './IOSShell';
import { IOSCanvas } from './IOSCanvas';
import { client } from '../../api/client';

interface Workflow {
  id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  created_at?: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
}

export const WorkspacePage: React.FC = () => {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workflowName, setWorkflowName] = useState('');
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showNodeList, setShowNodeList] = useState(false);
  const [newNodePrompt, setNewNodePrompt] = useState('');
  const [newNodeTitle, setNewNodeTitle] = useState('');
  const [nodeListTab, setNodeListTab] = useState<'available' | 'created'>('created');

  useEffect(() => {
    const saved = localStorage.getItem('workspace_selected_project');
    if (saved) {
      setSelectedProjectId(saved);
    }
    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      localStorage.setItem('workspace_selected_project', selectedProjectId);
      loadWorkflows();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);

  useEffect(() => {
    if (currentWorkflowId) {
      loadWorkflows();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentWorkflowId]);

  const loadProjects = async () => {
    try {
      const res = await client.GET('/api/projects');
      if (res.error) throw new Error(res.error.error || 'Failed to load projects');
      const projectsData: Project[] = (res.data || []).map((p: any) => ({
        id: p.id!,
        name: p.name!,
        description: p.description || '',
      }));
      setProjects(projectsData);
      const saved = localStorage.getItem('workspace_selected_project');
      if (projectsData.length > 0 && !saved) {
        setSelectedProjectId(projectsData[0].id);
      }
    } catch (e: any) {
      console.error('❌ Load projects error:', e);
      alert('Ошибка загрузки проектов: ' + e.message);
    }
  };

  const loadWorkflows = async () => {
    if (!selectedProjectId) return;
    try {
      const res = await client.GET('/api/workflows');
      if (res.error) throw new Error(res.error.error || 'Failed to load workflows');
      const workflowsData: Workflow[] = (res.data || []).map((w: any) => ({
        id: w.id!,
        name: w.name!,
        description: w.description || '',
        is_default: w.is_default || false,
        created_at: w.created_at,
      }));
      setWorkflows(workflowsData);
    } catch (e: any) {
      console.error('❌ Load workflows error:', e);
      alert('Ошибка загрузки workflow: ' + e.message);
    }
  };

  // #CHANGED: Fixed variable declaration (added 'data' variable name)
  const loadWorkflow = async (workflowId: string) => {
    try {
      const res = await client.GET('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: workflowId } }
      });
      if (res.error) throw new Error(res.error.error || 'Failed to load workflow');
      
      const data: any = res.data;  // ← FIX: Added 'data' variable name (was 'const  any')
      setNodes((data?.nodes || []).map((n: any) => ({
        id: n.node_id || crypto.randomUUID(),
        node_id: n.node_id,
        prompt_key: n.prompt_key || 'UNKNOWN',
        position_x: n.position_x || 100,
        position_y: n.position_y || 100,
        config: n.config || {},
      })));
      setEdges((data?.edges || []).map((e: any) => ({
        id: e.id || crypto.randomUUID(),
        source_node: e.source_node,
        target_node: e.target_node,
      })));
      setCurrentWorkflowId(workflowId);
      setWorkflowName(data?.workflow?.name || '');
    } catch (e: any) {
      console.error('❌ Load workflow error:', e);
      alert('Ошибка загрузки workflow: ' + e.message);
    }
  };

  const createNewWorkflow = () => {
    setNodes([]);
    setEdges([]);
    setCurrentWorkflowId(null);
    setWorkflowName('New Workflow');
    setShowNodeModal(true);
    console.log('✅ New workflow created (cleared state)');
  };

  const validateNodeUnique = (title: string, prompt: string): string | null => {
    const duplicateTitle = nodes.find(n => 
      n.prompt_key.toLowerCase() === title.toLowerCase() && n.prompt_key !== 'CUSTOM_PROMPT'
    );
    if (duplicateTitle) {
      return `Node with name "${title}" already exists`;
    }

    const duplicateContent = nodes.find(n => 
      n.config?.custom_prompt === prompt
    );
    if (duplicateContent) {
      return `Node with identical prompt already exists`;
    }

    return null;
  };

  const handleSave = async () => {
    if (!workflowName.trim()) {
      alert('⚠️ Введите название workflow');
      return;
    }

    if (!selectedProjectId) {
      alert('⚠️ Выберите проект');
      return;
    }

    setLoading(true);

    try {
      const url = currentWorkflowId 
        ? `/api/workflows/${currentWorkflowId}` 
        : '/api/workflows';
      
      const method = currentWorkflowId ? 'PUT' : 'POST';

      console.log('💾 Saving workflow:', { url, method, name: workflowName, nodes: nodes.length, edges: edges.length });

      const res = await fetch(url, {
        method,
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
            config: n.config,
          })),
          edges: edges.map(e => ({
            source_node: e.source_node,
            target_node: e.target_node,
          })),
        }),
      });

      const responseData = await res.json();
      console.log('💾 Save response:', res.status, responseData);

      if (!res.ok) {
        throw new Error(responseData.detail || `HTTP ${res.status}`);
      }

      if (!currentWorkflowId && responseData.id) {
        setCurrentWorkflowId(responseData.id);
        await loadWorkflows();
      } else if (currentWorkflowId) {
        await loadWorkflows();
      }

      alert(`✅ Workflow ${currentWorkflowId ? 'обновлён' : 'сохранён'}!`);

    } catch (e: any) {
      console.error('❌ Save error:', e);
      alert('❌ Ошибка сохранения: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!currentWorkflowId) return;
    if (!confirm(`Удалить workflow "${workflowName}"?`)) return;

    try {
      const res = await client.DELETE('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: currentWorkflowId } }
      });

      if (res.error) throw new Error(res.error.error || 'Failed to delete');

      createNewWorkflow();
      loadWorkflows();
      alert('✅ Workflow удалён');
    } catch (e: any) {
      console.error('❌ Delete error:', e);
      alert('❌ Ошибка удаления: ' + e.message);
    }
  };

  const handleAddCustomNode = (x: number, y: number) => {
    setNewNodeTitle('');
    setNewNodePrompt('');
    setShowNodeModal(true);
    (window as any)._newNodePosition = { x, y };
  };

  const confirmAddCustomNode = async () => {
    if (!newNodePrompt.trim()) {
      alert('Введите промпт');
      return;
    }

    const title = newNodeTitle.trim() || 'CUSTOM_PROMPT';
    const validationError = validateNodeUnique(title, newNodePrompt);
    if (validationError) {
      alert(`⚠️ ${validationError}`);
      return;
    }

    const pos = (window as any)._newNodePosition;
    if (pos) {
      const newNode: NodeData = {
        id: crypto.randomUUID(),
        node_id: crypto.randomUUID(),
        prompt_key: title,
        position_x: pos.x,
        position_y: pos.y,
        config: { custom_prompt: newNodePrompt },
      };
      setNodes(prev => [...prev, newNode]);
    }

    setShowNodeModal(false);
    setNewNodePrompt('');
    setNewNodeTitle('');
  };

  const addNodeFromList = (node: NodeData, x: number, y: number) => {
    const newNode: NodeData = {
      ...node,
      id: crypto.randomUUID(),
      node_id: crypto.randomUUID(),
      position_x: x,
      position_y: y,
    };
    setNodes(prev => [...prev, newNode]);
    setShowNodeList(false);
  };

  return (
    <IOSShell>
      <div className="flex h-full">
        {sidebarOpen && (
          <aside className="w-64 bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col z-50">
            <div className="p-3 border-b border-[var(--ios-border)]">
              <label className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider block mb-1">
                Project
              </label>
              <select
                value={selectedProjectId || ''}
                onChange={(e) => setSelectedProjectId(e.target.value || null)}
                className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-2 py-1.5 text-xs text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
              >
                <option value="">-- Select Project --</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div className="h-12 flex items-center justify-between px-4 border-b border-[var(--ios-border)]">
              <span className="text-xs font-bold text-[var(--bronze-base)] uppercase tracking-wider">
                Workflows
              </span>
              <button onClick={() => setSidebarOpen(false)} className="text-[var(--text-muted)] hover:text-[var(--text-main)]">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="p-3 border-b border-[var(--ios-border)]">
              <button
                onClick={createNewWorkflow}
                disabled={!selectedProjectId}
                className="w-full px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors flex items-center justify-center gap-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                New Workflow
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {!selectedProjectId ? (
                <div className="text-[10px] text-[var(--accent-warning)] text-center py-4">⚠️ Select a project first</div>
              ) : workflows.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] text-center py-4">No workflows yet</div>
              ) : (
                workflows.map(wf => (
                  <button
                    key={wf.id}
                    onClick={() => loadWorkflow(wf.id)}
                    className={`w-full text-left px-3 py-2 rounded mb-1 text-xs transition-colors ${
                      currentWorkflowId === wf.id
                        ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)] border border-[var(--bronze-dim)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'
                    }`}
                  >
                    <div className="font-semibold truncate">{wf.name}</div>
                    <div className="text-[9px] opacity-60 truncate">{wf.description || 'No description'}</div>
                  </button>
                ))
              )}
            </div>

            <div className="p-3 border-t border-[var(--ios-border)] text-[9px] text-[var(--text-muted)] text-center">
              {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
            </div>
          </aside>
        )}

        <div className="flex-1 flex flex-col">
          <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)] backdrop-blur-md z-100">
            <div className="flex items-center gap-4">
              {!sidebarOpen && (
                <button onClick={() => setSidebarOpen(true)} className="text-[var(--text-muted)] hover:text-[var(--text-main)]">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                  </svg>
                </button>
              )}
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                placeholder="Workflow Name"
                className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-1.5 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)] w-64"
              />
              {currentWorkflowId && (
                <span className="text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-0.5 rounded border border-[var(--ios-border)]">Editing</span>
              )}
              {loading && (
                <span className="text-[10px] text-[var(--accent-info)] animate-pulse">Saving...</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowNodeList(!showNodeList)}
                className="px-3 py-1.5 text-xs font-semibold rounded border border-[var(--ios-border)] text-[var(--text-main)] hover:bg-[var(--ios-glass-bright)] transition-colors"
              >
                📋 Nodes
              </button>
              <button
                onClick={handleDelete}
                disabled={!currentWorkflowId}
                className="px-3 py-1.5 text-xs font-semibold rounded border border-[var(--accent-danger)] text-[var(--accent-danger)] hover:bg-[var(--accent-danger)] hover:text-black transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Delete
              </button>
              <button
                onClick={handleSave}
                disabled={!selectedProjectId || !workflowName.trim() || loading}
                className="px-4 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {loading ? 'Saving...' : (currentWorkflowId ? 'Update' : 'Save')} Workflow
              </button>
            </div>
          </header>

          <IOSCanvas 
            nodes={nodes} 
            edges={edges} 
            onNodesChange={setNodes} 
            onEdgesChange={setEdges}
            onAddCustomNode={handleAddCustomNode}
          />

          {showNodeList && (
            <div className="absolute top-20 right-6 w-80 bg-[var(--ios-glass)] backdrop-blur-md border border-[var(--ios-border)] rounded-lg shadow-[var(--shadow-heavy)] z-[1000]">
              <div className="flex items-center justify-between p-3 border-b border-[var(--ios-border)]">
                <h3 className="text-sm font-bold text-[var(--bronze-base)]">Nodes</h3>
                <button onClick={() => setShowNodeList(false)} className="text-[var(--text-muted)] hover:text-[var(--text-main)]">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
              <div className="flex border-b border-[var(--ios-border)]">
                <button
                  onClick={() => setNodeListTab('created')}
                  className={`flex-1 px-3 py-2 text-xs font-semibold ${
                    nodeListTab === 'created' 
                      ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]' 
                      : 'text-[var(--text-muted)] hover:bg-[var(--ios-glass-bright)]'
                  }`}
                >
                  Created ({nodes.length})
                </button>
                <button
                  onClick={() => setNodeListTab('available')}
                  className={`flex-1 px-3 py-2 text-xs font-semibold ${
                    nodeListTab === 'available' 
                      ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]' 
                      : 'text-[var(--text-muted)] hover:bg-[var(--ios-glass-bright)]'
                  }`}
                >
                  Available
                </button>
              </div>
              <div className="p-3 max-h-96 overflow-y-auto">
                {nodeListTab === 'created' ? (
                  nodes.length === 0 ? (
                    <div className="text-[10px] text-[var(--text-muted)] text-center py-4">No nodes yet</div>
                  ) : (
                    nodes.map(node => (
                      <div
                        key={node.node_id}
                        className="p-2 mb-2 bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded text-xs cursor-pointer hover:border-[var(--bronze-base)] transition-colors"
                      >
                        <div className="font-semibold text-[var(--bronze-bright)]">{node.prompt_key}</div>
                        <div className="text-[9px] text-[var(--text-muted)] mt-1">
                          Pos: {Math.round(node.position_x)}, {Math.round(node.position_y)}
                        </div>
                      </div>
                    ))
                  )
                ) : (
                  <div className="space-y-2">
                    {['IDEA_CLARIFIER', 'BUSINESS_REQ_GEN', 'CODE_GEN'].map(type => (
                      <div
                        key={type}
                        className="p-2 bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded text-xs cursor-pointer hover:border-[var(--bronze-base)] transition-colors"
                        onClick={() => {
                          const pos = { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 };
                          addNodeFromList({
                            id: crypto.randomUUID(),
                            node_id: crypto.randomUUID(),
                            prompt_key: type,
                            position_x: pos.x,
                            position_y: pos.y,
                            config: {},
                          }, pos.x, pos.y);
                        }}
                      >
                        <div className="font-semibold text-[var(--bronze-bright)]">{type.replace(/_/g, ' ')}</div>
                        <div className="text-[9px] text-[var(--text-muted)] mt-1">Click to add</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {showNodeModal && (
            <div className="absolute inset-0 z-[2000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
              <div className="bg-[var(--ios-glass)] border border-[var(--ios-border)] rounded-lg p-6 w-[500px] shadow-[var(--shadow-heavy)]">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-[var(--bronze-base)]">Custom Prompt Node</h3>
                  <button
                    onClick={() => setShowNodeModal(false)}
                    className="text-[var(--text-muted)] hover:text-[var(--accent-danger)]"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
                <div className="mb-4">
                  <label className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider block mb-1">Node Title</label>
                  <input
                    type="text"
                    value={newNodeTitle}
                    onChange={(e) => setNewNodeTitle(e.target.value)}
                    placeholder="e.g., My Custom Node"
                    className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
                  />
                </div>
                <div className="mb-4">
                  <label className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider block mb-1">System Prompt</label>
                  <textarea
                    value={newNodePrompt}
                    onChange={(e) => setNewNodePrompt(e.target.value)}
                    placeholder="Enter your system prompt..."
                    className="w-full h-40 bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded p-3 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)] font-mono"
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={confirmAddCustomNode}
                    className="flex-1 px-4 py-2 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors"
                  >
                    Add Node
                  </button>
                  <button
                    onClick={() => setShowNodeModal(false)}
                    className="flex-1 px-4 py-2 text-xs font-semibold rounded border border-[var(--ios-border)] text-[var(--text-muted)] hover:bg-[var(--ios-glass-bright)] transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </IOSShell>
  );
};