import React, { useRef, useCallback, useState, useMemo, useEffect } from 'react';
import { useWorkflowStore } from '@/entities/workflow/store/workflowStore';
import { useVisibleNodes } from '@/entities/workflow/store/selectors';
import { IOSNode } from '@/entities/node/ui/Node';
import { Edge } from '@/entities/edge/ui/Edge';
import { NODE_HALF_WIDTH, NODE_HALF_HEIGHT } from '@/shared/lib/constants/canvas';

interface IOSCanvasProps {
  onOpenCreateModal?: (x: number, y: number) => void;
  onOpenEditModal?: (nodeId: string) => void;
}

export const IOSCanvas: React.FC<IOSCanvasProps> = ({
  onOpenCreateModal,
  onOpenEditModal,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; canvasX: number; canvasY: number } | null>(null);
  const [connectingNode, setConnectingNode] = useState<string | null>(null);

  // Store
  const visibleNodes = useWorkflowStore(state => state.graph.nodes);
  const edges = useWorkflowStore(state => state.graph.edges);
  const positions = useWorkflowStore(state => state.layout.positions);
  const viewport = useWorkflowStore(state => state.viewport);
  const selectedNodeId = useWorkflowStore(state => state.ui.selectedNodeId);
  const currentWorkflowId = useWorkflowStore(state => state.ui.currentWorkflowId);
  const moveNode = useWorkflowStore(state => state.moveNode);
  const addEdge = useWorkflowStore(state => state.addEdge);
  const updateNodeConfig = useWorkflowStore(state => state.updateNodeConfig);
  const removeNode = useWorkflowStore(state => state.removeNode);
  const removeEdge = useWorkflowStore(state => state.removeEdge);

  // Логи
  console.log('[IOSCanvas] render, currentWorkflowId:', currentWorkflowId);
  console.log('[IOSCanvas] nodes count:', visibleNodes.length);
  console.log('[IOSCanvas] edges count:', edges.length);

  useEffect(() => {
    console.log('[IOSCanvas] workflow changed to:', currentWorkflowId);
  }, [currentWorkflowId]);

  const getVisibleCanvasBounds = useCallback(() => {
    if (!containerRef.current) return null;
    const rect = containerRef.current.getBoundingClientRect();
    return {
      left: -viewport.cameraX / viewport.zoom,
      top: -viewport.cameraY / viewport.zoom,
      right: (rect.width - viewport.cameraX) / viewport.zoom,
      bottom: (rect.height - viewport.cameraY) / viewport.zoom,
    };
  }, [viewport]);

  const adjustToViewport = useCallback((x: number, y: number) => {
    const bounds = getVisibleCanvasBounds();
    if (!bounds) return { x, y };
    const nodeWidth = NODE_HALF_WIDTH * 2;
    const nodeHeight = NODE_HALF_HEIGHT * 2;
    let newX = x;
    let newY = y;
    if (bounds.right - bounds.left >= nodeWidth) {
      newX = Math.min(Math.max(x, bounds.left), bounds.right - nodeWidth);
    } else {
      newX = (bounds.left + bounds.right) / 2 - nodeWidth / 2;
    }
    if (bounds.bottom - bounds.top >= nodeHeight) {
      newY = Math.min(Math.max(y, bounds.top), bounds.bottom - nodeHeight);
    } else {
      newY = (bounds.top + bounds.bottom) / 2 - nodeHeight / 2;
    }
    return { x: newX, y: newY };
  }, [getVisibleCanvasBounds]);

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
    console.log('[IOSCanvas] double click at screen', e.clientX, e.clientY);
    if (onOpenCreateModal) {
      const { x, y } = getCanvasCoords(e.clientX, e.clientY);
      const { x: adjX, y: adjY } = adjustToViewport(x, y);
      console.log('[IOSCanvas] adjusted coords', adjX, adjY);
      onOpenCreateModal(adjX, adjY);
    } else {
      // Старое поведение (на случай обратной совместимости)
      const { x, y } = getCanvasCoords(e.clientX, e.clientY);
      const { x: adjX, y: adjY } = adjustToViewport(x, y);
      useWorkflowStore.getState().addNode(
        { type: 'prompt', promptKey: 'New Node', config: {} },
        { x: adjX, y: adjY }
      );
    }
  }, [getCanvasCoords, adjustToViewport, onOpenCreateModal]);

  const addNodeFromMenu = useCallback((type: string, promptKey: string) => {
    if (!contextMenu) return;
    const { x: adjX, y: adjY } = adjustToViewport(contextMenu.canvasX, contextMenu.canvasY);
    useWorkflowStore.getState().addNode(
      { type, promptKey, config: {} },
      { x: adjX, y: adjY }
    );
    setContextMenu(null);
  }, [contextMenu, adjustToViewport]);

  const handleNodeDragStart = useCallback((nodeId: string, e: React.MouseEvent | React.TouchEvent) => {
    e.stopPropagation();
    // Будет восстановлено позже
  }, []);

  const handleNodeDragStop = useCallback((nodeId: string, pos: { x: number; y: number }) => {
    moveNode(nodeId, pos);
  }, [moveNode]);

  const handleStartConnection = useCallback((nodeId: string) => {
    setConnectingNode(nodeId);
  }, []);

  const handleCompleteConnection = useCallback((targetNodeId: string) => {
    if (connectingNode && connectingNode !== targetNodeId) {
      addEdge(connectingNode, targetNodeId);
    }
    setConnectingNode(null);
  }, [connectingNode, addEdge]);

  const edgeElements = useMemo(() => {
    return edges.map(edge => {
      const fromPos = positions[edge.source];
      const toPos = positions[edge.target];
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
  }, [edges, positions]);

  const connectionLine = useMemo(() => {
    if (!connectingNode) return null;
    const fromPos = positions[connectingNode];
    if (!fromPos) return null;
    return (
      <line
        x1={fromPos.x + 140}
        y1={fromPos.y + 50}
        x2={(viewport.cameraX + 0) / viewport.zoom}
        y2={(viewport.cameraY + 0) / viewport.zoom}
        stroke="var(--bronze-base)"
        strokeWidth="1.5"
        strokeDasharray="5,5"
        opacity="0.6"
      />
    );
  }, [connectingNode, positions, viewport]);

  return (
    <div
      ref={containerRef}
      className="flex-1 relative overflow-hidden bg-[var(--bg-canvas)] cursor-crosshair touch-none"
      onDoubleClick={handleDoubleClick}
    >
      <div
        className="absolute w-full h-full origin-top-left"
        style={{
          transform: `translate3d(${viewport.cameraX}px, ${viewport.cameraY}px, 0) scale(${viewport.zoom})`,
          willChange: 'transform',
        }}
      >
        <svg className="absolute top-0 left-0 w-[20000px] h-[20000px] z-10" style={{ pointerEvents: 'none' }}>
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
              isSelected={selectedNodeId === node.id}
              isConnecting={connectingNode === node.id}
              onDragStart={handleNodeDragStart}
              onStartConnection={handleStartConnection}
              onCompleteConnection={handleCompleteConnection}
              onEdit={onOpenEditModal ? (id) => onOpenEditModal(id) : (id, promptKey, config) => updateNodeConfig(id, { promptKey, config })}
              onRequestDelete={(id) => removeNode(id)}
              onRequestDeleteEdge={(edgeId) => removeEdge(edgeId)}
              edges={edges}
            />
          ))}
        </div>
      </div>

      <div className="absolute bottom-4 right-4 text-[10px] text-[var(--text-muted)] bg-[var(--ios-glass-dark)] px-2 py-1 rounded border border-[var(--ios-border)]" style={{ pointerEvents: 'none' }}>
        {Math.round(viewport.zoom * 100)}%
      </div>

      <div className="absolute top-4 right-4 text-[10px] text-[var(--bronze-dim)] bg-black/80 px-2 py-1 rounded font-mono border border-[var(--bronze-dim)]" style={{ pointerEvents: 'none' }}>
        Scale: {viewport.zoom.toFixed(2)} | Pan: {Math.round(viewport.cameraX)}, {Math.round(viewport.cameraY)}
      </div>
    </div>
  );
};