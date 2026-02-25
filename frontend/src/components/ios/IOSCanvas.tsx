// frontend/src/components/ios/IOSCanvas.tsx
import React, { useRef, useCallback, useState } from 'react';
import type { NodeData, EdgeData } from '../../hooks/useCanvasEngine';
import { useCanvasEngine } from '../../hooks/useCanvasEngine';
import { IOSNode } from './IOSNode';

interface IOSCanvasProps {
  nodes: NodeData[];
  edges: EdgeData[];
  onNodesChange: (nodes: NodeData[]) => void;
  onEdgesChange: (edges: EdgeData[]) => void;
  onAddCustomNode?: (x: number, y: number) => void;
}

export const IOSCanvas: React.FC<IOSCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onAddCustomNode,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; canvasX: number; canvasY: number } | null>(null);
  const [connectingNode, setConnectingNode] = useState<string | null>(null);
  
  const {
    pan,
    scale,
    selectedNode,
    handleWheel,
    handlePanStart,
    handleMouseMove,
    handleMouseUp,
    handleNodeDragStart,
    
  } = useCanvasEngine(nodes, edges, onNodesChange, onEdgesChange);

  const getCanvasCoords = useCallback((e: React.MouseEvent) => {
    if (!containerRef.current) return { x: 0, y: 0 };
    const rect = containerRef.current.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left - pan.x) / scale,
      y: (e.clientY - rect.top - pan.y) / scale,
    };
  }, [pan, scale]);

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const { x, y } = getCanvasCoords(e);
    
    if (onAddCustomNode) {
      onAddCustomNode(x, y);
    }
    
    setContextMenu(null);
  }, [getCanvasCoords, onAddCustomNode]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const { x, y } = getCanvasCoords(e);
    setContextMenu({ x: e.clientX, y: e.clientY, canvasX: x, canvasY: y });
  }, [getCanvasCoords]);

  // FIX #5: Add node from context menu
  const addNodeFromMenu = useCallback((prompt_key: string) => {
    if (!contextMenu) return;
    
    const newNode: NodeData = {
      id: crypto.randomUUID(),
      node_id: crypto.randomUUID(),
      prompt_key,
      position_x: contextMenu.canvasX,
      position_y: contextMenu.canvasY,
      config: {},
    };
    
    onNodesChange([...nodes, newNode]);
    setContextMenu(null);
  }, [contextMenu, nodes, onNodesChange]);

  // FIX #7: Start edge connection
  const handleStartConnection = useCallback((nodeId: string) => {
    setConnectingNode(nodeId);
  }, []);

  // FIX #7: Complete edge connection
  const handleCompleteConnection = useCallback((targetNodeId: string) => {
    if (connectingNode && connectingNode !== targetNodeId) {
      // Check if edge already exists
      const edgeExists = edges.some(
        e => e.source_node === connectingNode && e.target_node === targetNodeId
      );
      
      if (!edgeExists) {
        const newEdge: EdgeData = {
          id: crypto.randomUUID(),
          source_node: connectingNode,
          target_node: targetNodeId,
        };
        onEdgesChange([...edges, newEdge]);
      } else {
        console.log('Edge already exists');
      }
    }
    setConnectingNode(null);
  }, [connectingNode, edges, onEdgesChange]);

  const handleCloseMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const onWheelHandler = useCallback((e: React.WheelEvent) => {
    if (containerRef.current) {
      handleWheel(e, containerRef.current.getBoundingClientRect());
    }
  }, [handleWheel]);

  return (
    <div
      ref={containerRef}
      className="flex-1 relative overflow-hidden bg-[var(--bg-canvas)] cursor-crosshair"
      onWheel={onWheelHandler}
      onMouseDown={(e) => {
        handleCloseMenu();
        handlePanStart(e);
      }}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onDoubleClick={handleDoubleClick}
      onContextMenu={handleContextMenu}
    >
      <div className="absolute top-[15%] left-1/2 -translate-x-1/2 text-6xl font-bold text-[var(--bronze-base)] opacity-[0.03] select-none" style={{ pointerEvents: 'none' }}>
        CRAFT IN SILENCE
      </div>

      <div
        className="absolute w-full h-full origin-top-left"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
          pointerEvents: 'none',
        }}
      >
        <svg 
          className="absolute top-0 left-0 w-[20000px] h-[20000px] z-10"
          style={{ pointerEvents: 'none' }}
        >
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="var(--bronze-base)" />
            </marker>
            <filter id="glow-line" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {edges.map(edge => {
            const from = nodes.find(n => n.node_id === edge.source_node);
            const to = nodes.find(n => n.node_id === edge.target_node);
            if (!from || !to) return null;

            const x1 = from.position_x + 140;
            const y1 = from.position_y + 50;
            const x2 = to.position_x;
            const y2 = to.position_y + 50;
            const cp1x = x1 + (x2 - x1) * 0.5;

            return (
              <path
                key={edge.id}
                d={`M ${x1} ${y1} C ${cp1x} ${y1}, ${cp1x} ${y2}, ${x2} ${y2}`}
                stroke="var(--bronze-base)"
                strokeWidth="1.5"
                fill="none"
                filter="url(#glow-line)"
                markerEnd="url(#arrowhead)"
                opacity="0.6"
                style={{ pointerEvents: 'none' }}
              />
            );
          })}

          {/* Connection line in progress */}
          {connectingNode && (
            <line
              x1={nodes.find(n => n.node_id === connectingNode)?.position_x! + 140}
              y1={nodes.find(n => n.node_id === connectingNode)?.position_y! + 50}
              x2={(pan.x + 0) / scale}
              y2={(pan.y + 0) / scale}
              stroke="var(--bronze-base)"
              strokeWidth="1.5"
              strokeDasharray="5,5"
              opacity="0.6"
            />
          )}
        </svg>

        <div style={{ pointerEvents: 'auto' }}>
          {nodes.map(node => (
            <IOSNode
              key={node.node_id}
              node={node}
              isSelected={selectedNode === node.node_id}
              isConnecting={connectingNode === node.node_id}
              onDragStart={handleNodeDragStart}
              onDelete={(nodeId) => {
                onNodesChange(nodes.filter(n => n.node_id !== nodeId));
                onEdgesChange(edges.filter(e => e.source_node !== nodeId && e.target_node !== nodeId));
              }}
              onStartConnection={handleStartConnection}
              onCompleteConnection={handleCompleteConnection}
            />
          ))}
        </div>
      </div>

      {contextMenu && (
        <div
          className="absolute z-[1000] bg-[var(--ios-glass)] backdrop-blur-md border border-[var(--ios-border)] rounded-lg p-2 shadow-[var(--shadow-heavy)]"
          style={{ left: contextMenu.x, top: contextMenu.y, pointerEvents: 'auto' }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-[10px] text-[var(--text-muted)] mb-2 px-2">Add Node</div>
          <button
            onClick={() => addNodeFromMenu('IDEA_CLARIFIER')}
            className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--bronze-dim)] rounded text-[var(--text-main)]"
          >
            💡 Idea Clarifier
          </button>
          <button
            onClick={() => addNodeFromMenu('BUSINESS_REQ_GEN')}
            className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--bronze-dim)] rounded text-[var(--text-main)]"
          >
            📋 Business Req
          </button>
          <button
            onClick={() => addNodeFromMenu('CODE_GEN')}
            className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--bronze-dim)] rounded text-[var(--text-main)]"
          >
            💻 Code Gen
          </button>
        </div>
      )}

      <div className="absolute bottom-4 right-4 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-1 rounded border border-[var(--ios-border)]" style={{ pointerEvents: 'none' }}>
        {Math.round(scale * 100)}%
      </div>

      <div className="absolute bottom-20 left-6 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-3 py-2 rounded border border-[var(--ios-border)] pointer-events-none">
        <div>🖱️ Double-click: Custom node</div>
        <div>🖱️ Right-click: Quick add</div>
        <div>🔗 Click node port: Start connection</div>
        <div>✋ Alt+Drag: Pan canvas</div>
        <div>🎯 Drag node: Move</div>
        <div>🔍 Scroll: Zoom</div>
      </div>

      <div className="absolute top-4 right-4 text-[10px] text-[var(--bronze-dim)] bg-black/80 px-2 py-1 rounded font-mono border border-[var(--bronze-dim)]" style={{ pointerEvents: 'none' }}>
        Scale: {scale.toFixed(2)} | Pan: {Math.round(pan.x)}, {Math.round(pan.y)}
      </div>
    </div>
  );
};