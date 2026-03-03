import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { NodeData } from '@shared/lib';

interface EditingNode {
  recordId: string;
  promptKey: string;
  config: Record<string, unknown>;
}

interface DeletingNode {
  recordId?: string;
  nodeId: string;
  name: string;
}

export const useNodeOperations = (
  data: ReturnType<typeof import('@/entities/workflow/api/useWorkflowsData').useWorkflowsData>,
  canvas: ReturnType<typeof import('@/widgets/workflow-editor/lib/useWorkflowCanvas').useWorkflowCanvas>,
  ui: ReturnType<typeof import('@/features/workflow/model/useWorkflowUI').useWorkflowUI>
) => {
  const [editingNode, setEditingNode] = useState<EditingNode | null>(null);
  const [deletingNode, setDeletingNode] = useState<DeletingNode | null>(null);

  const handleAddCustomNode = useCallback((x: number, y: number) => {
    canvas.handleAddCustomNode(x, y);
  }, [canvas]);

  const handleConfirmAddCustomNode = useCallback(async () => {
    const newNode = await canvas.confirmAddCustomNode();
    if (!newNode || !ui.currentWorkflowId) return;
    try {
      const result = await data.createNode.mutateAsync({
        workflowId: ui.currentWorkflowId,
        nodeId: newNode.node_id,
        promptKey: newNode.prompt_key,
        config: newNode.config || {},
        positionX: newNode.position_x,
        positionY: newNode.position_y,
      });
      canvas.setNodes(prev =>
        prev.map(n => (n.node_id === newNode.node_id ? { ...n, recordId: result.id } : n))
      );
    } catch (err) {
      console.error('Failed to create node:', err);
    }
  }, [canvas, data, ui.currentWorkflowId]);

  const handleAddNodeFromList = useCallback(async (node: NodeData) => {
    if (!ui.currentWorkflowId) return;
    canvas.addNodeFromList(node);
    try {
      const result = await data.createNode.mutateAsync({
        workflowId: ui.currentWorkflowId,
        nodeId: node.node_id,
        promptKey: node.prompt_key,
        config: node.config || {},
        positionX: node.position_x,
        positionY: node.position_y,
      });
      canvas.setNodes(prev =>
        prev.map(n => (n.node_id === node.node_id ? { ...n, recordId: result.id } : n))
      );
    } catch (err) {
      console.error('Failed to create node from list:', err);
    }
  }, [canvas, data, ui.currentWorkflowId]);

  const handleUpdateNode = useCallback(async (recordId: string, promptKey: string, config: Record<string, unknown>) => {
    try {
      await data.updateNode.mutateAsync({ recordId, prompt_key: promptKey, config });
    } catch (err) {
      console.error('Failed to update node:', err);
    }
  }, [data]);

  const handleDeleteNode = useCallback(async (recordId: string) => {
    try {
      await data.deleteNode.mutateAsync(recordId);
      canvas.setNodes(prev => prev.filter(n => n.recordId !== recordId));
      canvas.setEdges(prev => prev.filter(e => e.source_node !== recordId && e.target_node !== recordId));
    } catch (err) {
      console.error('Failed to delete node:', err);
    }
  }, [data, canvas]);

  const handleRequestDeleteNode = useCallback((recordId: string | undefined, nodeId: string, name: string) => {
    setDeletingNode({ recordId, nodeId, name });
  }, []);

  const confirmDeleteNode = useCallback(async () => {
    if (!deletingNode) return;
    if (deletingNode.recordId) {
      await handleDeleteNode(deletingNode.recordId);
    } else {
      canvas.setNodes(prev => prev.filter(n => n.node_id !== deletingNode.nodeId));
      canvas.setEdges(prev => prev.filter(e => e.source_node !== deletingNode.nodeId && e.target_node !== deletingNode.nodeId));
      toast.success('Node removed');
    }
    setDeletingNode(null);
  }, [deletingNode, handleDeleteNode, canvas]);

  return {
    editingNode,
    setEditingNode,
    deletingNode,
    setDeletingNode,
    handleAddCustomNode,
    handleConfirmAddCustomNode,
    handleAddNodeFromList,
    handleUpdateNode,
    handleDeleteNode,
    handleRequestDeleteNode,
    confirmDeleteNode,
  };
};
