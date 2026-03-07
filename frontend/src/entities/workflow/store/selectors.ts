import { useWorkflowStore } from './workflowStore';
import { GraphNode } from './types';

export const useVisibleNodes = (): GraphNode[] => {
  return useWorkflowStore((state) => {
    const { nodes } = state.graph;
    const { positions } = state.layout;
    const { zoom, cameraX, cameraY } = state.viewport;
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;
    const margin = 200;

    const visible: GraphNode[] = [];
    for (const node of nodes) {
      const pos = positions[node.id];
      if (!pos) continue;
      const screenX = pos.x * zoom + cameraX;
      const screenY = pos.y * zoom + cameraY;
      if (
        screenX > -margin &&
        screenX < screenWidth + margin &&
        screenY > -margin &&
        screenY < screenHeight + margin
      ) {
        visible.push(node);
      }
    }
    return visible;
  });
};