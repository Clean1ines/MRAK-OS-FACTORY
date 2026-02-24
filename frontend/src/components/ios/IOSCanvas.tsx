// frontend/src/components/ios/IOSCanvas.tsx
import React, { useRef, useCallback } from 'react';
import { useCanvasEngine, NodeData, EdgeData } from '../../hooks/useCanvasEngine';
import { IOSNode } from './IOSNode';

interface IOSCanvasProps {
  nodes: NodeData[];
  edges: EdgeData[];
  onNodesChange: (nodes: NodeData[]) => void;
  onEdgesChange: (edges: EdgeData[]) => void;
}

export const IOSCanvas: React.FC<IOSCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const {
    pan, scale, selectedNode,
    handleWheel, handlePanStart, handleMouseMove, handleMouseUp,
    handleNodeDragStart, addNode, removeNode,
    setNodes, setEdges,
  } = useCanvasEngine();

  // Sync with parent
  React.useEffect(() => {
    onNodesChange(nodes);
  }, [nodes, onNodesChange]);

  React.useEffect(() => {
    onEdgesChange(edges);
  }, [edges, onEdgesChange]);

  // Add node on double click
  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    if (e.target !== containerRef.current) return;
    
    const rect = containerRef.current!.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / scale;
    const y = (e.clientY - rect.top - pan.y) / scale;
    
    addNode('IDEA_CLARIFIER', x, y);
  }, [pan, scale, addNode]);

  return (
    <div
      ref={containerRef}
      className="flex-1 relative overflow-hidden bg-[var(--bg-canvas)] cursor-crosshair"
      onWheel={handleWheel}
      onMouseDown={handlePanStart}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onDoubleClick={handleDoubleClick}
    >
      {/* Watermark */}
      <div className="absolute top-[15%] left-1/2 -translate-x-1/2 text-6xl font-bold text-[var(--bronze-base)] opacity-[0.03] pointer-events-none select-none">
        CRAFT IN SILENCE
      </div>

      {/* Viewport */}
      <div
        className="absolute w-full h-full origin-top-left"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
        }}
      >
        {/* SVG Connections */}
        <svg className="absolute top-0 left-0 w-[20000px] h-[20000px] pointer-events-none z-10">
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
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
              />
            );
          })}
        </svg>

        {/* Nodes */}
        {nodes.map(node => (
          <IOSNode
            key={node.node_id}
            node={node}
            isSelected={selectedNode === node.node_id}
            onDragStart={handleNodeDragStart}
            onDelete={removeNode}
          />
        ))}
      </div>

      {/* Scale indicator */}
      <div className="absolute bottom-4 right-4 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-1 rounded border border-[var(--ios-border)]">
        {Math.round(scale * 100)}%
      </div>
    </div>
  );
};
