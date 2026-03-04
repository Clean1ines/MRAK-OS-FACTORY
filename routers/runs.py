from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from schemas import (
    RunCreate, RunResponse,
    NodeExecutionCreate, NodeExecutionResponse
)
from repositories import run_repository, node_execution_repository
from repositories.base import transaction
from use_cases.execute_node import ExecuteNodeUseCase
from dependencies import get_execute_use_case
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])

@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(run_data: RunCreate):
    """Создаёт новый Run."""
    async with transaction() as tx:
        run_id = await run_repository.create_run(
            project_id=run_data.project_id,
            workflow_id=run_data.workflow_id,
            created_by=None,  # позже можно достать из сессии
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
    """
    Идемпотентное выполнение узла в рамках Run.
    Возвращает существующее или новое NodeExecution.
    """
    try:
        execution = await use_case.execute(
            run_id=run_id,
            node_definition_id=node_id,
            parent_execution_id=body.parent_execution_id,
            idempotency_key=body.idempotency_key,
            input_artifact_ids=body.input_artifact_ids,
            model=None,  # модель можно добавить в схему позже
            background_tasks=background_tasks,
        )
        return execution
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/executions/{exec_id}/validate", response_model=NodeExecutionResponse)
async def validate_execution(exec_id: str):
    """Переводит выполнение в статус VALIDATED, автоматически деактивируя предыдущее активное."""
    async with transaction() as tx:
        exec_record = await node_execution_repository.get_node_execution(exec_id, tx=tx)
        if not exec_record:
            raise HTTPException(status_code=404, detail="Execution not found")
        if exec_record["status"] != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot validate execution with status {exec_record['status']}"
            )

        # Найти предыдущее VALIDATED для этого же узла в том же run
        previous = await node_execution_repository.get_validated_execution_for_node(
            run_id=exec_record["run_id"],
            node_definition_id=exec_record["node_definition_id"],
            tx=tx,
        )
        if previous:
            # Перевести предыдущее в SUPERSEDED
            await node_execution_repository.update_node_execution_status(
                exec_id=previous["id"],
                status="SUPERSEDED",
                tx=tx,
            )

        # Обновить текущее на VALIDATED
        await node_execution_repository.update_node_execution_status(
            exec_id=exec_id,
            status="VALIDATED",
            tx=tx,
        )

        updated = await node_execution_repository.get_node_execution(exec_id, tx=tx)
    return updated

@router.post("/runs/{run_id}/freeze")
async def freeze_run(run_id: str):
    """Заморозить Run (перевести в FROZEN)."""
    run = await run_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["status"] != "OPEN":
        raise HTTPException(
            status_code=400,
            detail=f"Run is not OPEN (status={run['status']})"
        )

    await run_repository.update_run_status(run_id, "FROZEN")
    return {"status": "frozen"}

@router.post("/executions/{exec_id}/supersede")
async def supersede_execution(exec_id: str, new_execution_id: str):
    """Помечает выполнение как заменённое новым."""
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

        # Переводим текущее в SUPERSEDED
        await node_execution_repository.update_node_execution_status(
            exec_id=exec_id,
            status="SUPERSEDED",
            tx=tx,
        )
    return {"status": "superseded"}