import { useState, useCallback, useRef, useEffect } from 'react';
import {
  VIEWPORT_SCALE_MIN,
  VIEWPORT_SCALE_MAX,
  VIEWPORT_SCALE_DEFAULT,
  ZOOM_SENSITIVITY,
  ZOOM_FACTOR,
  PAN_MOUSE_BUTTON,
} from '../constants/canvas';

export interface NodeData {
  id: string;
  node_id: string;
  prompt_key: string;
  position_x: number;
  position_y: number;
  config?: Record<string, unknown>;
  recordId?: string; // ADDED: идентификатор записи в БД
}

export interface EdgeData {
  id: string;
  source_node: string;
  target_node: string;
}

export interface UseCanvasEngineReturn {
  pan: { x: number; y: number };
  scale: number;
  selectedNode: string | null;
  handleWheel: (e: React.WheelEvent, containerRect: DOMRect) => void;
  handlePanStart: (e: React.MouseEvent | React.TouchEvent) => void;
  handleNodeDragStart: (nodeId: string, e: React.MouseEvent | React.TouchEvent) => void;
  setSelectedNode: (id: string | null) => void;
}

/**
 * Custom hook for canvas engine: pan, zoom, node drag, selection.
 * @param {NodeData[]} nodes - Current nodes array
 * @param {EdgeData[]} _edges - Current edges array (unused, kept for API symmetry)
 * @param {(nodes: NodeData[]) => void} setNodes - State setter for nodes (direct value only)
 * @param {(edges: EdgeData[]) => void} _setEdges - State setter for edges (unused)
 * @returns {UseCanvasEngineReturn} Canvas interaction handlers and state
 */
