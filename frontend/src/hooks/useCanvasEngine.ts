// frontend/src/hooks/useCanvasEngine.ts
import { useState, useCallback, useRef } from 'react';
// #CHANGED: Removed self-import (NodeData/EdgeData defined below)

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
  const [scale, setScale] = useState(1);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  
  const mouseStart = useRef({ x: 0, y: 0 });

  const handleWheel = useCallback((e: React.WheelEvent, containerRect: DOMRect) => {
    e.preventDefault();
    const factor = Math.pow(1.1, -e.deltaY / 300);
    const newScale = Math.min(Math.max(scale * factor, 0.2), 3);
    
    const mx = e.clientX - containerRect.left;
    const my = e.clientY - containerRect.top;

    setPan(prev => ({
      x: mx - (mx - prev.x) * (newScale / scale),
      y: my - (my - prev.y) * (newScale / scale),
    }));
    setScale(newScale);
  }, [scale]);

  const handlePanStart = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      setIsPanning(true);
      mouseStart.current = {
        x: e.clientX - pan.x,
        y: e.clientY - pan.y,
      };
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - mouseStart.current.x,
        y: e.clientY - mouseStart.current.y,
      });
    } else if (draggedNode) {
      setNodes(nodes.map(node => {
        if (node.node_id === draggedNode) {
          return {
            ...node,
            position_x: (e.clientX - pan.x) / scale - 110,
            position_y: (e.clientY - pan.y) / scale - 40,
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