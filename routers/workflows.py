# CHANGED: Use workflow_engine directly, remove orchestrator
# CHANGED: Добавлена поддержка nodes/edges в create и update
# CHANGED: Добавлен query-параметр project_id для list_workflows, project_id в create_workflow
# ADDED: Принты для отладки
# FIXED: Возврат словаря вместо JSONResponse для корректного статуса 201 (декоратор устанавливает статус)
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
import db
from repositories.base import transaction
from schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowNodeCreate,
    WorkflowNodeUpdate, WorkflowEdgeCreate
)
from validation import ValidationError
from use_cases.execute_workflow_step import ExecuteWorkflowStepUseCase
from services import workflow_engine
import logging

logger = logging.getLogger("MRAK-SERVER")

router = APIRouter(prefix="/api", tags=["workflows"])

@router.get("/workflows")
async def list_workflows(project_id: Optional[str] = Query(None, description="Filter workflows by project ID")):
    print(f"📥 GET /workflows project_id={project_id}")
    workflows = await db.list_workflows(project_id=project_id)
    print(f"📤 GET /workflows returning {len(workflows)} workflows")
    return JSONResponse(content=workflows)

@router.post("/workflows", status_code=201)
async def create_workflow(workflow: WorkflowCreate):
    print(f"📥 POST /workflows name={workflow.name}, project_id={workflow.project_id}")
    async with transaction() as tx:
        wf_id = await db.create_workflow(
            name=workflow.name,
            description=workflow.description,
            is_default=workflow.is_default,
            project_id=workflow.project_id,
            tx=tx
        )
        if workflow.nodes or workflow.edges:
            nodes_data = [node.dict() for node in workflow.nodes]
            edges_data = [edge.dict() for edge in workflow.edges]
            print(f"   nodes: {len(nodes_data)}, edges: {len(edges_data)}")
            await db.sync_workflow_graph(wf_id, nodes_data, edges_data, tx)
    print(f"📤 POST /workflows created {wf_id}")
    # Возвращаем словарь, FastAPI автоматически установит статус 201 благодаря декоратору
    return {"id": wf_id}

@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    print(f"📥 GET /workflows/{workflow_id}")
    wf = await db.get_workflow(workflow_id)
    if not wf:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)
    nodes = await db.get_workflow_nodes(workflow_id)
    edges = await db.get_workflow_edges(workflow_id)
    print(f"📤 GET /workflows/{workflow_id} returning workflow with {len(nodes)} nodes, {len(edges)} edges")
    return JSONResponse(content={
        "workflow": wf,
        "nodes": nodes,
        "edges": edges
    })

@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, wf_update: WorkflowUpdate):
    print(f"📥 PUT /workflows/{workflow_id}")
    existing = await db.get_workflow(workflow_id)
    if not existing:
        return JSONResponse(content={"error": "Workflow not found"}, status_code=404)

    async with transaction() as tx:
        update_data = wf_update.dict(exclude_unset=True)
        nodes_to_sync = update_data.pop('nodes', None)
        edges_to_sync = update_data.pop('edges', None)

        if update_data:
            print(f"   updating workflow metadata: {update_data}")
            await db.update_workflow(workflow_id, tx=tx, **update_data)

        # Если оба списка переданы, синхронизируем граф
        if nodes_to_sync is not None and edges_to_sync is not None:
            print(f"   syncing graph: {len(nodes_to_sync)} nodes, {len(edges_to_sync)} edges")
            await db.sync_workflow_graph(workflow_id, nodes_to_sync, edges_to_sync, tx)
        elif nodes_to_sync is not None or edges_to_sync is not None:
            print(f"   WARNING: partial graph update skipped")

    print(f"📤 PUT /workflows/{workflow_id} completed")
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
    return {"id": record_id}  # возвращаем словарь для корректного статуса 201

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
    return {"id": edge_id}  # возвращаем словарь для статуса 201

@router.delete("/workflows/edges/{edge_record_id}")
async def delete_workflow_edge(edge_record_id: str):
    async with transaction() as tx:
        await db.delete_workflow_edge(edge_record_id, tx=tx)
    return JSONResponse(content={"status": "deleted"})

# ==================== ПРОСТОЙ РЕЖИМ ====================
@router.get("/workflow/next")
async def get_next_step(project_id: str):
    try:
        step = await workflow_engine.get_next_step(project_id)
        if step:
            return JSONResponse(content=step)
        else:
            return JSONResponse(content={"next_stage": "finished", "description": "Проект завершён"})
    except Exception as e:
        logger.error(f"Error getting next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/workflow/execute_next")
async def execute_next_step(project_id: str, model: Optional[str] = None):
    use_case = ExecuteWorkflowStepUseCase(workflow_engine)
    try:
        result = await use_case.execute(project_id, model)
        return JSONResponse(content=result)
    except ValidationError as e:
        logger.warning(f"Validation error in simple mode: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=422)
    except Exception as e:
        logger.error(f"Error executing next step: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
