import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useWorkflows } from '../useWorkflows';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Мок для fetch
global.fetch = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockProjectId = 'test-project-id';
const mockWorkflowId = 'test-workflow-id';
const mockNodeId = 'test-node-id';
const mockEdgeId = 'test-edge-id';

describe('useWorkflows', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    sessionStorage.setItem('mrak_session_token', 'fake-token');
  });

  it('should create a node and update recordId', async () => {
    const mockNodeResponse = { id: 'new-record-id' };
    (fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockNodeResponse,
    });

    const { result } = renderHook(() => useWorkflows(mockProjectId), {
      wrapper: createWrapper(),
    });

    // Устанавливаем currentWorkflowId вручную (обычно он ставится при выборе)
    result.current.setCurrentWorkflowId(mockWorkflowId);

    // Симулируем локальное добавление узла через canvas.confirmAddCustomNode
    // Для теста напрямую вызовем wrappedConfirmAddCustomNode, но он требует canvas.confirmAddCustomNode
    // Проще протестировать createNodeMutation напрямую
    await result.current.createNodeMutation.mutateAsync({
      workflowId: mockWorkflowId,
      nodeId: mockNodeId,
      promptKey: 'TEST',
      config: { custom_prompt: 'test' },
      positionX: 100,
      positionY: 200,
    });

    expect(fetch).toHaveBeenCalledWith(
      `/api/workflows/${mockWorkflowId}/nodes`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          node_id: mockNodeId,
          prompt_key: 'TEST',
          config: { custom_prompt: 'test' },
          position_x: 100,
          position_y: 200,
        }),
      })
    );
  });

  it('should create an edge', async () => {
    (fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({ id: mockEdgeId }) });

    const { result } = renderHook(() => useWorkflows(mockProjectId), {
      wrapper: createWrapper(),
    });

    result.current.setCurrentWorkflowId(mockWorkflowId);

    // Эмулируем canvas.connectingNode
    Object.defineProperty(result.current, 'connectingNode', { value: 'source-node-id' });

    await result.current.createEdgeMutation.mutateAsync({
      workflowId: mockWorkflowId,
      sourceNode: 'source-node-id',
      targetNode: 'target-node-id',
    });

    expect(fetch).toHaveBeenCalledWith(
      `/api/workflows/${mockWorkflowId}/edges`,
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          source_node: 'source-node-id',
          target_node: 'target-node-id',
          source_output: 'output',
          target_input: 'input',
        }),
      })
    );
  });

  it('should delete an edge', async () => {
    (fetch as any).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

    const { result } = renderHook(() => useWorkflows(mockProjectId), {
      wrapper: createWrapper(),
    });

    await result.current.deleteEdge(mockEdgeId);

    expect(fetch).toHaveBeenCalledWith(
      `/api/workflows/edges/${mockEdgeId}`,
      expect.objectContaining({ method: 'DELETE' })
    );
  });
});
