import { useState, useCallback } from 'react';
import { client } from '../api/client';
import toast from 'react-hot-toast';
import type { NodeData, EdgeData } from './useCanvasEngine';
import { useNodeValidation } from '../components/ios/useNodeValidation';
import { validateWorkflowAcyclic } from '../utils/graphUtils';

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

export const useWorkflows = (selectedProjectId: string | null) => {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workflowName, setWorkflowName] = useState('');
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showNodeList, setShowNodeList] = useState(false);
  const [newNodePrompt, setNewNodePrompt] = useState('');
  const [newNodeTitle, setNewNodeTitle] = useState('');
  const { validateNodeUnique } = useNodeValidation(nodes);

  // Состояния для создания воркфлоу
  const [showCreateWorkflowModal, setShowCreateWorkflowModal] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDescription, setNewWorkflowDescription] = useState('');

  // Для создания кастомной ноды
  const [newNodePosition, setNewNodePosition] = useState<{ x: number; y: number } | null>(null);

  const loadWorkflows = useCallback(async () => {
    if (!selectedProjectId) return;
    try {
      const response = (await client.GET('/api/workflows')) as {
        data?: WorkflowSummary[];
        error?: unknown;
      };
      if (response.error) {
        console.error('Failed to load workflows:', response.error);
        return;
      }
      if (response.data && Array.isArray(response.data)) {
        setWorkflows(response.data);
      } else {
        setWorkflows([]);
      }
    } catch (e) {
      console.error('Error loading workflows:', e);
    }
  }, [selectedProjectId]);

  const loadWorkflow = useCallback(async (id: string) => {
    try {
      const r = await client.GET('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: id } }
      });
      if (r.error) {
        console.error('Failed to load workflow:', r.error);
        return;
      }
      const detail = r.data as WorkflowDetail;
      if (detail) {
        setNodes((detail.nodes || []).map((n: WorkflowNode) => ({
          id: n.node_id || crypto.randomUUID(),
          node_id: n.node_id!,
          prompt_key: n.prompt_key || 'UNKNOWN',
          position_x: n.position_x || 100,
          position_y: n.position_y || 100,
          config: n.config || {}
        })));
        setEdges((detail.edges || []).map((e: WorkflowEdge) => ({
          id: e.id || crypto.randomUUID(),
          source_node: e.source_node!,
          target_node: e.target_node!
        })));
        setCurrentWorkflowId(id);
        setWorkflowName(detail.workflow?.name || '');
      }
    } catch (e) {
      console.error('Error loading workflow:', e);
    }
  }, []);

  const handleSave = useCallback(async () => {
    if (!workflowName.trim() || !selectedProjectId) {
      toast.error('⚠️ Заполните обязательные поля');
      return false;
    }
    if (!validateWorkflowAcyclic(nodes, edges).valid) {
      toast.error('⚠️ Обнаружен цикл – удалите круговые соединения');
      return false;
    }
    setLoading(true);
    try {
      const url = currentWorkflowId
        ? `/api/workflows/${currentWorkflowId}`
        : '/api/workflows';
      const token = sessionStorage.getItem('mrak_session_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const res = await fetch(url, {
        method: currentWorkflowId ? 'PUT' : 'POST',
        headers,
        body: JSON.stringify({
          name: workflowName,
          description: 'Created in workspace editor',
          project_id: selectedProjectId,
          nodes: nodes.map(n => ({
            node_id: n.node_id,
            prompt_key: n.prompt_key,
            position_x: n.position_x,
            position_y: n.position_y,
            config: n.config
          })),
          edges: edges.map(e => ({
            source_node: e.source_node,
            target_node: e.target_node
          }))
        })
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }
      await loadWorkflows();
      toast.success(`✅ Workflow ${currentWorkflowId ? 'обновлён' : 'сохранён'}!`);
      return true;
    } catch (e: unknown) {
      console.error('Save error:', e);
      toast.error('❌ Ошибка при сохранении: ' + (e instanceof Error ? e.message : String(e)));
      return false;
    } finally {
      setLoading(false);
    }
  }, [workflowName, selectedProjectId, currentWorkflowId, nodes, edges, loadWorkflows]);

  const handleDelete = useCallback(async () => {
    if (!currentWorkflowId || !confirm(`Удалить "${workflowName}"?`)) return false;
    try {
      const r = await client.DELETE('/api/workflows/{workflow_id}', {
        params: { path: { workflow_id: currentWorkflowId } }
      });
      if (r.error) {
        console.error('Delete error:', r.error);
        return false;
      }
      setNodes([]);
      setEdges([]);
      setCurrentWorkflowId(null);
      setWorkflowName('New Workflow');
      await loadWorkflows();
      toast.success('✅ Удалено');
      return true;
    } catch (e: unknown) {
      console.error('Delete exception:', e);
      toast.error('❌ Ошибка при удалении');
      return false;
    }
  }, [currentWorkflowId, workflowName, loadWorkflows]);

  const handleAddCustomNode = useCallback((x: number, y: number) => {
    setNewNodeTitle('');
    setNewNodePrompt('');
    setShowNodeModal(true);
    setNewNodePosition({ x, y });
  }, []);

  const confirmAddCustomNode = useCallback(async () => {
    if (!newNodePrompt.trim()) {
      toast.error('Введите промпт');
      return;
    }
    const title = newNodeTitle.trim() || 'CUSTOM_PROMPT';
    const err = validateNodeUnique(title, newNodePrompt);
    if (err) {
      toast.error(`⚠️ ${err}`);
      return;
    }
    if (newNodePosition) {
      setNodes(prev => [...prev, {
        id: crypto.randomUUID(),
        node_id: crypto.randomUUID(),
        prompt_key: title,
        position_x: newNodePosition.x,
        position_y: newNodePosition.y,
        config: { custom_prompt: newNodePrompt }
      }]);
    }
    setShowNodeModal(false);
    setNewNodePrompt('');
    setNewNodeTitle('');
    setNewNodePosition(null);
  }, [newNodePrompt, newNodeTitle, newNodePosition, validateNodeUnique]);

  const addNodeFromList = useCallback((node: NodeData) => {
    setNodes(prev => [...prev, node]);
    setShowNodeList(false);
  }, []);

  const handleCreateWorkflow = useCallback(async () => {
    if (!newWorkflowName.trim() || !selectedProjectId) {
      toast.error('Name is required');
      return false;
    }
    const token = sessionStorage.getItem('mrak_session_token');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch('/api/workflows', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: newWorkflowName,
          description: newWorkflowDescription,
          project_id: selectedProjectId,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      await loadWorkflows();
      toast.success('Workflow created');
      setShowCreateWorkflowModal(false);
      setNewWorkflowName('');
      setNewWorkflowDescription('');
      return true;
    } catch (e: unknown) {
      console.error(e);
      toast.error('Failed to create workflow');
      return false;
    }
  }, [newWorkflowName, newWorkflowDescription, selectedProjectId, loadWorkflows]);

  return {
    // состояния
    nodes,
    edges,
    workflowName,
    currentWorkflowId,
    workflows,
    loading,
    showNodeModal,
    showNodeList,
    newNodePrompt,
    newNodeTitle,
    showCreateWorkflowModal,
    newWorkflowName,
    newWorkflowDescription,
    validateNodeUnique,

    // сеттеры
    setWorkflowName,
    setCurrentWorkflowId,
    setShowNodeList,
    setShowCreateWorkflowModal,
    setNewWorkflowName,
    setNewWorkflowDescription,
    setShowNodeModal,
    setNewNodePrompt,
    setNewNodeTitle,
    setNodes,
    setEdges,

    // функции
    loadWorkflows,
    loadWorkflow,
    handleSave,
    handleDelete,
    handleAddCustomNode,
    confirmAddCustomNode,
    addNodeFromList,
    handleCreateWorkflow,
  };
};
