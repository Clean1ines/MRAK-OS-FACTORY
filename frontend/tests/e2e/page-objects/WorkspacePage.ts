import { type Page, type Locator, expect } from '@playwright/test';
/**

    Page Object for WorkspacePage.tsx E2E testing
    Encapsulates selectors and user interactions for workflow operations
     */
    export class WorkspacePage {
      readonly page: Page;

  // Canvas selectors
  readonly canvas: Locator;
  readonly nodeLocator: (nodeId: string) => Locator;
  readonly portLocator: (portId: string) => Locator;
  readonly deleteButton: (nodeId: string) => Locator;
  readonly contextMenu: Locator;
  // UI controls
  readonly saveButton: Locator;
  readonly loadButton: Locator;
  readonly workflowNameInput: Locator;
  readonly addNodeButton: Locator;
  // API endpoints for test setup/verification
  readonly apiWorkflows = '/api/workflows';
  constructor(page: Page) {
    this.page = page;
// Canvas elements
this.canvas = page.locator('.flex-1.relative.overflow-hidden');
this.nodeLocator = (nodeId: string) => page.locator(`[data-node-id="${nodeId}"]`);
this.portLocator = (portId: string) => page.locator(`[data-port-id="${portId}"]`);
this.deleteButton = (nodeId: string) => page.locator(`[data-testid="delete-${nodeId}"]`);
this.contextMenu = page.locator('.backdrop-blur-md.border.rounded-lg');

// Control buttons
this.saveButton = page.getByRole('button', { name: /save/i });
this.loadButton = page.getByRole('button', { name: /load/i });
this.workflowNameInput = page.getByLabel(/workflow name/i);
this.addNodeButton = page.getByRole('button', { name: /add node/i });
  }
  /**

    Navigate to workspace page
       */
      async goto() {
    await this.page.goto('/workspace');
    await expect(this.canvas).toBeVisible();
      }

  /**

    Create new workflow via UI
       */
      async createWorkflow(name: string) {
    await this.workflowNameInput.fill(name);
    await this.saveButton.click();
    await expect(this.page.getByText(/workflow saved/i)).toBeVisible();
      }

  /**

    Add node to canvas at specified coordinates via double-click
       */
      async addNodeAtPosition(x: number, y: number, nodeType = 'default') {
    await this.canvas.dblclick({ position: { x, y } });
    // Wait for context menu if appears, then select node type
    if (await this.contextMenu.isVisible({ timeout: 2000 })) {
     await this.contextMenu.getByText(nodeType, { exact: false }).first().click();
    }
    // Wait for node to render
    await expect(this.canvas.locator('[data-node-id]')).toBeVisible();
      }

  /**

    Connect two nodes by dragging from source port to target port
       */
      async connectNodes(sourceNodeId: string, targetNodeId: string) {
    const sourcePort = this.portLocator(${sourceNodeId}-output);
    const targetPort = this.portLocator(${targetNodeId}-input);
await expect(sourcePort).toBeVisible();
await expect(targetPort).toBeVisible();

// Drag from source port to target port
await sourcePort.dragTo(targetPort);

// Verify edge/connection was created
await expect(this.page.locator('[data-edge]')).toBeVisible();
  }
  /**

    Save current workflow state via API interception for verification
       */
      async saveWorkflow(): Promise<string | null> {
    const [response] = await Promise.all([
     this.page.waitForResponse(
       (res) => res.url().includes(this.apiWorkflows) && res.status() === 200,
       { timeout: 10000 }
     ),
     this.saveButton.click(),
    ]);
const data = await response.json();
return data?.id ?? null;
  }
  /**

    Load workflow by ID and verify nodes are rendered
       */
      async loadWorkflow(workflowId: string): Promise<Array<{ id: string; type: string }>> {
    // Intercept API call to capture loaded data
    const loadPromise = this.page.waitForResponse(
     (res) => res.url().includes(${this.apiWorkflows}/${workflowId}) && res.status() === 200,
     { timeout: 10000 }
    );

await this.page.goto(`/workspace?workflow=${workflowId}`);
const response = await loadPromise;
const workflow = await response.json();

// Verify nodes from response are rendered on canvas
if (workflow?.nodes?.length) {
  for (const node of workflow.nodes) {
    await expect(this.nodeLocator(node.id)).toBeVisible();
  }
}

return workflow?.nodes ?? [];
  }
  /**

    Delete node via UI
       */
      async deleteNode(nodeId: string) {
    const deleteBtn = this.deleteButton(nodeId);
    await expect(deleteBtn).toBeVisible();
    await deleteBtn.click();
    await expect(this.nodeLocator(nodeId)).not.toBeVisible();
      }

  /**

    Verify node count on canvas
       */
      async verifyNodeCount(expected: number) {
    const nodes = this.canvas.locator('[data-node-id]');
    await expect(nodes).toHaveCount(expected);
      }

  /**

    Verify edge/connection count
       */
      async verifyEdgeCount(expected: number) {
    const edges = this.page.locator('[data-edge]');
    await expect(edges).toHaveCount(expected);
      }
    }
    EOF

