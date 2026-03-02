import { NodeData, EdgeData } from './types';

/**
 * # Cycle Detection in Directed Graph
 * * Uses Depth-First Search (DFS) with three-color marking:
 * - WHITE (0): Unvisited node
 * - GRAY (1): Node in current DFS path (visiting)
 * - BLACK (2): Fully processed node
 */

type Color = 0 | 1 | 2; 
const WHITE: Color = 0;
const GRAY: Color = 1;
const BLACK: Color = 2;

interface CycleResult {
  hasCycle: boolean;
  cyclePath?: string[];
}

/**
 * Detect cycles in a directed graph using DFS
 */
export function hasCycle(nodes: NodeData[], edges: EdgeData[]): CycleResult {
  const adjacency: Map<string, string[]> = new Map();
  const nodeIdSet = new Set(nodes.map(n => n.node_id));
  
  for (const node of nodes) {
    adjacency.set(node.node_id, []);
  }
  
  for (const edge of edges) {
    if (nodeIdSet.has(edge.source_node) && nodeIdSet.has(edge.target_node)) {
      const targets = adjacency.get(edge.source_node) || [];
      targets.push(edge.target_node);
      adjacency.set(edge.source_node, targets);
    }
  }
  
  const color: Map<string, Color> = new Map();
  const parent: Map<string, string | null> = new Map();
  
  for (const nodeId of nodeIdSet) {
    color.set(nodeId, WHITE);
    parent.set(nodeId, null);
  }
  
  let cyclePath: string[] | undefined;

  function dfs(nodeId: string): boolean {
    color.set(nodeId, GRAY);
    
    const neighbors = adjacency.get(nodeId) || [];
    for (const neighbor of neighbors) {
      const neighborColor = color.get(neighbor);
      
      if (neighborColor === GRAY) {
        cyclePath = reconstructCycle(nodeId, neighbor, parent);
        return true;
      }
      
      if (neighborColor === WHITE) {
        parent.set(neighbor, nodeId);
        if (dfs(neighbor)) return true;
      }
    }
    
    color.set(nodeId, BLACK);
    return false;
  }
  
  function reconstructCycle(current: string, cycleStart: string, parent: Map<string, string | null>): string[] {
    const path: string[] = [cycleStart];
    let node: string | null = current;
    while (node !== null && node !== cycleStart) {
      path.unshift(node);
      node = parent.get(node) || null;
    }
    path.unshift(cycleStart);
    return path;
  }
  
  for (const nodeId of nodeIdSet) {
    if (color.get(nodeId) === WHITE) {
      if (dfs(nodeId)) return { hasCycle: true, cyclePath };
    }
  }
  
  return { hasCycle: false };
}

/**
 * Get a human-readable description of a cycle
 */
export function formatCycleDescription(cyclePath: string[], nodes: NodeData[]): string {
  if (!cyclePath || cyclePath.length < 2) {
    return 'Detected a cycle in the workflow';
  }
  
  const nodeMap = new Map(nodes.map(n => [n.node_id, n.prompt_key]));
  const labels = cyclePath.map(id => nodeMap.get(id) || id);
  
  if (labels.length <= 5) {
    return `Cycle detected: ${labels.join(' → ')}`;
  }
  
  return `Cycle detected: ${labels.slice(0, 3).join(' → ')} → ... → ${labels[labels.length - 1]}`;
}

/**
 * Validate workflow has no cycles before saving
 */
export function validateWorkflowAcyclic(nodes: NodeData[], edges: EdgeData[]): { valid: boolean; error?: string } {
  const result = hasCycle(nodes, edges);
  
  if (result.hasCycle && result.cyclePath) {
    const description = formatCycleDescription(result.cyclePath, nodes);
    return { valid: false, error: description };
  }
  
  return { valid: true };
}
