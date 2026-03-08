import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { WorkflowStore, GraphNode, ApiWorkflowDetail, ApiNode, ApiEdge } from './types';
import { deterministicNodeId, deterministicEdgeId } from '@/shared/lib/deterministicId';
import { syncWithServer } from './syncMiddleware';
import toast from 'react-hot-toast';

const savedViewport = localStorage.getItem('workflowViewport');
const initialViewport = savedViewport
  ? JSON.parse(savedViewport)
  : { zoom: 1, cameraX: 0, cameraY: 0 };

export const useWorkflowStore = create<WorkflowStore>()(
  subscribeWithSelector((set, get) => ({
    graph: {
      nodes: [],
      edges: [],
    },
    layout: {
      positions: {},
      sizes: {},
    },
    viewport: initialViewport,
    ui: {
      selectedNodeId: null,
      sidebarOpen: true,
      workflows: [],
      currentWorkflowId: null,
    },

    // Загрузка данных с сервера
    loadWorkflow: (data: ApiWorkflowDetail) => {
      console.log('[loadWorkflow] loading workflow with data:', data);
      const nodes: GraphNode[] = data.nodes.map((n: ApiNode) => {
        const id = deterministicNodeId(n.type || 'prompt', n.prompt_key, n.config);
        return {
          id,
          recordId: n.id,
          type: n.type || 'prompt',
          promptKey: n.prompt_key,
          config: n.config,
        };
      });
      const positions: Record<string, { x: number; y: number }> = {};
      data.nodes.forEach((n: ApiNode) => {
        const id = deterministicNodeId(n.type || 'prompt', n.prompt_key, n.config);
        positions[id] = { x: n.position_x, y: n.position_y };
      });
      const edges = data.edges.map((e: ApiEdge) => ({
        id: e.id,
        source: e.source_node,
        target: e.target_node,
      }));
      console.log('[loadWorkflow] setting nodes:', nodes.length, 'edges:', edges.length);
      console.log('[loadWorkflow] positions:', Object.keys(positions).length);
      set({
        graph: { nodes, edges },
        layout: { ...get().layout, positions, sizes: {} },
      });
    },

    addNode: (nodeData, position = { x: 100, y: 100 }) => {
      const id = deterministicNodeId(nodeData.type, nodeData.promptKey, nodeData.config);
      console.log('[addNode] creating node with id:', id);
      console.log('[addNode] nodeData:', nodeData);
      console.log('[addNode] position:', position);
      
      set((state) => ({
        graph: {
          ...state.graph,
          nodes: [...state.graph.nodes, { ...nodeData, id, recordId: undefined }],
        },
        layout: {
          ...state.layout,
          positions: { ...state.layout.positions, [id]: position },
          sizes: { ...state.layout.sizes, [id]: { width: 0, height: 0 } },
        },
      }));

      syncWithServer('addNode', { ...nodeData, id, position })
        .then((recordId) => {
          console.log('[workflowStore] addNode success, recordId:', recordId);
          if (recordId) {
            set((state) => ({
              graph: {
                ...state.graph,
                nodes: state.graph.nodes.map((n) =>
                  n.id === id ? { ...n, recordId } : n
                ),
              },
            }));
          }
        })
        .catch((error) => {
          console.error('[workflowStore] addNode error:', error);
          set((state) => ({
            graph: {
              ...state.graph,
              nodes: state.graph.nodes.filter((n) => n.id !== id),
            },
            layout: {
              ...state.layout,
              positions: Object.fromEntries(
                Object.entries(state.layout.positions).filter(([k]) => k !== id)
              ),
              sizes: Object.fromEntries(
                Object.entries(state.layout.sizes).filter(([k]) => k !== id)
              ),
            },
          }));
          toast.error('Failed to create node');
        });
    },

    // Оптимистичное обновление позиции при перетаскивании (без отправки на сервер)
    setNodePositionOptimistic: (nodeId: string, position: { x: number; y: number }) => 
      set((state) => ({
        layout: {
          ...state.layout,
          positions: { ...state.layout.positions, [nodeId]: position },
        },
      })),

    // Перемещение узла (с сохранением на сервере)
    moveNode: (nodeId, position) => {
      const node = get().graph.nodes.find(n => n.id === nodeId);
      if (!node) return;

      set((state) => ({
        layout: {
          ...state.layout,
          positions: { ...state.layout.positions, [nodeId]: position },
        },
      }));

      syncWithServer('moveNode', { nodeId: node.recordId, position }).catch((error) => {
        console.error('[moveNode] error:', error);
        toast.error('Failed to save node position');
      });
    },

    // Обновление конфигурации узла
    updateNodeConfig: (nodeId, config) => {
      const node = get().graph.nodes.find(n => n.id === nodeId);
      if (!node) return;

      set((state) => ({
        graph: {
          ...state.graph,
          nodes: state.graph.nodes.map((n) =>
            n.id === nodeId ? { ...n, ...config } : n
          ),
        },
      }));

      // Приводим config к формату, ожидаемому syncMiddleware
      syncWithServer('updateNode', {
        nodeId: node.recordId,
        config: {
          promptKey: config.promptKey || '',
          config: config.config || {},
        },
      }).catch((error) => {
        console.error('[updateNode] error:', error);
        toast.error('Failed to update node');
      });
    },

    // Удаление узла
    removeNode: (nodeId) => {
      const node = get().graph.nodes.find(n => n.id === nodeId);
      if (!node) return;

      set((state) => {
        const newEdges = state.graph.edges.filter(
          (e) => e.source !== node.id && e.target !== node.id
        );
        const newPositions = { ...state.layout.positions };
        delete newPositions[nodeId];
        const newSizes = { ...state.layout.sizes };
        delete newSizes[nodeId];
        return {
          graph: {
            nodes: state.graph.nodes.filter((n) => n.id !== nodeId),
            edges: newEdges,
          },
          layout: { ...state.layout, positions: newPositions, sizes: newSizes },
        };
      });

      syncWithServer('removeNode', { nodeId: node.recordId }).catch((error) => {
        console.error('[removeNode] error:', error);
        toast.error('Failed to delete node');
      });
    },

    // Добавление ребра
    addEdge: (sourceId, targetId) => {
      const nodes = get().graph.nodes;
      const sourceNode = nodes.find(n => n.id === sourceId);
      const targetNode = nodes.find(n => n.id === targetId);
      if (!sourceNode || !targetNode) {
        toast.error('Node not found');
        return;
      }
      if (!sourceNode.recordId || !targetNode.recordId) {
        toast.error('Please wait for nodes to be saved before connecting');
        return;
      }
      const id = deterministicEdgeId(sourceId, targetId);
      set((state) => {
        const exists = state.graph.edges.some(e => e.source === sourceId && e.target === targetId);
        if (exists) return state;
        return {
          graph: {
            ...state.graph,
            edges: [...state.graph.edges, { id, source: sourceId, target: targetId }],
          },
        };
      });
      syncWithServer('addEdge', { source: sourceId, target: targetId }).catch((error) => {
        console.error('[addEdge] error:', error);
        set((state) => ({
          graph: {
            ...state.graph,
            edges: state.graph.edges.filter(e => e.id !== id),
          },
        }));
        toast.error('Failed to create edge');
      });
    },

    // Удаление ребра
    removeEdge: (edgeId) => {
      set((state) => ({
        graph: {
          ...state.graph,
          edges: state.graph.edges.filter((e) => e.id !== edgeId),
        },
      }));
      syncWithServer('removeEdge', { edgeId }).catch((error) => {
        console.error('[removeEdge] error:', error);
        toast.error('Failed to delete edge');
      });
    },

    setViewport: (zoom, cameraX, cameraY) => {
      set({ viewport: { zoom, cameraX, cameraY } });
      localStorage.setItem('workflowViewport', JSON.stringify({ zoom, cameraX, cameraY }));
    },

    selectNode: (nodeId) => set((state) => ({ ui: { ...state.ui, selectedNodeId: nodeId } })),
    toggleSidebar: () => set((state) => ({ ui: { ...state.ui, sidebarOpen: !state.ui.sidebarOpen } })),
    setWorkflows: (workflows) => {
      console.log('[setWorkflows] setting workflows:', workflows.length);
      set((state) => ({ ui: { ...state.ui, workflows } }));
    },
    selectWorkflow: (workflowId) => {
      console.log('[selectWorkflow] selecting workflow:', workflowId);
      set((state) => ({ ui: { ...state.ui, currentWorkflowId: workflowId } }));
    },
    updateNodeSize: (nodeId, size) => {
      set((state) => ({
        layout: {
          ...state.layout,
          sizes: { ...state.layout.sizes, [nodeId]: size },
        },
      }));
    },
  }))
);