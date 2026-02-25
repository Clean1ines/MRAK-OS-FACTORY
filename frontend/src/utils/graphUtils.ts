// frontend/src/utils/graphUtils.ts
// ADDED: Graph utilities for cycle detection in workflow DAG

import type { NodeData, EdgeData } from '../hooks/useCanvasEngine';

/**
 * # Cycle Detection in Directed Graph
 * 
 * Uses Depth-First Search (DFS) with three-color marking:
 * - WHITE (0): Unvisited node
 * - GRAY (1): Node in current DFS path (visiting)
 * - BLACK (2): Fully processed node
 * 
 * If we encounter a GRAY node during DFS, we found a cycle.
 * 
 * Time Complexity: O(V + E) where V = nodes, E = edges
 * Space Complexity: O(V) for recursion stack and color map
 */

type Color = 0 | 1 | 2; // WHITE, GRAY, BLACK
const WHITE: Color = 0;
const GRAY: Color = 1;
const BLACK: Color = 2;

interface CycleResult {
  hasCycle: boolean;
  cyclePath?: string[]; // Node IDs in the cycle, if found
}

/**
 * Detect cycles in a directed graph using DFS
 * @param nodes - Array of workflow nodes
 * @param edges - Array of directed edges (source_node → target_node)
 * @returns CycleResult with hasCycle flag and optional cycle path
 */
export function hasCycle(nodes: NodeData[], edges: EdgeData[]): CycleResult {
  // Build adjacency list: nodeId -> [targetNodeIds]
  const adjacency: Map<string, string[]> = new Map();
  const nodeIdSet = new Set(nodes.map(n => n.node_id));
  
  for (const node of nodes) {
    adjacency.set(node.node_id, []);
  }
  
  for (const edge of edges) {
    // Only include edges where both nodes exist
    if (nodeIdSet.has(edge.source_node) && nodeIdSet.has(edge.target_node)) {
      const targets = adjacency.get(edge.source_node) || [];
      targets.push(edge.target_node);
      adjacency.set(edge.source_node, targets);
    }
  }
  
  // Color map for DFS: 0=unvisited, 1=visiting, 2=visited
  const color: Map<string, Color> = new Map();
  const parent: Map<string, string | null> = new Map();
  
  for (const nodeId of nodeIdSet) {
    color.set(nodeId, WHITE);
    parent.set(nodeId, null);
  }
  
  // Track cycle path if found
  let cyclePath: string[] | undefined;
  
  /**
   * DFS helper: returns true if cycle found starting from nodeId
   */
  function dfs(nodeId: string): boolean {
    color.set(nodeId, GRAY);
    
    const neighbors = adjacency.get(nodeId) || [];
    for (const neighbor of neighbors) {
      const neighborColor = color.get(neighbor);
      
      if (neighborColor === GRAY) {
        // Found cycle! Reconstruct path
        cyclePath = reconstructCycle(nodeId, neighbor, parent);
        return true;
      }
      
      if (neighborColor === WHITE) {
        parent.set(neighbor, nodeId);
        if (dfs(neighbor)) {
          return true;
        }
      }
    }
    
    color.set(nodeId, BLACK);
    return false;
  }
  
  /**
   * Reconstruct cycle path from back-edge
   */
  function reconstructCycle(current: string, cycleStart: string, parent: Map<string, string | null>): string[] {
    const path: string[] = [cycleStart];
    let node: string | null = current;
    
    // Walk back through parents until we reach cycleStart
    while (node !== null && node !== cycleStart) {
      path.unshift(node);
      node = parent.get(node) || null;
    }
    path.unshift(cycleStart);
    
    return path;
  }
  
  // Run DFS from each unvisited node (handles disconnected graphs)
  for (const nodeId of nodeIdSet) {
    if (color.get(nodeId) === WHITE) {
      if (dfs(nodeId)) {
        return { hasCycle: true, cyclePath };
      }
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
  
  // Map node IDs to their prompt_key for readability
  const nodeMap = new Map(nodes.map(n => [n.node_id, n.prompt_key]));
  
  const labels = cyclePath.map(id => nodeMap.get(id) || id);
  
  if (labels.length <= 5) {
    return `Cycle detected: ${labels.join(' → ')}`;
  }
  
  // Truncate long cycles
  return `Cycle detected: ${labels.slice(0, 3).join(' → ')} → ... → ${labels[labels.length - 1]}`;
}

/**
 * Validate workflow has no cycles before saving
 * @param nodes - Workflow nodes
 * @param edges - Workflow edges
 * @returns { valid: boolean, error?: string }
 */
export function validateWorkflowAcyclic(nodes: NodeData[], edges: EdgeData[]): { valid: boolean; error?: string } {
  const result = hasCycle(nodes, edges);
  
  if (result.hasCycle && result.cyclePath) {
    const description = formatCycleDescription(result.cyclePath, nodes);
    return { valid: false, error: description };
  }
  
  return { valid: true };
}