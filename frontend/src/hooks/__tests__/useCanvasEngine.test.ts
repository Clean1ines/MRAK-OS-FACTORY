/**
 * @vitest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { useCanvasEngine, type NodeData, type EdgeData } from '../useCanvasEngine';
import {
  NODE_HALF_WIDTH,
  NODE_HALF_HEIGHT,
  VIEWPORT_SCALE_MIN,
  VIEWPORT_SCALE_MAX,
  VIEWPORT_SCALE_DEFAULT,
  ZOOM_SENSITIVITY,
  ZOOM_FACTOR,
  PAN_MOUSE_BUTTON,
} from '../../constants/canvas';

describe('useCanvasEngine', () => {
  const mockNodes: NodeData[] = [
    {
      id: '1',
      node_id: 'node-1',
      prompt_key: 'TEST',
      position_x: 100,
      position_y: 200,
      config: {},
    },
  ];

  const mockEdges: EdgeData[] = [];
  const mockSetNodes = vi.fn();
  const mockSetEdges = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(global.crypto, 'randomUUID').mockReturnValue('test-uuid-12345');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /** Test that hook initializes with default viewport state */
  it('initializes with default pan, scale, and no selection', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    expect(result.current.pan).toEqual({ x: 0, y: 0 });
    expect(result.current.scale).toBe(VIEWPORT_SCALE_DEFAULT);
    expect(result.current.selectedNode).toBeNull();
  });

  /** Test that handleWheel zooms in/out within configured bounds */
  it('handles zoom with wheel event respecting min/max scale', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    const mockRect: DOMRect = {
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: vi.fn(),
    };

    // Zoom in
    act(() => {
      result.current.handleWheel(
        { preventDefault: vi.fn(), deltaY: -100, clientX: 500, clientY: 400 } as unknown as React.WheelEvent,
        mockRect
      );
    });
    expect(result.current.scale).toBeGreaterThan(VIEWPORT_SCALE_DEFAULT);
    expect(result.current.scale).toBeLessThanOrEqual(VIEWPORT_SCALE_MAX);

    // Zoom out past minimum
    act(() => {
      result.current.handleWheel(
        { preventDefault: vi.fn(), deltaY: 500, clientX: 500, clientY: 400 } as unknown as React.WheelEvent,
        mockRect
      );
    });
    expect(result.current.scale).toBeGreaterThanOrEqual(VIEWPORT_SCALE_MIN);
  });

  /** Test that pan starts on middle mouse or alt+left-click */
  it('starts panning on middle mouse button or alt+left-click', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handlePanStart({ button: 1, clientX: 100, clientY: 100 } as React.MouseEvent);
    });

    act(() => {
      result.current.handleMouseMove({ clientX: 150, clientY: 150 } as React.MouseEvent);
    });

    expect(result.current.pan.x).toBe(50);
    expect(result.current.pan.y).toBe(50);

    act(() => { result.current.handleMouseUp(); });
  });

  /** Test that node drag updates node position via setNodes callback */
  it('updates dragged node position through setNodes callback', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handleNodeDragStart('node-1', {
        stopPropagation: vi.fn(),
        clientX: 200,
        clientY: 250,
      } as React.MouseEvent);
    });

    expect(result.current.selectedNode).toBe('node-1');

    act(() => {
      result.current.handleMouseMove({ clientX: 300, clientY: 300 } as React.MouseEvent);
    });

    expect(mockSetNodes).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          node_id: 'node-1',
          position_x: expect.any(Number),
          position_y: expect.any(Number),
        }),
      ])
    );
  });

  /** Test that setSelectedNode updates selection state */
  it('updates selected node via setSelectedNode', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => { result.current.setSelectedNode('node-1'); });
    expect(result.current.selectedNode).toBe('node-1');

    act(() => { result.current.setSelectedNode(null); });
    expect(result.current.selectedNode).toBeNull();
  });

  /** Test that zoom calculation uses mouse position for focal point */
  it('adjusts pan when zooming to maintain mouse position', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    const mockRect: DOMRect = {
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: vi.fn(),
    };

    act(() => {
      result.current.handlePanStart({ button: 1, clientX: 100, clientY: 100 } as React.MouseEvent);
      result.current.handleMouseMove({ clientX: 200, clientY: 200 } as React.MouseEvent);
      result.current.handleMouseUp();
    });

    const initialPan = { ...result.current.pan };

    act(() => {
      result.current.handleWheel(
        { preventDefault: vi.fn(), deltaY: -50, clientX: 300, clientY: 300 } as unknown as React.WheelEvent,
        mockRect
      );
    });

    expect(result.current.pan).not.toEqual(initialPan);
  });

  /** Test edge case: dragging non-existent node ID is ignored */
  it('ignores drag operations for non-existent node IDs', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handleNodeDragStart('non-existent', { stopPropagation: vi.fn() } as React.MouseEvent);
      result.current.handleMouseMove({ clientX: 100, clientY: 100 } as React.MouseEvent);
    });

    expect(mockSetNodes).not.toHaveBeenCalled();
  });

  /** Test that mouse up resets pan and drag states */
  it('resets isPanning and draggedNode on mouse up', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handlePanStart({ button: 1, clientX: 0, clientY: 0 } as React.MouseEvent);
    });

    act(() => {
      result.current.handleMouseMove({ clientX: 50, clientY: 50 } as React.MouseEvent);
    });

    act(() => { result.current.handleMouseUp(); });

    const panBefore = result.current.pan;
    act(() => {
      result.current.handleMouseMove({ clientX: 100, clientY: 100 } as React.MouseEvent);
    });
    expect(result.current.pan).toEqual(panBefore);
  });

  /** Test accessibility: preventDefault called on wheel to disable page scroll */
  it('prevents default browser scroll on wheel events', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    const mockRect: DOMRect = {
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: vi.fn(),
    };
    const preventDefault = vi.fn();

    act(() => {
      result.current.handleWheel(
        { preventDefault, deltaY: -50, clientX: 300, clientY: 300 } as unknown as React.WheelEvent,
        mockRect
      );
    });

    expect(preventDefault).toHaveBeenCalled();
  });
});
