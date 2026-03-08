import { useState, useCallback, useRef, useEffect } from 'react';
import { useWorkflowStore } from '@/entities/workflow/store/workflowStore';
import {
  VIEWPORT_SCALE_MIN,
  VIEWPORT_SCALE_MAX,
  ZOOM_SENSITIVITY,
  ZOOM_FACTOR,
  PAN_MOUSE_BUTTON,
} from '@/shared/lib/constants/canvas';

export interface UseCanvasEngineReturn {
  handleWheel: (e: React.WheelEvent, containerRect: DOMRect) => void;
  handlePanStart: (e: React.MouseEvent | React.TouchEvent) => void;
  handleNodeDragStart: (nodeId: string, e: React.MouseEvent | React.TouchEvent, element: HTMLDivElement) => void;
  draggedNodeId: string | null;
  draggedNodePosition: { x: number; y: number } | null;
}

export const useCanvasEngine = (): UseCanvasEngineReturn => {
  const store = useWorkflowStore();
  const viewport = store.viewport;
  const positions = store.layout.positions;
  const moveNode = store.moveNode;
  const setViewport = store.setViewport;

  const [draggedNode, setDraggedNode] = useState<string | null>(null);
  const [draggedNodePosition, setDraggedNodePosition] = useState<{ x: number; y: number } | null>(null);

  const draggedElement = useRef<HTMLDivElement | null>(null);
  const startWorldPos = useRef({ x: 0, y: 0 });
  const startScreenPos = useRef({ x: 0, y: 0 });
  const startZoom = useRef(1);

  const viewportRef = useRef(viewport);
  useEffect(() => { viewportRef.current = viewport; }, [viewport]);

  const getClientCoords = (e: MouseEvent | TouchEvent | React.MouseEvent | React.TouchEvent): { x: number; y: number } => {
    if ('touches' in e && e.touches.length > 0) {
      return { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
    if ('clientX' in e) {
      return { x: e.clientX, y: e.clientY };
    }
    return { x: 0, y: 0 };
  };

  useEffect(() => {
    if (!draggedNode || !draggedElement.current) return;

    const element = draggedElement.current;
    const prevUserSelect = document.body.style.userSelect;
    const prevCursor = document.body.style.cursor;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'grabbing';

    const handleGlobalMove = (e: MouseEvent | TouchEvent): void => {
      e.preventDefault();
      const { x, y } = getClientCoords(e);
      const deltaScreenX = x - startScreenPos.current.x;
      const deltaScreenY = y - startScreenPos.current.y;
      const deltaWorldX = deltaScreenX / startZoom.current;
      const deltaWorldY = deltaScreenY / startZoom.current;

      const newWorldX = startWorldPos.current.x + deltaWorldX;
      const newWorldY = startWorldPos.current.y + deltaWorldY;

      element.style.transform = `translate3d(${newWorldX}px, ${newWorldY}px, 0)`;
      setDraggedNodePosition({ x: newWorldX, y: newWorldY });
    };

    const handleGlobalEnd = (): void => {
      const finalWorldX = parseFloat(element.style.transform.split('(')[1]?.split('px')[0] || '0');
      const finalWorldY = parseFloat(element.style.transform.split(',')[1]?.split('px')[0] || '0');

      moveNode(draggedNode, { x: finalWorldX, y: finalWorldY });

      setDraggedNode(null);
      setDraggedNodePosition(null);
      draggedElement.current = null;
      document.body.style.userSelect = prevUserSelect;
      document.body.style.cursor = prevCursor;
      window.removeEventListener('mousemove', handleGlobalMove);
      window.removeEventListener('mouseup', handleGlobalEnd);
      window.removeEventListener('touchmove', handleGlobalMove);
      window.removeEventListener('touchend', handleGlobalEnd);
    };

    const passiveOpts = { passive: false } as AddEventListenerOptions;
    window.addEventListener('mousemove', handleGlobalMove, passiveOpts);
    window.addEventListener('mouseup', handleGlobalEnd);
    window.addEventListener('touchmove', handleGlobalMove, passiveOpts);
    window.addEventListener('touchend', handleGlobalEnd);

    return () => {
      window.removeEventListener('mousemove', handleGlobalMove);
      window.removeEventListener('mouseup', handleGlobalEnd);
      window.removeEventListener('touchmove', handleGlobalMove);
      window.removeEventListener('touchend', handleGlobalEnd);
      document.body.style.userSelect = prevUserSelect;
      document.body.style.cursor = prevCursor;
    };
  }, [draggedNode, moveNode]);

  const handleNodeDragStart = useCallback((nodeId: string, e: React.MouseEvent | React.TouchEvent, element: HTMLDivElement): void => {
    e.stopPropagation();
    e.preventDefault();

    const pos = positions[nodeId];
    if (!pos) return;

    const { x, y } = getClientCoords(e);

    startWorldPos.current = pos;
    startScreenPos.current = { x, y };
    startZoom.current = viewport.zoom;
    draggedElement.current = element;
    setDraggedNode(nodeId);
    setDraggedNodePosition(pos);
    store.selectNode(nodeId);
  }, [positions, viewport.zoom, store]);

  const handleWheel = useCallback((e: React.WheelEvent, containerRect: DOMRect): void => {
    e.preventDefault();
    const factor = Math.pow(ZOOM_FACTOR, -e.deltaY / ZOOM_SENSITIVITY);
    const newScale = Math.min(Math.max(viewport.zoom * factor, VIEWPORT_SCALE_MIN), VIEWPORT_SCALE_MAX);
    const mx = e.clientX - containerRect.left;
    const my = e.clientY - containerRect.top;

    const newPan = {
      x: mx - (mx - viewport.cameraX) * (newScale / viewport.zoom),
      y: my - (my - viewport.cameraY) * (newScale / viewport.zoom),
    };

    setViewport(newScale, newPan.x, newPan.y);
  }, [viewport, setViewport]);

  const handlePanStart = useCallback((e: React.MouseEvent | React.TouchEvent): void => {
    const isMouse = 'button' in e;
    const button = isMouse ? (e as React.MouseEvent).button : -1;
    const isAlt = isMouse ? (e as React.MouseEvent).altKey : false;

    if (button === PAN_MOUSE_BUTTON || (button === 0 && isAlt)) {
      const { x: startX, y: startY } = getClientCoords(e);
      const prevUserSelect = document.body.style.userSelect;
      const prevCursor = document.body.style.cursor;
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'grab';

      const handleGlobalPanMove = (ev: MouseEvent | TouchEvent): void => {
        ev.preventDefault();
        const { x, y } = getClientCoords(ev);
        const newPan = {
          x: x - startX + viewport.cameraX,
          y: y - startY + viewport.cameraY,
        };
        setViewport(viewport.zoom, newPan.x, newPan.y);
      };

      const handleGlobalPanUp = (): void => {
        document.body.style.userSelect = prevUserSelect;
        document.body.style.cursor = prevCursor;
        window.removeEventListener('mousemove', handleGlobalPanMove);
        window.removeEventListener('mouseup', handleGlobalPanUp);
        window.removeEventListener('touchmove', handleGlobalPanMove);
        window.removeEventListener('touchend', handleGlobalPanUp);
      };

      const passiveOpts = { passive: false } as AddEventListenerOptions;
      window.addEventListener('mousemove', handleGlobalPanMove);
      window.addEventListener('mouseup', handleGlobalPanUp);
      window.addEventListener('touchmove', handleGlobalPanMove, passiveOpts);
      window.addEventListener('touchend', handleGlobalPanUp);
    }
  }, [viewport, setViewport]);

  return {
    handleWheel,
    handlePanStart,
    handleNodeDragStart,
    draggedNodeId: draggedNode,
    draggedNodePosition,
  };
};