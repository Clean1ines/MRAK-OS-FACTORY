// frontend/src/components/ios/IOSNode.tsx
import React from 'react';

interface IOSNodeProps {
  node: {
    node_id: string;
    prompt_key: string;
    position_x: number;
    position_y: number;
    config?: Record<string, any>;
  };
  isSelected: boolean;
  isConnecting?: boolean;
  onDragStart: (nodeId: string, e: React.MouseEvent) => void;
  onDelete: (nodeId: string) => void;
  onStartConnection?: (nodeId: string) => void;
  onCompleteConnection?: (targetNodeId: string) => void;
}

export const IOSNode: React.FC<IOSNodeProps> = ({
  node,
  isSelected,
  isConnecting = false,
  onDragStart,
  onDelete,
  onStartConnection,
  onCompleteConnection,
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
        ${isConnecting ? 'ring-2 ring-[var(--bronze-base)] ring-offset-2 ring-offset-black' : ''}
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
        <div className="flex items-center gap-1">
          {/* Connection port - FIX #7 */}
          {onStartConnection && onCompleteConnection && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStartConnection(node.node_id);
              }}
              className="w-4 h-4 rounded-full bg-[var(--bronze-dim)] hover:bg-[var(--bronze-base)] transition-colors flex items-center justify-center"
              title="Start connection"
            >
              <svg className="w-2 h-2 text-[var(--bronze-bright)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
          )}
          {/* Delete button */}
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
      </div>

      {/* Title */}
      <div className="text-sm font-semibold text-[var(--text-main)] mb-2">
        {node.prompt_key.replace(/_/g, ' ')}
      </div>

      {/* Connection target zone - FIX #7 */}
      {onCompleteConnection && (
        <div
          onClick={(e) => {
            e.stopPropagation();
            onCompleteConnection(node.node_id);
          }}
          className="mt-2 pt-2 border-t border-[var(--ios-border)] text-[9px] text-[var(--text-muted)] hover:text-[var(--bronze-bright)] cursor-pointer transition-colors"
        >
          ⚡ Click to connect
        </div>
      )}

      {/* Status */}
      <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)] mt-2">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-success)] animate-pulse" />
        Ready
      </div>

      {/* Custom prompt preview */}
      {node.config?.custom_prompt && (
        <div className="mt-2 p-2 bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded text-[9px] text-[var(--text-secondary)] font-mono max-h-16 overflow-hidden">
          {node.config.custom_prompt.substring(0, 80)}...
        </div>
      )}
    </div>
  );
};