cat > tests/e2e/workspace.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';
import { WorkspacePage } from './page-objects/WorkspacePage';
test.describe('Workspace E2E Flows', () => {
  let workspace: WorkspacePage;
  test.beforeEach(async ({ page }) => {
    workspace = new WorkspacePage(page);
    await workspace.goto();
  });
  /**

    Test: Create workflow → add node → save
    Covers: REQ-022 (workflow creation), REQ-023 (node management)
       */
      test('TASK-012-01: should create workflow, add node, and save successfully', async ({ page }) => {
    const workflowName = Test Workflow ${Date.now()};

// Create new workflow
await workspace.createWorkflow(workflowName);

// Add node at canvas center (approx 400x300 for 800x600 viewport)
await workspace.addNodeAtPosition(400, 300, 'data-processor');

// Verify node was added
await workspace.verifyNodeCount(1);

// Save workflow and capture ID for verification
const workflowId = await workspace.saveWorkflow();
expect(workflowId).toBeTruthy();

// Verify save response contains our node
const savedResponse = await page.request.get(`/api/workflows/${workflowId}`);
const savedData = await savedResponse.json();

expect(savedData.nodes).toHaveLength(1);
expect(savedData.name).toBe(workflowName);
  });
  /**

    Test: Connect 2 nodes → save
    Covers: REQ-022 (edge creation), data flow validation
       */
      test('TASK-012-02: should connect two nodes and persist the connection', async ({ page }) => {
    const workflowName = Connection Test ${Date.now()};
await workspace.createWorkflow(workflowName);

// Add two nodes at different positions
await workspace.addNodeAtPosition(200, 200, 'input');
await workspace.addNodeAtPosition(600, 200, 'output');

await workspace.verifyNodeCount(2);

// Get node IDs from rendered elements
const nodeIds = await page.locator('[data-node-id]').allInnerTexts();
expect(nodeIds).toHaveLength(2);

// Connect nodes: first node output → second node input
await workspace.connectNodes(nodeIds[0], nodeIds[1]);

// Verify connection exists
await workspace.verifyEdgeCount(1);

// Save and verify edge persistence
const workflowId = await workspace.saveWorkflow();

const savedResponse = await page.request.get(`/api/workflows/${workflowId}`);
const savedData = await savedResponse.json();

expect(savedData.edges).toHaveLength(1);
expect(savedData.edges[0].source).toBe(nodeIds[0]);
expect(savedData.edges[0].target).toBe(nodeIds[1]);
  });
  /**

    Test: Load workflow → verify nodes rendered
    Covers: REQ-023 (workflow loading), state restoration
       */
      test('TASK-012-03: should load existing workflow and render all nodes correctly', async ({ page, request }) => {
    // Setup: Create and save a workflow with known state via API
    const testWorkflow = {
     name: Load Test ${Date.now()},
     nodes: [
       { id: 'node-a', type: 'input', position: { x: 100, y: 100 }, data: { label: 'Input A' } },
       { id: 'node-b', type: 'processor', position: { x: 400, y: 100 }, data: { label: 'Process B' } },
       { id: 'node-c', type: 'output', position: { x: 700, y: 100 }, data: { label: 'Output C' } },
     ],
     edges: [
       { id: 'edge-1', source: 'node-a', target: 'node-b', sourceHandle: 'output', targetHandle: 'input' },
       { id: 'edge-2', source: 'node-b', target: 'node-c', sourceHandle: 'output', targetHandle: 'input' },
     ],
    };
const createResponse = await request.post('/api/workflows', {
  data: testWorkflow,
  headers: { 'Content-Type': 'application/json' }
});
expect(createResponse.ok()).toBeTruthy();
const created = await createResponse.json();
const workflowId = created.id;

// Navigate to load the workflow
const loadedNodes = await workspace.loadWorkflow(workflowId);

// Verify all nodes from setup are rendered
expect(loadedNodes).toHaveLength(3);
await workspace.verifyNodeCount(3);
await workspace.verifyEdgeCount(2);

// Verify each node type and position roughly
for (const node of testWorkflow.nodes) {
  const nodeEl = workspace.nodeLocator(node.id);
  await expect(nodeEl).toBeVisible();
  // Verify node contains expected label
  await expect(nodeEl.getByText(node.data.label)).toBeVisible();
}
  });
});
/**

    Accessibility checks for critical flows (if QA_COUNCIL flags a11y)
     */
    test.describe('Workspace Accessibility', () => {
      test('should have proper ARIA labels on interactive canvas elements', async ({ page }) => {
     const workspace = new WorkspacePage(page);
     await workspace.goto();
     // Canvas should have role and label
     await expect(workspace.canvas).toHaveAttribute('role', 'application');
     await expect(workspace.canvas).toHaveAttribute('aria-label', /workflow canvas/i);
     // Nodes should be focusable and labeled
     await workspace.addNodeAtPosition(300, 200);
     const node = workspace.canvas.locator('[data-node-id]').first();
     await expect(node).toBeVisible();
     await expect(node).toHaveAttribute('tabindex', '0');
     await expect(node).toHaveAttribute('aria-label', /node/i);

  });
});
