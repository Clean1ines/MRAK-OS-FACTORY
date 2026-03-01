import React, { useState } from 'react';

interface IOSNodeProps {
  node: {
    node_id: string;
    prompt_key: string;
    position_x: number;
    position_y: number;
    config?: Record<string, unknown>;
    recordId?: string;
  };
  isSelected: boolean;
  isConnecting?: boolean;
  onDragStart: (nodeId: string, e: React.MouseEvent | React.TouchEvent, element: HTMLDivElement) => void;
  onStartConnection?: (nodeId: string) => void;
  onCompleteConnection?: (targetNodeId: string) => void;
  onEdit?: (recordId: string, promptKey: string, config: Record<string, unknown>) => void;
  onRequestDelete: (recordId: string | undefined, nodeId: string, name: string) => void;
}

export const IOSNode = React.forwardRef<HTMLDivElement, IOSNodeProps>(({
  node,
  isSelected,
  isConnecting = false,
  onDragStart,
  onStartConnection,
  onCompleteConnection,
  onEdit,
  onRequestDelete,
}, ref) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const previewText = (() => {
    const customPrompt = node.config?.custom_prompt;
    if (customPrompt == null) return null;
    if (typeof customPrompt === 'string') {
      return customPrompt.length > 80 ? customPrompt.substring(0, 80) + '...' : customPrompt;
    }
    try {
      const str = JSON.stringify(customPrompt);
      return str.length > 80 ? str.substring(0, 80) + '...' : str;
    } catch {
      return String(customPrompt).substring(0, 80) + '...';
    }
  })();

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit && node.recordId) {
      onEdit(node.recordId, node.prompt_key, node.config || {});
    }
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRequestDelete(node.recordId, node.node_id, node.prompt_key);
  };

  return (
    <div
      ref={ref}
      className={`
        absolute min-w-[220px] max-w-[280px] p-4 rounded-lg backdrop-blur-md border
        transition-[opacity,transform,border-color,box-shadow,ring-color,background-color] duration-200
        will-change-transform
        ${isSelected
          ? 'border-[var(--bronze-base)] shadow-[0_0_25px_var(--bronze-glow)]'
          : 'border-[var(--ios-border)] shadow-[var(--shadow-node)]'
        }
        ${isConnecting ? 'ring-2 ring-[var(--bronze-base)] ring-offset-2 ring-offset-black' : ''}
      `}
      style={{
        transform: `translate3d(${node.position_x}px, ${node.position_y}px, 0)`,
        background: 'linear-gradient(145deg, rgba(30,30,32,0.9), rgba(20,20,22,0.95))',
        transitionProperty: 'opacity, border-color, box-shadow, ring-color, background-color',
      }}
      onMouseDown={(e) => onDragStart(node.node_id, e, e.currentTarget)}
      onTouchStart={(e) => onDragStart(node.node_id, e, e.currentTarget)}
      onTouchMove={(e) => e.preventDefault()}
      onDoubleClick={handleDoubleClick}
    >
      <div className="flex items-center justify-between mb-2 pb-2 border-b border-[var(--ios-border)] pointer-events-none">
        <span className="text-[10px] text-[var(--bronze-base)] uppercase tracking-wider font-bold">
          {node.prompt_key}
        </span>
        <div className="flex items-center gap-1 pointer-events-auto">
          <button
            onClick={(e) => { e.stopPropagation(); setIsCollapsed(!isCollapsed); }}
            className="text-[var(--text-muted)] hover:text-[var(--bronze-base)] transition-colors p-1"
            title={isCollapsed ? "Expand" : "Collapse"}
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {isCollapsed ? (
                <polyline points="18 15 12 9 6 15" />
              ) : (
                <polyline points="18 9 12 15 6 9" />
              )}
            </svg>
          </button>
          {onStartConnection && onCompleteConnection && (
            <button
              onClick={(e) => { e.stopPropagation(); onStartConnection(node.node_id); }}
              className="w-4 h-4 rounded-full bg-[var(--bronze-dim)] hover:bg-[var(--bronze-base)] transition-colors flex items-center justify-center"
              title="Start connection"
            >
              <svg className="w-2 h-2 text-[var(--bronze-bright)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
          )}
          <button
            onClick={handleDeleteClick}
            className="text-[var(--text-muted)] hover:text-[var(--accent-danger)] transition-colors"
          >
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          <div className="text-sm font-semibold text-[var(--text-main)] mb-2 pointer-events-none">
            {node.prompt_key.replace(/_/g, ' ')}
          </div>

          {onCompleteConnection && (
            <div
              onClick={(e) => { e.stopPropagation(); onCompleteConnection(node.node_id); }}
              className="mt-2 pt-2 border-t border-[var(--ios-border)] text-[9px] text-[var(--text-muted)] hover:text-[var(--bronze-bright)] cursor-pointer transition-colors"
            >
              ⚡ Click to connect
            </div>
          )}

          <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)] mt-2 pointer-events-none">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-success)] animate-pulse" />
            Ready
          </div>

          {previewText && (
            <div className="mt-2 p-2 bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded text-[9px] text-[var(--text-secondary)] font-mono max-h-16 overflow-hidden pointer-events-none">
              {previewText}
            </div>
          )}
        </>
      )}
    </div>
  );
});
IOSNode.displayName = 'IOSNode';
