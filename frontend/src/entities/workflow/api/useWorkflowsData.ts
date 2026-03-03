import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { workflowApi } from './workflowApi';

export interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface WorkflowNode {
  id: string;
  workflow_id: string;
  node_id: string;
  prompt_key: string;
  config?: Record<string, unknown>;
  position_x: number;
  position_y: number;
  created_at?: string;
  updated_at?: string;
}

export interface WorkflowEdge {
  id: string;
  workflow_id: string;
  source_node: string;
  target_node: string;
  source_output?: string;
  target_input?: string;
  created_at?: string;
}

export interface WorkflowDetail {
  workflow: WorkflowSummary;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export const useWorkflowsData = (projectId: string | null) => {
  const queryClient = useQueryClient();

  const workflowsQuery = useQuery<WorkflowSummary[]>({
    queryKey: ['workflows', projectId],
    queryFn: () => workflowApi.list(projectId ?? undefined).then(res => (res.data as WorkflowSummary[]) ?? []),
    enabled: !!projectId,
  });

  const createWorkflow = useMutation({
    mutationFn: (params: { name: string; description: string; projectId: string }) =>
      workflowApi
        .create({ 
          name: params.name, 
          description: params.description, 
          project_id: params.projectId,
          is_default: false 
        })
        .then(res => res.data as WorkflowSummary),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', projectId] });
      toast.success('✅ Workflow created');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to create workflow: ${message}`);
    },
  });

  const updateWorkflow = useMutation({
    mutationFn: (params: { id: string; name: string; description: string }) =>
      workflowApi.update(params.id, { name: params.name, description: params.description }).then(res => res.data as WorkflowSummary),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', projectId] });
      queryClient.invalidateQueries({ queryKey: ['workflow', variables.id] });
      toast.success('✅ Workflow updated');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to update workflow: ${message}`);
    },
  });

  const deleteWorkflow = useMutation({
    mutationFn: (id: string) => workflowApi.delete(id).then(() => id),
    onSuccess: (deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', projectId] });
      queryClient.removeQueries({ queryKey: ['workflow', deletedId] });
      toast.success('✅ Workflow deleted');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to delete workflow: ${message}`);
    },
  });

  const createNode = useMutation({
    mutationFn: (params: {
      workflowId: string;
      nodeId: string;
      promptKey: string;
      config: Record<string, unknown>;
      positionX: number;
      positionY: number;
    }) =>
      workflowApi.nodes
        .create(params.workflowId, {
          node_id: params.nodeId,
          prompt_key: params.promptKey,
          config: params.config,
          position_x: params.positionX,
          position_y: params.positionY,
        })
        .then(res => res.data as { id: string }),
    onSuccess: () => {
      toast.success('✅ Node created');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to create node: ${message}`);
    },
  });

  const updateNode = useMutation({
    mutationFn: (params: { recordId: string; prompt_key: string; config: Record<string, unknown> }) =>
      workflowApi.nodes
        .update(params.recordId, { prompt_key: params.prompt_key, config: params.config })
        .then(res => res.data),
    onSuccess: () => {
      toast.success('✅ Node updated');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to update node: ${message}`);
    },
  });

  const deleteNode = useMutation({
    mutationFn: (recordId: string) => workflowApi.nodes.delete(recordId).then(() => recordId),
    onSuccess: () => {
      toast.success('✅ Node deleted');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to delete node: ${message}`);
    },
  });

  const createEdge = useMutation({
    mutationFn: (params: { workflowId: string; sourceNode: string; targetNode: string }) =>
      workflowApi.edges
        .create(params.workflowId, {
          source_node: params.sourceNode,
          target_node: params.targetNode,
          source_output: 'output',
          target_input: 'input',
        })
        .then(res => res.data as { id: string }),
    onSuccess: () => {
      toast.success('✅ Edge created');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to create edge: ${message}`);
    },
  });

  const deleteEdge = useMutation({
    mutationFn: (edgeId: string) => workflowApi.edges.delete(edgeId).then(() => edgeId),
    onSuccess: () => {
      toast.success('✅ Edge deleted');
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`❌ Failed to delete edge: ${message}`);
    },
  });

  return {
    workflows: workflowsQuery.data ?? [],
    isLoadingWorkflows: workflowsQuery.isLoading,
    workflowsError: workflowsQuery.error,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    createNode,
    updateNode,
    deleteNode,
    createEdge,
    deleteEdge,
  };
};
