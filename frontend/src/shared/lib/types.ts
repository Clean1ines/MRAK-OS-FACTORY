// src/shared/lib/types.ts
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
