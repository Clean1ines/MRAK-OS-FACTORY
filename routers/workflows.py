# CHANGED: Use use cases for simple mode endpoints
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Optional
import db
from repositories.base import transaction
from schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowNodeCreate,
    WorkflowNodeUpdate, WorkflowEdgeCreate
)
from orchestrator import MrakOrchestrator
from validation import ValidationError
from use_cases.execute_workflow_step import ExecuteWorkflowStepUseCase
import logging

logger = logging.getLogger("MRAK-SERVER")
orch = MrakOrchestrator()

router = APIRouter(prefix="/api", tags=["workflows"])

@router.get("/workflows")
async def list_workflows():
    workflows = await db.list_workflows()
    return JSONResponse(content=workflows)

@router.post("/workflows", status_code=201)
async def create_workflow(workflow: WorkflowCreate):
    async with transaction() as tx:
        wf_id = await db.create_workflow(workflow.name, workflow.description, workflow.is_default, tx=tx)
    return JSONResponse(content={"id": wf_id})

@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    wf = await db.get_workflow(workflow_id)
    if not wf:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)
    nodes = await db.get_workflow_nodes(workflow_id)
    edges = await db.get_workflow_edges(workflow_id)
    return JSONResponse(content={
        "workflow": wf,
        "nodes": nodes,
        "edges": edges
    })

@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, wf_update: WorkflowUpdate):
    existing = await db.get_workflow(workflow_id)
    if not existing:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)
    update_data = wf_update.dict(exclude_unset=True)
    if update_data:
        async with transaction() as tx:
            await db.update_workflow(workflow_id, tx=tx, **update_data)
    return JSONResponse(content={"status": "updated"})

@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    existing = await db.get_workflow(workflow_id)
    if not existing:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)
    async with transaction() as tx:
        await db.delete_workflow(workflow_id, tx=tx)
    return JSONResponse(content={"status": "deleted"})

# ----- Узлы -----

@router.post("/workflows/{workflow_id}/nodes", status_code=201)
async def create_workflow_node(workflow_id: str, node: WorkflowNodeCreate):
    wf = await db.get_workflow(workflow_id)
    if not wf:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)
    existing_nodes = await db.get_workflow_nodes(workflow_id)
    if any(n['node_id'] == node.node_id for n in existing_nodes):
        return JSONResponse(content={"error": f"Node with id '{node.node_id}' already exists in this workflow"}, status_code=400)
    async with transaction() as tx:
        record_id = await db.create_workflow_node(
            workflow_id, node.node_id, node.prompt_key, node.config,
            node.position_x, node.position_y, tx=tx
        )
    return JSONResponse(content={"id": record_id})

@router.put("/workflows/nodes/{node_record_id}")
async def update_workflow_node(node_record_id: str, node_update: WorkflowNodeUpdate):
    update_data = node_update.dict(exclude_unset=True)
    if update_data:
        async with transaction() as tx:
            await db.update_workflow_node(node_record_id, tx=tx, **update_data)
    return JSONResponse(content={"status": "updated"})

@router.delete("/workflows/nodes/{node_record_id}")
async def delete_workflow_node(node_record_id: str):
    async with transaction() as tx:
        await db.delete_workflow_node(node_record_id, tx=tx)
    return JSONResponse(content={"status": "deleted"})

# ----- Рёбра -----

@router.post("/workflows/{workflow_id}/edges", status_code=201)
async def create_workflow_edge(workflow_id: str, edge: WorkflowEdgeCreate):
    wf = await db.get_workflow(workflow_id)
    if not wf:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)
    nodes = await db.get_workflow_nodes(workflow_id)
    node_ids = [n['node_id'] for n in nodes]
    if edge.source_node not in node_ids:
        return JSONResponse(content={"error": f"Source node '{edge.source_node}' not found in workflow"}, status_code=400)
    if edge.target_node not in node_ids:
        return JSONResponse(content={"error": f"Target node '{edge.target_node}' not found in workflow"}, status_code=400)
    async with transaction() as tx:
        edge_id = await db.create_workflow_edge(
            workflow_id, edge.source_node, edge.target_node,
            edge.source_output, edge.target_input, tx=tx
        )
    return JSONResponse(content={"id": edge_id})

@router.delete("/workflows/edges/{edge_record_id}")
async def delete_workflow_edge(edge_record_id: str):
    async with transaction() as tx:
        await db.delete_workflow_edge(edge_record_id, tx=tx)
    return JSONResponse(content={"status": "deleted"})

# ==================== ПРОСТОЙ РЕЖИМ ====================
@router.get("/workflow/next")
async def get_next_step(project_id: str):
    try:
        step = await orch.get_next_step(project_id)
        if step:
            return JSONResponse(content=step)
        else:
            return JSONResponse(content={"next_stage": "finished", "description": "Проект завершён"})
    except Exception as e:
        logger.error(f"Error getting next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/workflow/execute_next")
async def execute_next_step(project_id: str, model: Optional[str] = None):
    use_case = ExecuteWorkflowStepUseCase(orch)
    try:
        result = await use_case.execute(project_id, model)
        return JSONResponse(content=result)
    except ValidationError as e:
        logger.warning(f"Validation error in simple mode: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=422)
    except Exception as e:
        logger.error(f"Error executing next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
