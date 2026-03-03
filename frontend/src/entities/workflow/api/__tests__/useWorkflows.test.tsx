import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useWorkflows } from '../useWorkflows';

// Мокаем useWorkflowCanvas
const mockSetNodes = vi.fn();
const mockSetEdges = vi.fn();
vi.mock('@/widgets/workflow-editor/lib/useWorkflowCanvas', () => ({
  useWorkflowCanvas: vi.fn(() => ({
    nodes: [],
    edges: [],
    connectingNode: null,
    setNodes: mockSetNodes,
    setEdges: mockSetEdges,
    confirmAddCustomNode: vi.fn(),
    addNodeFromList: vi.fn(),
    handleCompleteConnection: vi.fn(),
  })),
}));

// Мокаем validateWorkflowAcyclic
vi.mock('@shared/lib', () => ({
  validateWorkflowAcyclic: () => ({ valid: true, cycles: [] }),
}));

const mockSessionStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(window, 'sessionStorage', { value: mockSessionStorage });

describe('useWorkflows', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
    window.sessionStorage.clear();
    window.sessionStorage.setItem('mrak_session_token', 'fake-token');
    global.fetch = vi.fn();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  const mockWorkflows = [
    { id: 'wf1', name: 'Workflow 1', description: 'Desc 1' },
    { id: 'wf2', name: 'Workflow 2', description: 'Desc 2' },
  ];

  const mockWorkflowDetail = {
    workflow: { id: 'wf1', name: 'Workflow 1', description: 'Desc 1' },
    nodes: [{ id: 'n1', node_id: 'n1', prompt_key: 'KEY', position_x: 100, position_y: 200, config: {} }],
    edges: [],
  };

  it('should fetch workflows when projectId provided', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflows,
    });

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    await waitFor(() => expect(result.current.isLoadingWorkflows).toBe(false));
    expect(result.current.workflows).toEqual(mockWorkflows);
  });

  it('should fetch workflow detail when currentWorkflowId changes', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflows,
    });
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflowDetail,
    });

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    await waitFor(() => expect(result.current.isLoadingWorkflows).toBe(false));

    act(() => {
      result.current.setCurrentWorkflowId('wf1');
    });

    await waitFor(() => expect(result.current.workflowName).toBe('Workflow 1'));

    // Проверяем, что setNodes был вызван хотя бы один раз с правильными данными
    expect(mockSetNodes).toHaveBeenCalled();
    const lastNodesCall = mockSetNodes.mock.calls[mockSetNodes.mock.calls.length - 1];
    expect(lastNodesCall[0]).toHaveLength(1);
    expect(lastNodesCall[0][0]).toMatchObject({
      node_id: 'n1',
      prompt_key: 'KEY',
    });

    // Проверяем edges
    expect(mockSetEdges).toHaveBeenCalledWith([]);
  });

  it('should create workflow via handleCreateWorkflow', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflows,
    });
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 'new-wf', name: 'New' }),
    });

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    await waitFor(() => expect(result.current.isLoadingWorkflows).toBe(false));

    let success: boolean;
    await act(async () => {
      success = await result.current.handleCreateWorkflow('New Workflow', 'Desc');
    });

    expect(success!).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer fake-token' }),
        body: JSON.stringify({ name: 'New Workflow', description: 'Desc', project_id: 'proj-123' }),
      })
    );
  });

  it('should save workflow via handleSave', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflows,
    });
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflowDetail,
    });
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: 'wf1' }),
    });

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    act(() => {
      result.current.setCurrentWorkflowId('wf1');
    });

    await waitFor(() => expect(result.current.workflowName).toBe('Workflow 1'));

    let saveResult: boolean;
    await act(async () => {
      saveResult = await result.current.handleSave();
    });

    expect(saveResult!).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/wf1',
      expect.objectContaining({ method: 'PUT' })
    );
  });

  it('should delete workflow', async () => {
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflows,
    });
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockWorkflowDetail,
    });
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });
    window.confirm = vi.fn(() => true);

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    act(() => {
      result.current.setCurrentWorkflowId('wf1');
    });

    await waitFor(() => expect(result.current.workflowName).toBe('Workflow 1'));

    let deleteResult: boolean;
    await act(async () => {
      deleteResult = await result.current.handleDelete('wf1');
    });

    expect(deleteResult!).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      '/api/workflows/wf1',
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});
