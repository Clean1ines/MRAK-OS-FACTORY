// src/entities/workflow/store/syncMiddleware.ts
import { api } from '@/shared/api';
import { useWorkflowStore } from './workflowStore';

export async function syncWithServer(action: string, data: any): Promise<void> {
  const state = useWorkflowStore.getState();
  const workflowId = state.ui.currentWorkflowId;
  
  if (!workflowId) {
    console.warn('syncWithServer: No current workflow ID – skipping sync');
    return;
  }

  try {
    switch (action) {
      case 'addNode':
        await api.workflows.nodes.create(workflowId, {
          node_id: data.id || data.nodeId || crypto.randomUUID(),
          prompt_key: data.promptKey,
          config: data.config,
          position_x: data.position.x,
          position_y: data.position.y,
        });
        break;
      case 'moveNode':
        await api.workflows.nodes.update(data.nodeId, {
          position_x: data.position.x,
          position_y: data.position.y,
        });
        break;
      case 'updateNode':
        await api.workflows.nodes.update(data.nodeId, {
          prompt_key: data.config.promptKey,
          config: data.config.config,
        });
        break;
      case 'removeNode':
        await api.workflows.nodes.delete(data.nodeId);
        break;
      case 'addEdge':
        await api.workflows.edges.create(workflowId, {
          source_node: data.source,
          target_node: data.target,
          source_output: 'output',
          target_input: 'input',
        });
        break;
      case 'removeEdge':
        await api.workflows.edges.delete(data.edgeId);
        break;
      default:
        console.warn(`Unknown action: ${action}`);
    }
  } catch (error) {
    console.error('syncWithServer error:', error);
  }
}