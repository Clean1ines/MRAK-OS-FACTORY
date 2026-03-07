import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { WorkflowStore, GraphNode } from './types';
import { deterministicNodeId, deterministicEdgeId } from '@/shared/lib/deterministicId';
import { syncWithServer } from './syncMiddleware';

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
    },
    viewport: initialViewport,
    ui: {
      selectedNodeId: null,
      sidebarOpen: true,
      workflows: [],
      currentWorkflowId: null,
    },

    loadWorkflow: (data) => {
      console.log('[loadWorkflow] loading workflow with data:', data);
      const nodes: GraphNode[] = data.nodes.map((n: any) => ({
        id: n.id,
        type: n.type || 'prompt',
        promptKey: n.prompt_key,
        config: n.config,
      }));
      const positions: Record<string, { x: number; y: number }> = {};
      data.nodes.forEach((n: any) => {
        positions[n.id] = { x: n.position_x, y: n.position_y };
      });
      const edges = data.edges.map((e: any) => ({
        id: e.id,
        source: e.source_node,
        target: e.target_node,
      }));
      console.log('[loadWorkflow] setting nodes:', nodes.length, 'edges:', edges.length);
      console.log('[loadWorkflow] positions:', Object.keys(positions).length);
      set({
        graph: { nodes, edges },
        layout: { positions },
      });
    },

    addNode: (nodeData, position = { x: 100, y: 100 }) => {
      const id = deterministicNodeId(nodeData.type, nodeData.promptKey, nodeData.config);
      console.log('[addNode] creating node with id:', id);
      set((state) => ({
        graph: {
          ...state.graph,
          nodes: [...state.graph.nodes, { ...nodeData, id }],
        },
        layout: {
          positions: { ...state.layout.positions, [id]: position },
        },
      }));
      syncWithServer('addNode', { ...nodeData, id, position });
    },

    moveNode: (nodeId, position) => {
      console.log('[moveNode] moving node:', nodeId, position);
      set((state) => ({
        layout: {
          positions: { ...state.layout.positions, [nodeId]: position },
        },
      }));
      syncWithServer('moveNode', { nodeId, position });
    },

    updateNodeConfig: (nodeId, config) => {
      console.log('[updateNodeConfig] updating node:', nodeId, config);
      set((state) => ({
        graph: {
          ...state.graph,
          nodes: state.graph.nodes.map((n) =>
            n.id === nodeId ? { ...n, ...config } : n
          ),
        },
      }));
      syncWithServer('updateNode', { nodeId, config });
    },

    removeNode: (nodeId) => {
      console.log('[removeNode] removing node:', nodeId);
      set((state) => {
        const newEdges = state.graph.edges.filter(
          (e) => e.source !== nodeId && e.target !== nodeId
        );
        const newPositions = { ...state.layout.positions };
        delete newPositions[nodeId];
        return {
          graph: {
            nodes: state.graph.nodes.filter((n) => n.id !== nodeId),
            edges: newEdges,
          },
          layout: { positions: newPositions },
        };
      });
      syncWithServer('removeNode', { nodeId });
    },

    addEdge: (source, target) => {
      const id = deterministicEdgeId(source, target);
      console.log('[addEdge] adding edge:', id, source, target);
      set((state) => {
        const exists = state.graph.edges.some((e) => e.source === source && e.target === target);
        if (exists) return state;
        return {
          graph: {
            ...state.graph,
            edges: [...state.graph.edges, { id, source, target }],
          },
        };
      });
      syncWithServer('addEdge', { source, target });
    },

    removeEdge: (edgeId) => {
      console.log('[removeEdge] removing edge:', edgeId);
      set((state) => ({
        graph: {
          ...state.graph,
          edges: state.graph.edges.filter((e) => e.id !== edgeId),
        },
      }));
      syncWithServer('removeEdge', { edgeId });
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
  }))
);