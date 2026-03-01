import { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { useNodeValidation } from '../components/ios/useNodeValidation';

// Локальные типы, расширяющие базовые
export interface NodeData {
  id: string;
  node_id: string;
  prompt_key: string;
  position_x: number;
  position_y: number;
  config?: Record<string, unknown>;
  recordId?: string;
}

export interface EdgeData {
  id: string;
  source_node: string;
  target_node: string;
}

interface UseWorkflowCanvasReturn {
  nodes: NodeData[];
  edges: EdgeData[];
  showNodeModal: boolean;
  showNodeList: boolean;
  newNodePrompt: string;
  newNodeTitle: string;
  setShowNodeList: (show: boolean) => void;
  setShowNodeModal: (show: boolean) => void;
  setNewNodePrompt: (prompt: string) => void;
  setNewNodeTitle: (title: string) => void;
  setNodes: (nodes: NodeData[] | ((prev: NodeData[]) => NodeData[])) => void;
  setEdges: (edges: EdgeData[] | ((prev: EdgeData[]) => EdgeData[])) => void;
  handleAddCustomNode: (x: number, y: number) => void;
  confirmAddCustomNode: () => Promise<NodeData | undefined>;
  addNodeFromList: (node: NodeData) => void;
  validateNodeUnique: (title: string, prompt: string) => string | null;
  createDeleteHandler: (nodeId: string) => () => void;
  handleStartConnection: (nodeId: string) => void;
  handleCompleteConnection: (targetNodeId: string) => void;
  connectingNode: string | null;
  selectedNode: string | null;
  setSelectedNode: (nodeId: string | null) => void;
}

export const useWorkflowCanvas = (initialNodes: NodeData[] = [], initialEdges: EdgeData[] = []): UseWorkflowCanvasReturn => {
  const [nodes, setNodes] = useState<NodeData[]>(initialNodes);
  const [edges, setEdges] = useState<EdgeData[]>(initialEdges);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [connectingNode, setConnectingNode] = useState<string | null>(null);

  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showNodeList, setShowNodeList] = useState(false);
  const [newNodePrompt, setNewNodePrompt] = useState('');
  const [newNodeTitle, setNewNodeTitle] = useState('');

  const [newNodePosition, setNewNodePosition] = useState<{ x: number; y: number } | null>(null);

  const { validateNodeUnique } = useNodeValidation(nodes);

  const handleAddCustomNode = useCallback((x: number, y: number) => {
    setNewNodeTitle('');
    setNewNodePrompt('');
    setShowNodeModal(true);
    setNewNodePosition({ x, y });
  }, []);

  const confirmAddCustomNode = useCallback(async (): Promise<NodeData | undefined> => {
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
    if (!newNodePosition) {
      toast.error('Position not set');
      return;
    }
    const newNode: NodeData = {
      id: crypto.randomUUID(),
      node_id: crypto.randomUUID(),
      prompt_key: title,
      position_x: newNodePosition.x,
      position_y: newNodePosition.y,
      config: { custom_prompt: newNodePrompt },
      recordId: undefined,
    };
    setNodes(prev => [...prev, newNode]);
    setShowNodeModal(false);
    setNewNodePrompt('');
    setNewNodeTitle('');
    setNewNodePosition(null);
    return newNode;
  }, [newNodePrompt, newNodeTitle, newNodePosition, validateNodeUnique]);

  const addNodeFromList = useCallback((node: NodeData) => {
    setNodes(prev => [...prev, node]);
    setShowNodeList(false);
  }, []);

  const handleStartConnection = useCallback((nodeId: string) => {
    setConnectingNode(nodeId);
  }, []);

  const handleCompleteConnection = useCallback((targetNodeId: string) => {
    setConnectingNode(prev => {
      if (prev && prev !== targetNodeId) {
        const edgeExists = edges.some(
          e => e.source_node === prev && e.target_node === targetNodeId
        );
        if (!edgeExists) {
          const newEdge: EdgeData = {
            id: crypto.randomUUID(),
            source_node: prev,
            target_node: targetNodeId,
          };
          setEdges(prevEdges => [...prevEdges, newEdge]);
        }
      }
      return null;
    });
  }, [edges]);

  const createDeleteHandler = useCallback((nodeId: string) => {
    return () => {
      setNodes(prevNodes => prevNodes.filter(n => n.node_id !== nodeId));
      setEdges(prevEdges => prevEdges.filter(e => e.source_node !== nodeId && e.target_node !== nodeId));
      if (selectedNode === nodeId) setSelectedNode(null);
      if (connectingNode === nodeId) setConnectingNode(null);
    };
  }, [selectedNode, connectingNode]);

  return {
    nodes,
    edges,
    showNodeModal,
    showNodeList,
    newNodePrompt,
    newNodeTitle,
    setShowNodeList,
    setShowNodeModal,
    setNewNodePrompt,
    setNewNodeTitle,
    setNodes,
    setEdges,
    handleAddCustomNode,
    confirmAddCustomNode,
    addNodeFromList,
    validateNodeUnique,
    createDeleteHandler,
    handleStartConnection,
    handleCompleteConnection,
    connectingNode,
    selectedNode,
    setSelectedNode,
  };
};
