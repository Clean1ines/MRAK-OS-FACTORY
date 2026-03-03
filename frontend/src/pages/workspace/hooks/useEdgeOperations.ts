import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';

interface DeletingEdge {
  edgeId: string;
  sourceNode: string;
  targetNode: string;
}

export const useEdgeOperations = (
  data: ReturnType<typeof import('@/entities/workflow/api/useWorkflowsData').useWorkflowsData>,
  canvas: ReturnType<typeof import('@/widgets/workflow-editor/lib/useWorkflowCanvas').useWorkflowCanvas>,
  ui: ReturnType<typeof import('@/features/workflow/model/useWorkflowUI').useWorkflowUI>
) => {
  const [deletingEdge, setDeletingEdge] = useState<DeletingEdge | null>(null);

  const handleStartConnection = useCallback((nodeId: string) => {
    canvas.handleStartConnection(nodeId);
  }, [canvas]);

  const handleCompleteConnection = useCallback(async (targetNodeId: string) => {
    const sourceNodeId = canvas.connectingNode;
    if (!sourceNodeId || !ui.currentWorkflowId) return;

    const sourceNode = canvas.nodes.find(n => n.node_id === sourceNodeId);
    if (!sourceNode) {
      toast.error('Source node not found');
      return;
    }
    if (!sourceNode.recordId) {
      toast.error('Please wait for node to be saved before connecting');
      return;
    }

    try {
      await data.createEdge.mutateAsync({
        workflowId: ui.currentWorkflowId,
        sourceNode: sourceNodeId,
        targetNode: targetNodeId,
      });
      canvas.handleCompleteConnection(targetNodeId);
    } catch (err) {
      console.error('Failed to create edge:', err);
    }
  }, [canvas, data, ui.currentWorkflowId]);

  const handleDeleteEdge = useCallback(async (edgeId: string) => {
    try {
      await data.deleteEdge.mutateAsync(edgeId);
      canvas.setEdges(prev => prev.filter(e => e.id !== edgeId));
    } catch (err) {
      console.error('Failed to delete edge:', err);
    }
  }, [data, canvas]);

  const handleRequestDeleteEdge = useCallback((edgeId: string, sourceNode: string, targetNode: string) => {
    setDeletingEdge({ edgeId, sourceNode, targetNode });
  }, []);

  const confirmDeleteEdge = useCallback(async () => {
    if (!deletingEdge) return;
    await handleDeleteEdge(deletingEdge.edgeId);
    setDeletingEdge(null);
  }, [deletingEdge, handleDeleteEdge]);

  return {
    deletingEdge,
    setDeletingEdge,
    handleStartConnection,
    handleCompleteConnection,
    handleDeleteEdge,
    handleRequestDeleteEdge,
    confirmDeleteEdge,
  };
};
