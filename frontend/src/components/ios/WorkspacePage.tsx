// frontend/src/components/ios/WorkspacePage.tsx
import React, { useState, useEffect } from 'react';
import type { NodeData, EdgeData } from '../../hooks/useCanvasEngine';
import { IOSShell } from './IOSShell';
import { IOSCanvas } from './IOSCanvas';

interface Workflow {
  id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  created_at?: string;
}

interface WorkflowDetail {
  workflow: Workflow;
  nodes: NodeData[];
  edges: EdgeData[];
}

export const WorkspacePage: React.FC = () => {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workflowName, setWorkflowName] = useState('');
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Загрузка списка workflow
  useEffect(() => {
    loadWorkflows();
  }, []);

  const loadWorkflows = async () => {
    try {
      const res = await fetch('/api/workflows');
      if (res.ok) {
        const data = await res.json();
        setWorkflows(data);
      }
    } catch (e) {
      console.error('Failed to load workflows', e);
    }
  };

  // Загрузка конкретного workflow
  const loadWorkflow = async (workflowId: string) => {
    try {
      const res = await fetch(`/api/workflows/${workflowId}`);
      if (res.ok) {
        const data: WorkflowDetail = await res.json();
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
        setCurrentWorkflowId(workflowId);
        setWorkflowName(data.workflow?.name || '');
      }
    } catch (e) {
      console.error('Failed to load workflow', e);
      alert('Ошибка загрузки workflow');
    }
  };

  // Создание нового workflow
  const createNewWorkflow = () => {
    setNodes([]);
    setEdges([]);
    setCurrentWorkflowId(null);
    setWorkflowName('');
  };

  // Сохранение workflow
  const handleSave = async () => {
    if (!workflowName) {
      alert('Введите название workflow');
      return;
    }

    try {
      const url = currentWorkflowId 
        ? `/api/workflows/${currentWorkflowId}` 
        : '/api/workflows';
      
      const method = currentWorkflowId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: workflowName,
          description: 'Created in workspace editor',
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

      if (res.ok) {
        const data = await res.json();
        if (!currentWorkflowId) {
          setCurrentWorkflowId(data.id);
          loadWorkflows();
        }
        alert(`Workflow ${currentWorkflowId ? 'обновлён' : 'сохранён'}!`);
      } else {
        alert('Ошибка сохранения');
      }
    } catch (e) {
      console.error(e);
      alert('Ошибка сети');
    }
  };

  // Удаление workflow
  const handleDelete = async () => {
    if (!currentWorkflowId) return;
    if (!confirm(`Удалить workflow "${workflowName}"?`)) return;

    try {
      const res = await fetch(`/api/workflows/${currentWorkflowId}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        createNewWorkflow();
        loadWorkflows();
        alert('Workflow удалён');
      } else {
        alert('Ошибка удаления');
      }
    } catch (e) {
      console.error(e);
      alert('Ошибка сети');
    }
  };

  return (
    <IOSShell>
      <div className="flex h-full">
        {/* Sidebar */}
        {sidebarOpen && (
          <aside className="w-64 bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col z-50">
            {/* Header */}
            <div className="h-14 flex items-center justify-between px-4 border-b border-[var(--ios-border)]">
              <span className="text-xs font-bold text-[var(--bronze-base)] uppercase tracking-wider">
                Workflows
              </span>
              <button
                onClick={() => setSidebarOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-main)]"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {/* New Workflow Button */}
            <div className="p-3 border-b border-[var(--ios-border)]">
              <button
                onClick={createNewWorkflow}
                className="w-full px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                New Workflow
              </button>
            </div>

            {/* Workflow List */}
            <div className="flex-1 overflow-y-auto p-2">
              {workflows.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] text-center py-4">
                  No workflows yet
                </div>
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
                    <div className="text-[9px] opacity-60 truncate">
                      {wf.description || 'No description'}
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-[var(--ios-border)] text-[9px] text-[var(--text-muted)] text-center">
              {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
            </div>
          </aside>
        )}

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)] backdrop-blur-md z-100">
            <div className="flex items-center gap-4">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="text-[var(--text-muted)] hover:text-[var(--text-main)]"
                >
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
                <span className="text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-0.5 rounded border border-[var(--ios-border)]">
                  Editing
                </span>
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
                className="px-4 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors"
              >
                {currentWorkflowId ? 'Update' : 'Save'} Workflow
              </button>
            </div>
          </header>

          {/* Canvas */}
          <IOSCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={setNodes}
            onEdgesChange={setEdges}
          />

          {/* Instructions */}
          <div className="absolute bottom-20 left-6 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-3 py-2 rounded border border-[var(--ios-border)] pointer-events-none">
            <div>Double-click / Right-click: Add node</div>
            <div>Alt+Drag: Pan canvas</div>
            <div>Drag node: Move</div>
            <div>Scroll: Zoom</div>
          </div>
        </div>
      </div>
    </IOSShell>
  );
};