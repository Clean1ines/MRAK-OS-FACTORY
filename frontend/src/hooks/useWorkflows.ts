import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { client } from '../api/client';
import toast from 'react-hot-toast';
import type { NodeData, EdgeData } from './useCanvasEngine';
import { validateWorkflowAcyclic } from '../utils/graphUtils';
import { useWorkflowCanvas } from './useWorkflowCanvas';

interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  is_default?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface WorkflowNode {
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

interface WorkflowEdge {
  id: string;
  workflow_id: string;
  source_node: string;
  target_node: string;
  source_output?: string;
  target_input?: string;
  created_at?: string;
}

interface WorkflowDetail {
  workflow: WorkflowSummary;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

const fetchWorkflows = async (projectId: string | null): Promise<WorkflowSummary[]> => {
  if (!projectId) return [];
  const response = (await client.GET('/api/workflows')) as {
    data?: WorkflowSummary[];
    error?: unknown;
  };
  if (response.error) throw response.error;
  return response.data || [];
};

const fetchWorkflowDetail = async (id: string): Promise<WorkflowDetail> => {
  const r = await client.GET('/api/workflows/{workflow_id}', {
    params: { path: { workflow_id: id } }
  });
  if (r.error) throw r.error;
  return r.data as WorkflowDetail;
};

const createWorkflowApi = async (params: {
  name: string;
  description: string;
  projectId: string;
}): Promise<WorkflowSummary> => {
  const token = sessionStorage.getItem('mrak_session_token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch('/api/workflows', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      name: params.name,
      description: params.description,
      project_id: params.projectId,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${res.status}`);
  }
  return res.json();
};

const saveWorkflowApi = async (params: {
  id?: string;
  name: string;
  description: string;
  projectId: string;
  nodes: NodeData[];
  edges: EdgeData[];
}) => {
  const token = sessionStorage.getItem('mrak_session_token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const url = params.id ? `/api/workflows/${params.id}` : '/api/workflows';
  const method = params.id ? 'PUT' : 'POST';

  const res = await fetch(url, {
    method,
    headers,
    body: JSON.stringify({
      name: params.name,
      description: params.description,
      project_id: params.projectId,
      nodes: params.nodes.map(n => ({
        node_id: n.node_id,
        prompt_key: n.prompt_key,
        position_x: n.position_x,
        position_y: n.position_y,
        config: n.config,
      })),
      edges: params.edges.map(e => ({
        source_node: e.source_node,
        target_node: e.target_node,
      })),
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${res.status}`);
  }
  return res.json();
};

const deleteWorkflowApi = async (id: string) => {
  const r = await client.DELETE('/api/workflows/{workflow_id}', {
    params: { path: { workflow_id: id } }
  });
  if (r.error) throw r.error;
  return id;
};

export const useWorkflows = (selectedProjectId: string | null) => {
  const queryClient = useQueryClient();

  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState('');
  const [loading, setLoading] = useState(false);

  // Состояния для создания воркфлоу
  const [showCreateWorkflowModal, setShowCreateWorkflowModal] = useState(false);

  // Холст управляется отдельным хуком
  const canvas = useWorkflowCanvas();

  // Запрос списка воркфлоу
  const {
    data: workflows = [],
    isLoading: isLoadingWorkflows,
    error: workflowsError,
  } = useQuery({
    queryKey: ['workflows', selectedProjectId],
    queryFn: () => fetchWorkflows(selectedProjectId),
    enabled: !!selectedProjectId,
  });

  // Запрос деталей текущего воркфлоу
  const {
    data: workflowDetail,
    isLoading: isLoadingDetail,
  } = useQuery({
    queryKey: ['workflow', currentWorkflowId],
    queryFn: () => fetchWorkflowDetail(currentWorkflowId!),
    enabled: !!currentWorkflowId,
  });

  // Эффект для обновления canvas при загрузке деталей
  useEffect(() => {
    if (workflowDetail) {
      const nodes = (workflowDetail.nodes || []).map((n: WorkflowNode) => ({
        id: n.node_id || crypto.randomUUID(),
        node_id: n.node_id!,
        prompt_key: n.prompt_key || 'UNKNOWN',
        position_x: n.position_x || 100,
        position_y: n.position_y || 100,
        config: n.config || {}
      }));
      const edges = (workflowDetail.edges || []).map((e: WorkflowEdge) => ({
        id: e.id || crypto.randomUUID(),
        source_node: e.source_node!,
        target_node: e.target_node!
      }));
      // Обновляем состояние холста (setNodes/setEdges доступны из canvas)
      canvas.setNodes(nodes);
      canvas.setEdges(edges);
      setWorkflowName(workflowDetail.workflow?.name || '');
    } else {
      canvas.setNodes([]);
      canvas.setEdges([]);
      setWorkflowName('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowDetail]);

  // Мутация создания воркфлоу (просто имя, без нод)
  const createWorkflowMutation = useMutation({
    mutationFn: createWorkflowApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', selectedProjectId] });
      toast.success('Workflow created');
      setShowCreateWorkflowModal(false);
    },
    onError: (err: unknown) => {
      console.error(err);
      toast.error('Failed to create workflow');
    },
  });

  // Мутация сохранения (с нодами и рёбрами)
  const saveWorkflowMutation = useMutation({
    mutationFn: saveWorkflowApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', selectedProjectId] });
      toast.success(`✅ Workflow ${currentWorkflowId ? 'обновлён' : 'сохранён'}!`);
    },
    onError: (err: unknown) => {
      console.error('Save error:', err);
      toast.error('❌ Ошибка при сохранении: ' + (err instanceof Error ? err.message : String(err)));
    },
  });

  // Мутация удаления
  const deleteWorkflowMutation = useMutation({
    mutationFn: deleteWorkflowApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', selectedProjectId] });
      canvas.setNodes([]);
      canvas.setEdges([]);
      setCurrentWorkflowId(null);
      setWorkflowName('New Workflow');
      toast.success('✅ Удалено');
    },
    onError: (err: unknown) => {
      console.error('Delete error:', err);
      toast.error('❌ Ошибка при удалении');
    },
  });

  const handleSave = useCallback(async () => {
    if (!workflowName.trim() || !selectedProjectId) {
      toast.error('⚠️ Заполните обязательные поля');
      return false;
    }
    if (!validateWorkflowAcyclic(canvas.nodes, canvas.edges).valid) {
      toast.error('⚠️ Обнаружен цикл – удалите круговые соединения');
      return false;
    }
    setLoading(true);
    try {
      await saveWorkflowMutation.mutateAsync({
        id: currentWorkflowId || undefined,
        name: workflowName,
        description: 'Created in workspace editor',
        projectId: selectedProjectId,
        nodes: canvas.nodes,
        edges: canvas.edges,
      });
      return true;
    } finally {
      setLoading(false);
    }
  }, [workflowName, selectedProjectId, currentWorkflowId, canvas.nodes, canvas.edges, saveWorkflowMutation]);

  const handleDelete = useCallback(async () => {
    if (!currentWorkflowId || !confirm(`Удалить "${workflowName}"?`)) return false;
    try {
      await deleteWorkflowMutation.mutateAsync(currentWorkflowId);
      return true;
    } catch {
      return false;
    }
  }, [currentWorkflowId, workflowName, deleteWorkflowMutation]);

  const handleCreateWorkflow = useCallback(async (name: string, description: string) => {
    if (!name.trim() || !selectedProjectId) {
      toast.error('Name is required');
      return false;
    }
    try {
      await createWorkflowMutation.mutateAsync({
        name,
        description,
        projectId: selectedProjectId,
      });
      return true;
    } catch {
      return false;
    }
  }, [selectedProjectId, createWorkflowMutation]);

  return {
    // данные из query
    workflows,
    isLoadingWorkflows,
    workflowsError,
    // состояния из canvas
    ...canvas,
    // состояния
    workflowName,
    currentWorkflowId,
    loading: loading || isLoadingDetail || saveWorkflowMutation.isPending,
    showCreateWorkflowModal,
    // сеттеры
    setWorkflowName,
    setCurrentWorkflowId,
    setShowCreateWorkflowModal,
    // функции
    handleSave,
    handleDelete,
    handleCreateWorkflow,
    // статусы мутаций
    isCreatingWorkflow: createWorkflowMutation.isPending,
    isDeletingWorkflow: deleteWorkflowMutation.isPending,
  };
};
