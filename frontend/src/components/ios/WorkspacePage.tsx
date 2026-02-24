// frontend/src/components/ios/WorkspacePage.tsx
import React, { useState } from 'react';
import { IOSShell } from './IOSShell';
import { IOSCanvas } from './IOSCanvas';
import { NodeData, EdgeData } from '../../hooks/useCanvasEngine';

export const WorkspacePage: React.FC = () => {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workflowName, setWorkflowName] = useState('');

  const handleSave = async () => {
    if (!workflowName) {
      alert('Введите название workflow');
      return;
    }

    try {
      const res = await fetch('/api/workflows', {
        method: 'POST',
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
        alert(`Workflow сохранён! ID: ${data.id}`);
      } else {
        alert('Ошибка сохранения');
      }
    } catch (e) {
      console.error(e);
      alert('Ошибка сети');
    }
  };

  return (
    <IOSShell>
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-[var(--ios-border)] bg-[var(--ios-glass-dark)] backdrop-blur-md z-100">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold text-[var(--bronze-base)]">MRAK-OS Workspace</h1>
          <input
            type="text"
            placeholder="Workflow name..."
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-1 text-xs text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
          />
        </div>
        <button
          onClick={handleSave}
          className="px-4 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors"
        >
          Save Workflow
        </button>
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
        <div>🖱️ Double-click: Add node</div>
        <div>✋ Alt+Drag: Pan canvas</div>
        <div>🎯 Drag node: Move</div>
        <div>🔍 Scroll: Zoom</div>
      </div>
    </IOSShell>
  );
};
