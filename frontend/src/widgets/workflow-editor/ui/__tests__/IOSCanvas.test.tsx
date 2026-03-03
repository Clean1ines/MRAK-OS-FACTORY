/**
 * @vitest-environment jsdom
 */
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';
import { IOSCanvas } from '@/widgets/workflow-editor/ui/IOSCanvas';
import type { NodeData, EdgeData } from '@/widgets/workflow-editor/lib/useCanvasEngine';
import { useCanvasEngine } from '@/widgets/workflow-editor/lib/useCanvasEngine';

import '@testing-library/jest-dom/vitest';

// Mock useCanvasEngine hook
vi.mock('@/widgets/workflow-editor/lib/useCanvasEngine', () => ({
  useCanvasEngine: vi.fn(),
}));

// Mock IOSNode (исправлен путь на @/entities/node/ui/Node и добавлен вызов onDelete)
vi.mock('@/entities/node/ui/Node', () => ({
  IOSNode: vi.fn(({ node, onDragStart, onRequestDelete, onStartConnection, onCompleteConnection }) => (
    <div
      data-testid={`node-${node.node_id}`}
      data-node-id={node.node_id}
      onMouseDown={(e) => onDragStart?.(node.node_id, e)}
      onContextMenu={(e) => {
        e.preventDefault();
        onStartConnection?.(node.node_id);
      }}
      onClick={() => onCompleteConnection?.(node.node_id)}
    >
      <button 
        data-testid={`delete-${node.node_id}`} 
        onClick={() => onRequestDelete?.(node.recordId, node.node_id, node.prompt_key)}
      >
        Delete
      </button>
      <div 
        data-testid={`port-${node.node_id}`} 
        data-port-id={node.node_id}
        onClick={(e) => {
          e.stopPropagation();
          onStartConnection?.(node.node_id);
        }}
      />
      {node.prompt_key}
    </div>
  )),
}));

const mockUseCanvasEngine = vi.mocked(useCanvasEngine);
const mockUuid = 'test-uuid-12345';

describe('IOSCanvas', () => {
  const mockNodes: NodeData[] = [
    {
      id: '1',
      node_id: 'node-1',
      prompt_key: 'IDEA_CLARIFIER',
      position_x: 100,
      position_y: 200,
      config: {},
      recordId: 'rec-1',
    },
  ];
  
  const mockEdges: EdgeData[] = [
    {
      id: 'edge-1',
      source_node: 'node-1',
      target_node: 'node-2',
    },
  ];

  const mockOnNodesChange = vi.fn();
  const mockOnEdgesChange = vi.fn();
  const mockOnAddCustomNode = vi.fn();
  const mockOnRequestDeleteNode = vi.fn(); // Добавили мок для удаления узла

  const mockCanvasEngineReturn = {
    pan: { x: 0, y: 0 },
    scale: 1,
    selectedNode: null,
    handleWheel: vi.fn(),
    handlePanStart: vi.fn(),
    handleMouseMove: vi.fn(),
    handleMouseUp: vi.fn(),
    handleNodeDragStart: vi.fn(),
    setSelectedNode: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCanvasEngine.mockReturnValue(mockCanvasEngineReturn);
    vi.spyOn(global.crypto, 'randomUUID').mockReturnValue(mockUuid);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('renders nodes and edges from props', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    expect(screen.getByTestId('node-node-1')).toBeInTheDocument();
  });

  it('calls onAddCustomNode on canvas double-click', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onAddCustomNode={mockOnAddCustomNode}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const canvas = screen.getByTestId('workspace-canvas');
    
    const originalGetBCR = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: () => ({}),
    }));

    fireEvent.doubleClick(canvas, { clientX: 150, clientY: 100 });

    Element.prototype.getBoundingClientRect = originalGetBCR;

    expect(mockOnAddCustomNode).toHaveBeenCalled();
    const callArgs = mockOnAddCustomNode.mock.calls[0];
    expect(typeof callArgs[0]).toBe('number');
    expect(typeof callArgs[1]).toBe('number');
  });

  it('adds node from context menu when button is clicked', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const canvas = screen.getByTestId('workspace-canvas');
    
    fireEvent.contextMenu(canvas, { clientX: 200, clientY: 150, button: 2 });
    
    const ideaBtn = screen.getByText('💡 Idea Clarifier');
    expect(ideaBtn).toBeInTheDocument();
    
    fireEvent.click(ideaBtn);

    expect(mockOnNodesChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          node_id: mockUuid,
          prompt_key: 'IDEA_CLARIFIER',
        }),
      ])
    );
  });

  it('calls handleNodeDragStart when node drag begins', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const node = screen.getByTestId('node-node-1');
    fireEvent.mouseDown(node, { button: 0, clientX: 10, clientY: 10 });
    
    expect(mockCanvasEngineReturn.handleNodeDragStart).toHaveBeenCalledWith(
      'node-1',
      expect.any(Object)
    );
  });

  it('delegates wheel events to handleWheel with container rect', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const canvas = screen.getByTestId('workspace-canvas');
    
    const originalGetBCR = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = vi.fn(() => ({
      left: 0, top: 0, width: 1000, height: 800,
      right: 1000, bottom: 800, x: 0, y: 0, toJSON: () => ({}),
    }));

    fireEvent.wheel(canvas, { deltaY: -100, clientX: 500, clientY: 400 });

    Element.prototype.getBoundingClientRect = originalGetBCR;

    expect(mockCanvasEngineReturn.handleWheel).toHaveBeenCalled();
  });

  it('creates edge when connection is completed between two nodes', () => {
    const nodesWithTwo = [
      ...mockNodes,
      {
        id: '2',
        node_id: 'node-2',
        prompt_key: 'CODE_GEN',
        position_x: 300,
        position_y: 200,
        config: {},
        recordId: 'rec-2',
      },
    ];

    render(
      <IOSCanvas
        nodes={nodesWithTwo}
        edges={[]}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const port1 = screen.getByTestId('port-node-1');
    fireEvent.click(port1);

    const node2 = screen.getByTestId('node-node-2');
    fireEvent.click(node2);

    expect(mockOnEdgesChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          source_node: 'node-1',
          target_node: 'node-2',
        }),
      ])
    );
  });

  it('calls onRequestDeleteNode when delete button is clicked', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const deleteBtn = screen.getByTestId('delete-node-1');
    fireEvent.click(deleteBtn);

    expect(mockOnRequestDeleteNode).toHaveBeenCalledWith(
      'rec-1',  // recordId
      'node-1', // node_id
      'IDEA_CLARIFIER' // prompt_key
    );
  });

  it('has expected canvas container classes', () => {
    render(
      <IOSCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodesChange={mockOnNodesChange}
        onEdgesChange={mockOnEdgesChange}
        onRequestDeleteNode={mockOnRequestDeleteNode}
      />
    );

    const canvas = screen.getByTestId('workspace-canvas');
    expect(canvas).toHaveClass('cursor-crosshair');
  });
});
