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

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadWorkflows();
    }
  }, [selectedProjectId]);

  const loadProjects = async () => {
    try {
      const res = await client.GET('/api/projects');
      if (res.error) throw new Error(res.error.error || 'Failed to load projects');
      const projectsData = (res.data || []).filter((p): p is Project => !!p.id);
      setProjects(projectsData);
      if (projectsData.length > 0 && !selectedProjectId) {
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
      const workflowsData = (res.data || []).filter((w): w is Workflow => !!w.id);
      setWorkflows(workflowsData);
    } catch (e: any) {
      console.error('❌ Load workflows error:', e);
      alert('Ошибка загрузки workflow: ' + e.message);
    }
  };

  const loadWorkflow = async (workflowId: string) => {
    try {
      const res = await client.GET('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: workflowId } }
      });
      if (res.error) throw new Error(res.error.error || 'Failed to load workflow');
      
      const data: any = res.data;
      setNodes((data?.nodes || []).map((n: any) => ({
        id: n.node_id || crypto.randomUUID(),
        node_id: n.node_id,
        prompt_key: n.prompt_key || 'UNKNOWN',
        position_x: n.position_x || 0,
        position_y: n.position_y || 0,
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
    setWorkflowName('');
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
        loadWorkflows();
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
              <h1 className="text-lg font-bold text-[var(--bronze-base)]">
                {currentWorkflowId ? workflowName : 'New Workflow'}
              </h1>
              {currentWorkflowId && (
                <span className="text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-0.5 rounded border border-[var(--ios-border)]">Editing</span>
              )}
              {loading && (
                <span className="text-[10px] text-[var(--accent-info)] animate-pulse">Saving...</span>
              )}
            </div>
            <div className="flex items-center gap-2">
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

          <IOSCanvas nodes={nodes} edges={edges} onNodesChange={setNodes} onEdgesChange={setEdges} />

          <div className="absolute bottom-20 left-6 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-3 py-2 rounded border border-[var(--ios-border)] pointer-events-none">
            <div>🖱️ Double-click / Right-click: Add node</div>
            <div>✋ Alt+Drag: Pan canvas</div>
            <div>🎯 Drag node: Move</div>
            <div>🔍 Scroll: Zoom</div>
          </div>
        </div>
      </div>
    </IOSShell>
  );
};