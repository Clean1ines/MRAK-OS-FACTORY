import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useWorkflows } from '../useWorkflows';
import { client } from '../../api/client';
import toast from 'react-hot-toast';

// Мокаем модули
vi.mock('../../api/client');
vi.mock('react-hot-toast');
vi.mock('../../utils/graphUtils', () => ({
  validateWorkflowAcyclic: () => ({ valid: true, cycles: [] }),
}));

// Мокаем sessionStorage
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
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  const mockWorkflows = [
    { id: 'wf1', name: 'Workflow 1', description: 'Desc 1' },
    { id: 'wf2', name: 'Workflow 2', description: 'Desc 2' },
  ];

  const mockWorkflowDetail = {
    workflow: { id: 'wf1', name: 'Workflow 1' },
    nodes: [{ node_id: 'n1', prompt_key: 'KEY', position_x: 100, position_y: 200, config: {} }],
    edges: [],
  };

  it('should fetch workflows when projectId provided', async () => {
    (client.GET as any).mockImplementation((path: string) => {
      if (path === '/api/workflows') {
        return Promise.resolve({ data: mockWorkflows, error: null });
      }
      return Promise.reject();
    });

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    await waitFor(() => expect(result.current.isLoadingWorkflows).toBe(false));
    expect(result.current.workflows).toEqual(mockWorkflows);
  });

  it('should fetch workflow detail when currentWorkflowId changes', async () => {
    (client.GET as any).mockImplementation((path: string) => {
      if (path === '/api/workflows') {
        return Promise.resolve({ data: mockWorkflows, error: null });
      }
      if (path === '/api/workflows/{workflow_id}') {
        return Promise.resolve({ data: mockWorkflowDetail, error: null });
      }
      return Promise.reject();
    });

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    await waitFor(() => expect(result.current.isLoadingWorkflows).toBe(false));

    result.current.setCurrentWorkflowId('wf1');

    await waitFor(() => expect(result.current.workflowName).toBe('Workflow 1'));
    expect(result.current.nodes).toHaveLength(1);
    expect(result.current.edges).toHaveLength(0);
  });

  it('should create workflow via handleCreateWorkflow', async () => {
    (client.GET as any).mockResolvedValue({ data: mockWorkflows, error: null });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'new-wf', name: 'New' }),
    });
    global.fetch = fetchMock as any;

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    await waitFor(() => expect(result.current.isLoadingWorkflows).toBe(false));

    const success = await result.current.handleCreateWorkflow('New Workflow', 'Desc');
    expect(success).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/workflows',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer fake-token' }),
        body: JSON.stringify({ name: 'New Workflow', description: 'Desc', project_id: 'proj-123' }),
      })
    );
  });

  it('should save workflow via handleSave', async () => {
    (client.GET as any).mockImplementation((path: string) => {
      if (path === '/api/workflows') return Promise.resolve({ data: mockWorkflows, error: null });
      if (path === '/api/workflows/{workflow_id}') return Promise.resolve({ data: mockWorkflowDetail, error: null });
      return Promise.reject();
    });

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 'wf1' }),
    });
    global.fetch = fetchMock as any;

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    result.current.setCurrentWorkflowId('wf1');
    await waitFor(() => expect(result.current.workflowName).toBe('Workflow 1'));

    const saveResult = await result.current.handleSave();
    expect(saveResult).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/workflows/wf1',
      expect.objectContaining({ method: 'PUT' })
    );
  });

  it('should delete workflow', async () => {
    (client.GET as any).mockImplementation((path: string) => {
      if (path === '/api/workflows') return Promise.resolve({ data: mockWorkflows, error: null });
      if (path === '/api/workflows/{workflow_id}') return Promise.resolve({ data: mockWorkflowDetail, error: null });
      return Promise.reject();
    });
    (client.DELETE as any).mockResolvedValue({ error: null });
    window.confirm = vi.fn(() => true);

    const { result } = renderHook(() => useWorkflows('proj-123'), { wrapper });

    result.current.setCurrentWorkflowId('wf1');
    await waitFor(() => expect(result.current.workflowName).toBe('Workflow 1'));

    const deleteResult = await result.current.handleDelete();
    expect(deleteResult).toBe(true);
    expect(client.DELETE).toHaveBeenCalledWith('/api/workflows/{workflow_id}', {
      params: { path: { workflow_id: 'wf1' } },
    });
  });
});
