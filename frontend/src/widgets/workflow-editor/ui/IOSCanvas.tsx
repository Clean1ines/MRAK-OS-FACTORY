import React, { useRef, useCallback, useState, useMemo, useEffect } from 'react';
import { useWorkflowStore } from '@/entities/workflow/store/workflowStore';
import { IOSNode } from '@/entities/node/ui/Node';
import { Edge } from '@/entities/edge/ui/Edge';
import { useCanvasEngine } from '../lib/useCanvasEngine';

interface IOSCanvasProps {
  onOpenCreateModal?: (x: number, y: number) => void;
  onOpenEditModal?: (nodeId: string) => void;
  onRequestDeleteNode?: (nodeId: string) => void;
  onRequestDeleteEdge?: (edgeId: string) => void;
}

export const IOSCanvas: React.FC<IOSCanvasProps> = ({
  onOpenCreateModal,
  onOpenEditModal,
  onRequestDeleteNode,
  onRequestDeleteEdge,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [connectingNode, setConnectingNode] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);

  const {
    handleWheel,
    handlePanStart,
    handleNodeDragStart,
    draggedNodeId,
    draggedNodePosition,
  } = useCanvasEngine();

  const visibleNodes = useWorkflowStore(state => state.graph.nodes);
  const edges = useWorkflowStore(state => state.graph.edges);
  const positions = useWorkflowStore(state => state.layout.positions);
  const viewport = useWorkflowStore(state => state.viewport);
  const selectedNodeId = useWorkflowStore(state => state.ui.selectedNodeId);
  const addEdge = useWorkflowStore(state => state.addEdge);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current || !connectingNode) return;
    const rect = containerRef.current.getBoundingClientRect();
    const worldX = (e.clientX - rect.left - viewport.cameraX) / viewport.zoom;
    const worldY = (e.clientY - rect.top - viewport.cameraY) / viewport.zoom;
    setMousePos({ x: worldX, y: worldY });
  }, [connectingNode, viewport]);

  // Сбрасываем позицию мыши при отключении режима соединения
  useEffect(() => {
    if (!connectingNode) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMousePos(null);
    }
  }, [connectingNode]);

  // Подписываемся на движение мыши только в режиме соединения
  useEffect(() => {
    if (connectingNode) {
      window.addEventListener('mousemove', handleMouseMove);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
      };
    }
  }, [connectingNode, handleMouseMove]);

  const handleNodeClick = useCallback((nodeId: string) => {
    if (connectingNode && connectingNode !== nodeId) {
      addEdge(connectingNode, nodeId);
      setConnectingNode(null);
      setMousePos(null);
    } else if (connectingNode === nodeId) {
      setConnectingNode(null);
      setMousePos(null);
    }
  }, [connectingNode, addEdge]);

  const handleBackgroundClick = useCallback((e: React.MouseEvent) => {
    if (e.target === containerRef.current) {
      setConnectingNode(null);
      setMousePos(null);
    }
  }, []);

  const edgeElements = useMemo(() => {
    return edges.map(edge => {
      const fromNode = visibleNodes.find(n => n.id === edge.source);
      const toNode = visibleNodes.find(n => n.id === edge.target);
      if (!fromNode || !toNode) return null;

      let fromPos = positions[edge.source];
      let toPos = positions[edge.target];
      if (edge.source === draggedNodeId && draggedNodePosition) {
        fromPos = draggedNodePosition;
      }
      if (edge.target === draggedNodeId && draggedNodePosition) {
        toPos = draggedNodePosition;
      }
      if (!fromPos || !toPos) return null;

      return (
        <Edge
          key={edge.id}
          edge={edge}
          fromPos={fromPos}
          toPos={toPos}
        />
      );
    });
  }, [edges, visibleNodes, positions, draggedNodeId, draggedNodePosition]);

  const connectionLine = useMemo(() => {
    if (!connectingNode) return null;
    const fromPos = positions[connectingNode];
    if (!fromPos) return null;
    const toPos = mousePos || {
      x: (viewport.cameraX + 0) / viewport.zoom,
      y: (viewport.cameraY + 0) / viewport.zoom,
    };
    return (
      <line
        x1={fromPos.x}
        y1={fromPos.y}
        x2={toPos.x}
        y2={toPos.y}
        stroke="var(--bronze-bright)"
        strokeWidth="1.5"
        strokeDasharray="5,5"
        opacity="0.8"
      />
    );
  }, [connectingNode, positions, mousePos, viewport]);

  const getCanvasCoords = useCallback((clientX: number, clientY: number) => {
    if (!containerRef.current) return { x: 0, y: 0 };
    const rect = containerRef.current.getBoundingClientRect();
    return {
      x: (clientX - rect.left - viewport.cameraX) / viewport.zoom,
      y: (clientY - rect.top - viewport.cameraY) / viewport.zoom,
    };
  }, [viewport]);

  const handleDoubleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onOpenCreateModal) {
      const { x, y } = getCanvasCoords(e.clientX, e.clientY);
      onOpenCreateModal(x, y);
    }
  }, [getCanvasCoords, onOpenCreateModal]);

  return (
    <div
      ref={containerRef}
      className="flex-1 relative overflow-hidden bg-[var(--bg-canvas)] cursor-crosshair"
      onWheel={(e) => {
        if (containerRef.current) {
          handleWheel(e, containerRef.current.getBoundingClientRect());
        }
      }}
      onMouseDown={handlePanStart}
      onTouchStart={handlePanStart}
      onDoubleClick={handleDoubleClick}
      onClick={handleBackgroundClick}
    >
      <div
        className="absolute w-full h-full origin-top-left"
        style={{
          transform: `translate3d(${viewport.cameraX}px, ${viewport.cameraY}px, 0) scale(${viewport.zoom})`,
          willChange: 'transform',
        }}
      >
        <svg className="absolute top-0 left-0 w-[20000px] h-[20000px]" style={{ pointerEvents: 'none' }}>
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
          {edgeElements}
          {connectionLine}
        </svg>

        <div style={{ pointerEvents: 'auto' }}>
          {visibleNodes.map(node => (
            <IOSNode
              key={node.id}
              node={node}
              position={positions[node.id]}
              edges={edges}
              allNodes={visibleNodes}
              isSelected={selectedNodeId === node.id}
              isConnecting={connectingNode === node.id}
              onDragStart={handleNodeDragStart}
              onEdit={onOpenEditModal || (() => {})}
              onStartConnection={() => setConnectingNode(node.id)}
              onNodeClick={handleNodeClick}
              onRequestDelete={onRequestDeleteNode || (() => {})}
              onRequestDeleteEdge={onRequestDeleteEdge || (() => {})}
            />
          ))}
        </div>
      </div>

      <div className="absolute bottom-4 right-4 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-1 rounded border border-[var(--ios-border)]">
        {Math.round(viewport.zoom * 100)}%
      </div>

      <div className="absolute top-4 right-4 text-[10px] text-[var(--bronze-dim)] bg-black/80 px-2 py-1 rounded font-mono border border-[var(--bronze-dim)]">
        Scale: {viewport.zoom.toFixed(2)} | Pan: {Math.round(viewport.cameraX)}, {Math.round(viewport.cameraY)}
      </div>
    </div>
  );
};