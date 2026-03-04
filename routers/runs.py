from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from schemas import (
    RunCreate, RunResponse,
    NodeExecutionCreate, NodeExecutionResponse,
    ValidateExecutionResponse
)
from repositories import run_repository, node_execution_repository, project_repository, workflow_repository, artifact_repository
from repositories.base import transaction
from use_cases.execute_node import ExecuteNodeUseCase
from dependencies import get_execute_use_case
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])

@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(run_data: RunCreate):
    """Создаёт новый Run с проверкой существования проекта и воркфлоу."""
    project = await project_repository.get_project(run_data.project_id)
    if not project:
        raise HTTPException(status_code=400, detail="Project not found")
    workflow = await workflow_repository.get_workflow(run_data.workflow_id)
    if not workflow:
        raise HTTPException(status_code=400, detail="Workflow not found")

    async with transaction() as tx:
        run_id = await run_repository.create_run(
            project_id=run_data.project_id,
            workflow_id=run_data.workflow_id,
            created_by=None,
            tx=tx,
        )
        run = await run_repository.get_run(run_id, tx=tx)
    if not run:
        raise HTTPException(status_code=500, detail="Failed to create run")
    return run

@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    run = await run_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.post("/runs/{run_id}/nodes/{node_id}/execute", response_model=NodeExecutionResponse)
async def execute_node(
    run_id: str,
    node_id: str,
    body: NodeExecutionCreate,
    background_tasks: BackgroundTasks,
    use_case: ExecuteNodeUseCase = Depends(get_execute_use_case),
):
    try:
        execution = await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
            parent_execution_id=body.parent_execution_id,
            idempotency_key=body.idempotency_key,
            input_artifact_ids=body.input_artifact_ids,
            model=None,
            background_tasks=background_tasks,
        )
        return execution
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/executions/{exec_id}/validate", response_model=ValidateExecutionResponse)
async def validate_execution(exec_id: str):
    """
    Переводит выполнение в VALIDATED, автоматически деактивируя предыдущее активное.
    Требует статус COMPLETED и run в состоянии OPEN.
    """
    async with transaction() as tx:
        # 1. Блокируем целевую запись
        target_row = await tx.conn.fetchrow(
            "SELECT * FROM node_executions WHERE id = $1 FOR UPDATE", exec_id
        )
        if not target_row:
            raise HTTPException(status_code=404, detail="Execution not found")
        target = dict(target_row)
        for k in ['id', 'run_id', 'node_definition_id', 'parent_execution_id', 'output_artifact_id']:
            if target.get(k):
                target[k] = str(target[k])

        if target["status"] != "COMPLETED":
            raise HTTPException(
                status_code=409,
                detail=f"Cannot validate execution with status {target['status']}"
            )

        run = await run_repository.get_run(target["run_id"], tx=tx)
        if not run or run["status"] != "OPEN":
            raise HTTPException(status_code=409, detail="Run is not OPEN, cannot validate")

        # FIX: use project_id instead of run_id to find active execution project-wide
        active_row = await tx.conn.fetchrow("""
            SELECT * FROM node_executions
            WHERE project_id = $1
              AND node_definition_id = $2
              AND status = 'VALIDATED'
              AND superseded_by_id IS NULL
            FOR UPDATE
        """, run["project_id"], target["node_definition_id"])

        superseded_id = None
        previous_active_id = None

        if active_row:
            active = dict(active_row)
            for k in ['id', 'output_artifact_id']:
                if active.get(k):
                    active[k] = str(active[k])
            previous_active_id = active["id"]

            await node_execution_repository.supersede_execution(active["id"], exec_id, tx=tx)
            superseded_id = active["id"]

            if active.get("output_artifact_id"):
                await artifact_repository.update_artifact_status(
                    active["output_artifact_id"], "SUPERSEDED", tx=tx
                )

        await node_execution_repository.validate_execution(exec_id, tx=tx)

        if target.get("output_artifact_id"):
            await artifact_repository.update_artifact_status(
                target["output_artifact_id"], "ACTIVE", tx=tx
            )

        # ADDED for ADR-006: update project_truth_snapshot
        project_id = run["project_id"]
        node_def_id = target["node_definition_id"]
        artifact_id = target.get("output_artifact_id")
        if artifact_id:
            artifact = await artifact_repository.get_artifact(artifact_id, tx=tx)
            logical_key = artifact.get("logical_key") if artifact else None
            version = artifact.get("version") if artifact else None
        else:
            # По ограничению validated_requires_artifact это не должно происходить, но оставим защиту
            logical_key = None
            version = None

        await tx.conn.execute("""
            INSERT INTO project_truth_snapshot
                (project_id, node_definition_id, execution_id, artifact_id, validated_at,
                 artifact_logical_key, artifact_version)
            VALUES ($1, $2, $3, $4, NOW(), $5, $6)
            ON CONFLICT (project_id, node_definition_id) DO UPDATE
            SET execution_id = EXCLUDED.execution_id,
                artifact_id = EXCLUDED.artifact_id,
                validated_at = EXCLUDED.validated_at,
                artifact_logical_key = EXCLUDED.artifact_logical_key,
                artifact_version = EXCLUDED.artifact_version,
                updated_at = NOW()
        """, project_id, node_def_id, exec_id, artifact_id, logical_key, version)

        updated = await node_execution_repository.get_node_execution(exec_id, tx=tx)

    return ValidateExecutionResponse(
        id=updated["id"],
        status=updated["status"],
        superseded_id=superseded_id,
        previous_active_id=previous_active_id,
    )

@router.post("/runs/{run_id}/freeze")
async def freeze_run(run_id: str):
    run = await run_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["status"] != "OPEN":
        raise HTTPException(status_code=400, detail=f"Run is not OPEN (status={run['status']})")
    await run_repository.update_run_status(run_id, "FROZEN")
    return {"status": "frozen"}

@router.post("/executions/{exec_id}/supersede")
async def supersede_execution(exec_id: str, new_execution_id: str):
    async with transaction() as tx:
        exec_record = await node_execution_repository.get_node_execution(exec_id, tx=tx)
        if not exec_record:
            raise HTTPException(status_code=404, detail="Execution not found")
        if exec_record["status"] not in ("VALIDATED", "COMPLETED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot supersede execution with status {exec_record['status']}"
            )
        new_exec = await node_execution_repository.get_node_execution(new_execution_id, tx=tx)
        if not new_exec:
            raise HTTPException(status_code=404, detail="New execution not found")
        await node_execution_repository.supersede_execution(exec_id, new_execution_id, tx=tx)
    return {"status": "superseded"}