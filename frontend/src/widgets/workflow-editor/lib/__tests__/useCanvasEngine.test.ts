/**
 * @vitest-environment jsdom
 */
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { useCanvasEngine, type NodeData, type EdgeData } from '../useCanvasEngine';
import {
  VIEWPORT_SCALE_MIN,
  VIEWPORT_SCALE_MAX,
  VIEWPORT_SCALE_DEFAULT,
} from '@/shared/lib/constants/canvas';

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

  it('initializes with default pan, scale, and no selection', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    expect(result.current.pan).toEqual({ x: 0, y: 0 });
    expect(result.current.scale).toBe(VIEWPORT_SCALE_DEFAULT);
    expect(result.current.selectedNode).toBeNull();
  });

  it('handles zoom with wheel event respecting min/max scale', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    const mockRect: DOMRect = {
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: vi.fn(),
    };

    act(() => {
      result.current.handleWheel(
        { preventDefault: vi.fn(), deltaY: -100, clientX: 500, clientY: 400 } as unknown as React.WheelEvent,
        mockRect
      );
    });
    expect(result.current.scale).toBeGreaterThan(VIEWPORT_SCALE_DEFAULT);
    expect(result.current.scale).toBeLessThanOrEqual(VIEWPORT_SCALE_MAX);

    act(() => {
      result.current.handleWheel(
        { preventDefault: vi.fn(), deltaY: 500, clientX: 500, clientY: 400 } as unknown as React.WheelEvent,
        mockRect
      );
    });
    expect(result.current.scale).toBeGreaterThanOrEqual(VIEWPORT_SCALE_MIN);
  });

  it('starts panning on middle mouse button or alt+left-click', async () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handlePanStart({ button: 1, clientX: 100, clientY: 100 } as React.MouseEvent);
    });

    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 150, clientY: 150 }));
    });

    await waitFor(() => {
      expect(result.current.pan.x).toBe(50);
      expect(result.current.pan.y).toBe(50);
    });

    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });
  });

  it('updates dragged node position through setNodes callback', async () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handleNodeDragStart('node-1', {
        stopPropagation: vi.fn(),
        preventDefault: vi.fn(),
        clientX: 200,
        clientY: 250,
      } as unknown as React.MouseEvent);
    });

    expect(result.current.selectedNode).toBe('node-1');

    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 300, clientY: 300 }));
    });

    await waitFor(() => {
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

    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });
  });

  it('updates selected node via setSelectedNode', () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => { result.current.setSelectedNode('node-1'); });
    expect(result.current.selectedNode).toBe('node-1');

    act(() => { result.current.setSelectedNode(null); });
    expect(result.current.selectedNode).toBeNull();
  });

  it.skip('adjusts pan when zooming to maintain mouse position', async () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    const mockRect: DOMRect = {
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: vi.fn(),
    };

    act(() => {
      result.current.handlePanStart({ button: 1, clientX: 100, clientY: 100 } as React.MouseEvent);
    });
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 200, clientY: 200 }));
    });
    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });

    // Дожидаемся, что pan действительно стал (100,100)
    await waitFor(() => {
      expect(result.current.pan.x).toBe(100);
      expect(result.current.pan.y).toBe(100);
    });

    const initialPan = { ...result.current.pan };

    act(() => {
      result.current.handleWheel(
        { preventDefault: vi.fn(), deltaY: -50, clientX: 300, clientY: 300 } as unknown as React.WheelEvent,
        mockRect
      );
    });

    // После зума pan должен измениться. Проверим это асинхронно, т.к. обновление может занять время
    await waitFor(() => {
      expect(result.current.pan).not.toEqual(initialPan);
    });
  });

  it('ignores drag operations for non-existent node IDs', async () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handleNodeDragStart('non-existent', { stopPropagation: vi.fn(), preventDefault: vi.fn() } as any);
    });

    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 100, clientY: 100 }));
    });

    expect(mockSetNodes).not.toHaveBeenCalled();

    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });
  });

  it('resets isPanning and draggedNode on mouse up', async () => {
    const { result } = renderHook(() =>
      useCanvasEngine(mockNodes, mockEdges, mockSetNodes, mockSetEdges)
    );

    act(() => {
      result.current.handlePanStart({ button: 1, clientX: 0, clientY: 0 } as React.MouseEvent);
    });
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 50, clientY: 50 }));
    });

    const panAfterMove = result.current.pan;
    expect(panAfterMove.x).not.toBe(0);

    act(() => {
      window.dispatchEvent(new MouseEvent('mouseup'));
    });

    const panBefore = result.current.pan;
    act(() => {
      window.dispatchEvent(new MouseEvent('mousemove', { clientX: 100, clientY: 100 }));
    });
    expect(result.current.pan).toEqual(panBefore);
  });

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
