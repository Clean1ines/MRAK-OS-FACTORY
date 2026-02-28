// frontend/src/components/ios/NodeListPanel.tsx
// ADDED: Sidebar panel for node list management (SRP extraction)

import React from 'react';
import type { NodeData } from '../../hooks/useCanvasEngine';
import { hashPosition, avoidCollisions } from '../../utils/deterministicRandom';

interface NodeListPanelProps {
  visible: boolean;
  onClose: () => void;
  nodes: NodeData[];
  onAddNode: (node: NodeData) => void;
}

type TabType = 'created' | 'available';

export const NodeListPanel: React.FC<NodeListPanelProps> = ({
  visible,
  onClose,
  nodes,
  onAddNode,
}) => {
  const [activeTab, setActiveTab] = React.useState<TabType>('created');

  if (!visible) return null;

  const handleAddFromList = (type: string) => {
    const basePos = hashPosition(type, 0, 1200, 800);
    const existingPositions = nodes.map(n => ({ x: n.position_x, y: n.position_y }));
    const finalPos = avoidCollisions(basePos, existingPositions);
    
    onAddNode({
      id: crypto.randomUUID(),
      node_id: crypto.randomUUID(),
      prompt_key: type,
      position_x: finalPos.x,
      position_y: finalPos.y,
      config: {},
    });
  };

  return (
    <div className="absolute top-20 right-6 w-80 bg-[var(--ios-glass)] backdrop-blur-md border border-[var(--ios-border)] rounded-lg shadow-[var(--shadow-heavy)] z-[1000]">
      <div className="flex items-center justify-between p-3 border-b border-[var(--ios-border)]">
        <h3 className="text-sm font-bold text-[var(--bronze-base)]">Nodes</h3>
        <button onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-main)]">
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      <div className="flex border-b border-[var(--ios-border)]">
        <button
          onClick={() => setActiveTab('created')}
          className={`flex-1 px-3 py-2 text-xs font-semibold ${
            activeTab === 'created' 
              ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]' 
              : 'text-[var(--text-muted)] hover:bg-[var(--ios-glass-bright)]'
          }`}
        >
          Created ({nodes.length})
        </button>
        <button
          onClick={() => setActiveTab('available')}
          className={`flex-1 px-3 py-2 text-xs font-semibold ${
            activeTab === 'available' 
              ? 'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]' 
              : 'text-[var(--text-muted)] hover:bg-[var(--ios-glass-bright)]'
          }`}
        >
          Available
        </button>
      </div>
      <div className="p-3 max-h-96 overflow-y-auto">
        {activeTab === 'created' ? (
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
                onClick={() => handleAddFromList(type)}
              >
                <div className="font-semibold text-[var(--bronze-bright)]">{type.replace(/_/g, ' ')}</div>
                <div className="text-[9px] text-[var(--text-muted)] mt-1">Click to add</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
