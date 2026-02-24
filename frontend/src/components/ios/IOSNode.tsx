// frontend/src/components/ios/IOSNode.tsx
import React from 'react';

interface IOSNodeProps {
  node: {
    node_id: string;
    prompt_key: string;
    position_x: number;
    position_y: number;
  };
  isSelected: boolean;
  onDragStart: (nodeId: string, e: React.MouseEvent) => void;
  onDelete: (nodeId: string) => void;
}

export const IOSNode: React.FC<IOSNodeProps> = ({
  node,
  isSelected,
  onDragStart,
  onDelete,
}) => {
  return (
    <div
      className={`
        absolute min-w-[220px] max-w-[280px] p-4 rounded-lg
        backdrop-blur-md border transition-all duration-300
        ${isSelected 
          ? 'border-[var(--bronze-base)] shadow-[0_0_25px_var(--bronze-glow)]' 
          : 'border-[var(--ios-border)] shadow-[var(--shadow-node)]'
        }
      `}
      style={{
        left: node.position_x,
        top: node.position_y,
        background: 'linear-gradient(145deg, rgba(30,30,32,0.9), rgba(20,20,22,0.95))',
      }}
      onMouseDown={(e) => onDragStart(node.node_id, e)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2 pb-2 border-b border-[var(--ios-border)]">
        <span className="text-[10px] text-[var(--bronze-base)] uppercase tracking-wider font-bold">
          {node.prompt_key}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(node.node_id);
          }}
          className="text-[var(--text-muted)] hover:text-[var(--accent-danger)] transition-colors"
        >
          <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Title */}
      <div className="text-sm font-semibold text-[var(--text-main)] mb-2">
        {node.prompt_key.replace(/_/g, ' ')}
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-success)] animate-pulse" />
        Ready
      </div>
    </div>
  );
};
