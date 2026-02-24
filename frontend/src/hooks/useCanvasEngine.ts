// frontend/src/hooks/useCanvasEngine.ts
import { useState, useCallback, useRef } from 'react';
// #ADDED: Import named constants
import {
  NODE_HALF_WIDTH,
  NODE_HALF_HEIGHT,
  VIEWPORT_SCALE_MIN,
  VIEWPORT_SCALE_MAX,
  ZOOM_SENSITIVITY,
  ZOOM_FACTOR,
  PAN_MOUSE_BUTTON,
  PAN_MODIFIER_KEY,
} from '../constants/canvas';

export interface NodeData {
  id: string;
  node_id: string;
  prompt_key: string;
  position_x: number;
  position_y: number;
  config?: Record<string, any>;
}

export interface EdgeData {
  id: string;
  source_node: string;
  target_node: string;
}

interface UseCanvasEngineReturn {
  pan: { x: number; y: number };
  scale: number;
  selectedNode: string | null;
  handleWheel: (e: React.WheelEvent, containerRect: DOMRect) => void;
  handlePanStart: (e: React.MouseEvent) => void;
  handleMouseMove: (e: React.MouseEvent) => void;
  handleMouseUp: () => void;
  handleNodeDragStart: (nodeId: string, e: React.MouseEvent) => void;
  setSelectedNode: (id: string | null) => void;
}

export const useCanvasEngine = (
  nodes: NodeData[],
  edges: EdgeData[],
  setNodes: (nodes: NodeData[]) => void,
  setEdges: (edges: EdgeData[]) => void
): UseCanvasEngineReturn => {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(VIEWPORT_SCALE_DEFAULT);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  
  const mouseStart = useRef({ x: 0, y: 0 });

  // #CHANGED: Use named constants instead of magic numbers
  const handleWheel = useCallback((e: React.WheelEvent, containerRect: DOMRect) => {
    e.preventDefault();
    const factor = Math.pow(ZOOM_FACTOR, -e.deltaY / ZOOM_SENSITIVITY);
    const newScale = Math.min(Math.max(scale * factor, VIEWPORT_SCALE_MIN), VIEWPORT_SCALE_MAX);
    
    const mx = e.clientX - containerRect.left;
    const my = e.clientY - containerRect.top;

    // Invariant: screen_pos = (world_pos × scale) + pan
    setPan(prev => ({
      x: mx - (mx - prev.x) * (newScale / scale),
      y: my - (my - prev.y) * (newScale / scale),
    }));
    setScale(newScale);
  }, [scale]);

  // #CHANGED: Use named constants for pan button
  const handlePanStart = useCallback((e: React.MouseEvent) => {
    if (e.button === PAN_MOUSE_BUTTON || (e.button === 0 && e.altKey === (PAN_MODIFIER_KEY === 'Alt'))) {
      setIsPanning(true);
      mouseStart.current = {
        x: e.clientX - pan.x,
        y: e.clientY - pan.y,
      };
    }
  }, [pan]);

  // #CHANGED: Use named constants for node centering
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - mouseStart.current.x,
        y: e.clientY - mouseStart.current.y,
      });
    } else if (draggedNode) {
      // Invariant: world_pos = (screen_pos - pan) / scale
      // Center node: subtract half dimensions
      setNodes(nodes.map(node => {
        if (node.node_id === draggedNode) {
          return {
            ...node,
            position_x: (e.clientX - pan.x) / scale - NODE_HALF_WIDTH,
            position_y: (e.clientY - pan.y) / scale - NODE_HALF_HEIGHT,
          };
        }
        return node;
      }));
    }
  }, [isPanning, draggedNode, pan, scale, nodes, setNodes]);

  const handleMouseUp = useCallback(() => {
    setIsPanning(false);
    setDraggedNode(null);
  }, []);

  const handleNodeDragStart = useCallback((nodeId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDraggedNode(nodeId);
    setSelectedNode(nodeId);
  }, []);

  return {
    pan,
    scale,
    selectedNode,
    handleWheel,
    handlePanStart,
    handleMouseMove,
    handleMouseUp,
    handleNodeDragStart,
    setSelectedNode,
  };
};