export interface GraphNode {
  id: string;
  type: string;
  promptKey: string;
  config: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface Layout {
  positions: Record<string, { x: number; y: number }>;
}

export interface Viewport {
  zoom: number;
  cameraX: number;
  cameraY: number;
}

export interface UIState {
  selectedNodeId: string | null;
  sidebarOpen: boolean;
  workflows: { id: string; name: string; description?: string }[];
  currentWorkflowId: string | null;
}

export interface WorkflowStore {
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  layout: Layout;
  viewport: Viewport;
  ui: UIState;

  loadWorkflow: (data: { nodes: any[]; edges: any[] }) => void;
  addNode: (nodeData: Omit<GraphNode, 'id'>, position?: { x: number; y: number }) => void;
  moveNode: (nodeId: string, position: { x: number; y: number }) => void;
  updateNodeConfig: (nodeId: string, config: Partial<GraphNode>) => void;
  removeNode: (nodeId: string) => void;
  addEdge: (source: string, target: string) => void;
  removeEdge: (edgeId: string) => void;
  setViewport: (zoom: number, cameraX: number, cameraY: number) => void;
  selectNode: (nodeId: string | null) => void;
  toggleSidebar: () => void;
  setWorkflows: (workflows: UIState['workflows']) => void;
  selectWorkflow: (workflowId: string | null) => void;
}