export const useCanvasEngine = (
  nodes: NodeData[],
  _edges: EdgeData[],
  setNodes: (nodes: NodeData[]) => void,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _setEdges: (edges: EdgeData[]) => void
): UseCanvasEngineReturn => {
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(VIEWPORT_SCALE_DEFAULT);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [draggedNode, setDraggedNode] = useState<string | null>(null);

  const panRef = useRef(pan);
  const scaleRef = useRef(scale);
  const nodesRef = useRef<NodeData[]>(nodes);

  useEffect(() => { panRef.current = pan; }, [pan]);
  useEffect(() => { scaleRef.current = scale; }, [scale]);
  useEffect(() => { nodesRef.current = nodes; }, [nodes]);

  const dragStartScreen = useRef({ x: 0, y: 0 });
  const dragStartWorld = useRef({ x: 0, y: 0 });
  const dragStartScale = useRef(1);

  useEffect(() => {
    if (!draggedNode) return;

    const prevUserSelect = document.body.style.userSelect;
    const prevCursor = document.body.style.cursor;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'grabbing';

    const getClientCoords = (e: MouseEvent | TouchEvent): { x: number; y: number } => {
      if ('touches' in e && e.touches.length > 0) {
        return { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
      const mouseEvent = e as MouseEvent;
      return { x: mouseEvent.clientX, y: mouseEvent.clientY };
    };

    const handleGlobalMove = (e: MouseEvent | TouchEvent): void => {
      e.preventDefault();
      const { x, y } = getClientCoords(e);
      const deltaScreenX = x - dragStartScreen.current.x;
      const deltaScreenY = y - dragStartScreen.current.y;
      const deltaWorldX = deltaScreenX / dragStartScale.current;
      const deltaWorldY = deltaScreenY / dragStartScale.current;
      const newWorldX = dragStartWorld.current.x + deltaWorldX;
      const newWorldY = dragStartWorld.current.y + deltaWorldY;

      const updatedNodes: NodeData[] = nodesRef.current.map((node: NodeData): NodeData =>
        node.node_id === draggedNode
          ? { ...node, position_x: newWorldX, position_y: newWorldY }
          : node
      );
      setNodes(updatedNodes);
    };

    const handleGlobalEnd = (): void => {
      setDraggedNode(null);
      document.body.style.userSelect = prevUserSelect;
      document.body.style.cursor = prevCursor;
      window.removeEventListener('mousemove', handleGlobalMove as EventListener);
      window.removeEventListener('mouseup', handleGlobalEnd);
      window.removeEventListener('touchmove', handleGlobalMove as EventListener);
      window.removeEventListener('touchend', handleGlobalEnd);
    };

    const passiveOpts = { passive: false } as AddEventListenerOptions;
    window.addEventListener('mousemove', handleGlobalMove as EventListener, passiveOpts);
    window.addEventListener('mouseup', handleGlobalEnd);
    window.addEventListener('touchmove', handleGlobalMove as EventListener, passiveOpts);
    window.addEventListener('touchend', handleGlobalEnd);

    return () => {
      window.removeEventListener('mousemove', handleGlobalMove as EventListener);
      window.removeEventListener('mouseup', handleGlobalEnd);
      window.removeEventListener('touchmove', handleGlobalMove as EventListener);
      window.removeEventListener('touchend', handleGlobalEnd);
      document.body.style.userSelect = prevUserSelect;
      document.body.style.cursor = prevCursor;
    };
  }, [draggedNode, setNodes]);

  const handleWheel = useCallback((e: React.WheelEvent, containerRect: DOMRect): void => {
    e.preventDefault();
    const factor = Math.pow(ZOOM_FACTOR, -e.deltaY / ZOOM_SENSITIVITY);
    const newScale = Math.min(Math.max(scaleRef.current * factor, VIEWPORT_SCALE_MIN), VIEWPORT_SCALE_MAX);
    const mx = e.clientX - containerRect.left;
    const my = e.clientY - containerRect.top;

    setPan(prev => {
      const newPan = {
        x: mx - (mx - prev.x) * (newScale / scaleRef.current),
        y: my - (my - prev.y) * (newScale / scaleRef.current),
      };
      panRef.current = newPan;
      return newPan;
    });
    setScale(newScale);
    scaleRef.current = newScale;
  }, []);

  const handlePanStart = useCallback((e: React.MouseEvent | React.TouchEvent): void => {
    const isMouse = 'button' in e;
    const button = isMouse ? (e as React.MouseEvent).button : -1;
    const isAlt = isMouse ? (e as React.MouseEvent).altKey : false;

    if (button === PAN_MOUSE_BUTTON || (button === 0 && isAlt)) {
      const getClientCoords = (ev: MouseEvent | TouchEvent): { x: number; y: number } => {
        if ('touches' in ev && ev.touches.length > 0) {
          return { x: ev.touches[0].clientX, y: ev.touches[0].clientY };
        }
        const mouseEvent = ev as MouseEvent;
        return { x: mouseEvent.clientX, y: mouseEvent.clientY };
      };

      const { x: startX, y: startY } = getClientCoords(e as unknown as MouseEvent | TouchEvent);
      const prevUserSelect = document.body.style.userSelect;
      const prevCursor = document.body.style.cursor;
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'grab';

      const handleGlobalPanMove = (ev: MouseEvent | TouchEvent): void => {
        ev.preventDefault();
        const { x, y } = getClientCoords(ev);
        const newPan = {
          x: x - startX + panRef.current.x,
          y: y - startY + panRef.current.y,
        };
        setPan(newPan);
        panRef.current = newPan;
      };

      const handleGlobalPanUp = (): void => {
        document.body.style.userSelect = prevUserSelect;
        document.body.style.cursor = prevCursor;
        window.removeEventListener('mousemove', handleGlobalPanMove as EventListener);
        window.removeEventListener('mouseup', handleGlobalPanUp);
        window.removeEventListener('touchmove', handleGlobalPanMove as EventListener);
        window.removeEventListener('touchend', handleGlobalPanUp);
      };

      const passiveOpts = { passive: false } as AddEventListenerOptions;
      window.addEventListener('mousemove', handleGlobalPanMove as EventListener);
      window.addEventListener('mouseup', handleGlobalPanUp);
      window.addEventListener('touchmove', handleGlobalPanMove as EventListener, passiveOpts);
      window.addEventListener('touchend', handleGlobalPanUp);
    }
  }, []);

  const handleNodeDragStart = useCallback((nodeId: string, e: React.MouseEvent | React.TouchEvent): void => {
    e.stopPropagation();
    e.preventDefault();

    const node = nodes.find(n => n.node_id === nodeId);
    if (!node) return;

    const getClientCoords = (): { x: number; y: number } => {
      if ('touches' in e && e.touches.length > 0) {
        return { x: e.touches[0].clientX, y: e.touches[0].clientY };
      }
      const mouseEvent = e as React.MouseEvent;
      return { x: mouseEvent.clientX, y: mouseEvent.clientY };
    };

    const { x, y } = getClientCoords();

    setDraggedNode(nodeId);
    setSelectedNode(nodeId);
    dragStartScreen.current = { x, y };
    dragStartWorld.current = { x: node.position_x, y: node.position_y };
    dragStartScale.current = scaleRef.current;
  }, [nodes]);

  return {
    pan,
    scale,
    selectedNode,
    handleWheel,
    handlePanStart,
    handleNodeDragStart,
    setSelectedNode,
  };
};
