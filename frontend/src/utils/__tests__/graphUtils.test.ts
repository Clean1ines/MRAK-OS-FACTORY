// frontend/src/utils/__tests__/graphUtils.test.ts
// ADDED: Unit tests for cycle detection in workflow graphs

import { describe, it, expect } from 'vitest';
import { hasCycle, formatCycleDescription, validateWorkflowAcyclic } from '../graphUtils';
import type { NodeData, EdgeData } from '../../hooks/useCanvasEngine';

// Helper to create test nodes
const makeNode = (id: string, prompt_key: string): NodeData => ({
  id: crypto.randomUUID(),
  node_id: id,
  prompt_key,
  position_x: 0,
  position_y: 0,
  config: {},
});

describe('graphUtils - Cycle Detection', () => {
  describe('hasCycle - Basic Cases', () => {
    it('should return false for empty graph', () => {
      const result = hasCycle([], []);
      expect(result.hasCycle).toBe(false);
    });

    it('should return false for single node with no edges', () => {
      const nodes = [makeNode('A', 'NODE_A')];
      const result = hasCycle(nodes, []);
      expect(result.hasCycle).toBe(false);
    });

    it('should return false for linear chain A→B→C', () => {
      const nodes = [
        makeNode('A', 'NODE_A'),
        makeNode('B', 'NODE_B'),
        makeNode('C', 'NODE_C'),
      ];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'B' },
        { id: 'e2', source_node: 'B', target_node: 'C' },
      ];
      const result = hasCycle(nodes, edges);
      expect(result.hasCycle).toBe(false);
    });
  });

  describe('hasCycle - Cycle Detection', () => {
    it('should detect simple 2-node cycle A→B→A', () => {
      const nodes = [makeNode('A', 'NODE_A'), makeNode('B', 'NODE_B')];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'B' },
        { id: 'e2', source_node: 'B', target_node: 'A' },
      ];
      const result = hasCycle(nodes, edges);
      expect(result.hasCycle).toBe(true);
      expect(result.cyclePath).toBeDefined();
    });

    it('should detect 3-node cycle A→B→C→A', () => {
      const nodes = [
        makeNode('A', 'NODE_A'),
        makeNode('B', 'NODE_B'),
        makeNode('C', 'NODE_C'),
      ];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'B' },
        { id: 'e2', source_node: 'B', target_node: 'C' },
        { id: 'e3', source_node: 'C', target_node: 'A' },
      ];
      const result = hasCycle(nodes, edges);
      expect(result.hasCycle).toBe(true);
      expect(result.cyclePath?.length).toBe(4); // A→B→C→A
    });

    it('should detect cycle in larger graph with extra nodes', () => {
      const nodes = [
        makeNode('A', 'NODE_A'),
        makeNode('B', 'NODE_B'),
        makeNode('C', 'NODE_C'),
        makeNode('D', 'NODE_D'), // Not part of cycle
      ];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'B' },
        { id: 'e2', source_node: 'B', target_node: 'C' },
        { id: 'e3', source_node: 'C', target_node: 'A' }, // Cycle
        { id: 'e4', source_node: 'C', target_node: 'D' }, // Extra edge
      ];
      const result = hasCycle(nodes, edges);
      expect(result.hasCycle).toBe(true);
    });

    it('should handle self-loop A→A', () => {
      const nodes = [makeNode('A', 'NODE_A')];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'A' },
      ];
      const result = hasCycle(nodes, edges);
      expect(result.hasCycle).toBe(true);
    });
  });

  describe('formatCycleDescription', () => {
    it('should format short cycle with node labels', () => {
      const nodes = [
        makeNode('A', 'IDEA_CLARIFIER'),
        makeNode('B', 'BUSINESS_REQ'),
        makeNode('C', 'CODE_GEN'),
      ];
      const cyclePath = ['A', 'B', 'C', 'A'];
      const desc = formatCycleDescription(cyclePath, nodes);
      expect(desc).toContain('IDEA_CLARIFIER');
      expect(desc).toContain('→');
    });

    it('should truncate long cycle descriptions', () => {
      const nodes = Array.from({ length: 10 }, (_, i) => 
        makeNode(`N${i}`, `NODE_${i}`)
      );
      const cyclePath = Array.from({ length: 11 }, (_, i) => `N${i % 10}`);
      const desc = formatCycleDescription(cyclePath, nodes);
      expect(desc).toContain('...');
    });
  });

  describe('validateWorkflowAcyclic', () => {
    it('should return valid:true for acyclic graph', () => {
      const nodes = [makeNode('A', 'A'), makeNode('B', 'B')];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'B' },
      ];
      const result = validateWorkflowAcyclic(nodes, edges);
      expect(result.valid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should return valid:false with error message for cyclic graph', () => {
      const nodes = [makeNode('A', 'NODE_A'), makeNode('B', 'NODE_B')];
      const edges: EdgeData[] = [
        { id: 'e1', source_node: 'A', target_node: 'B' },
        { id: 'e2', source_node: 'B', target_node: 'A' },
      ];
      const result = validateWorkflowAcyclic(nodes, edges);
      expect(result.valid).toBe(false);
      expect(result.error).toContain('Cycle detected');
    });
  });

  describe('Performance', () => {
    it('should detect cycle in ≤10ms for 100 nodes', () => {
      // Create 100 nodes in a chain + one edge to create cycle
      const nodes = Array.from({ length: 100 }, (_, i) => 
        makeNode(`N${i}`, `NODE_${i}`)
      );
      const edges: EdgeData[] = [];
      
      // Linear chain: N0→N1→N2→...→N99
      for (let i = 0; i < 99; i++) {
        edges.push({ id: `e${i}`, source_node: `N${i}`, target_node: `N${i + 1}` });
      }
      // Add cycle: N99→N50
      edges.push({ id: 'e-cycle', source_node: 'N99', target_node: 'N50' });
      
      const start = performance.now();
      const result = hasCycle(nodes, edges);
      const elapsed = performance.now() - start;
      
      expect(result.hasCycle).toBe(true);
      expect(elapsed).toBeLessThan(10);
    });
  });
});