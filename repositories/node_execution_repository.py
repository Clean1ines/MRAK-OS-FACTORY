"""
Репозиторий для работы с таблицей node_executions.
"""
import json
from typing import Optional, Dict, Any, List
from .base import get_connection

async def create_node_execution(
    run_id: str,
    node_definition_id: str,
    parent_execution_id: Optional[str],
    idempotency_key: str,
    input_artifact_ids: Optional[List[str]] = None,
    tx=None
) -> str:
    """
    Создаёт новую запись NodeExecution со статусом PROCESSING.
    Возвращает ID созданной записи.
    input_artifact_ids преобразуется в JSONB (через json.dumps).
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        # Преобразуем список UUID в JSON-строку (asyncpg ожидает строку для JSONB)
        input_artifacts_json = json.dumps(input_artifact_ids) if input_artifact_ids is not None else None
        exec_id = await conn.fetchval("""
            INSERT INTO node_executions (
                run_id, node_definition_id, parent_execution_id,
                idempotency_key, input_artifact_ids
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, run_id, node_definition_id, parent_execution_id,
            idempotency_key, input_artifacts_json)
        return str(exec_id)
    finally:
        if close_conn:
            await conn.close()

async def get_node_execution(exec_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """
    Возвращает запись NodeExecution по ID или None.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        row = await conn.fetchrow("SELECT * FROM node_executions WHERE id = $1", exec_id)
        if row:
            exec_dict = dict(row)
            # Преобразуем UUID в строки
            exec_dict['id'] = str(exec_dict['id'])
            exec_dict['run_id'] = str(exec_dict['run_id'])
            exec_dict['node_definition_id'] = str(exec_dict['node_definition_id'])
            if exec_dict['parent_execution_id']:
                exec_dict['parent_execution_id'] = str(exec_dict['parent_execution_id'])
            if exec_dict['output_artifact_id']:
                exec_dict['output_artifact_id'] = str(exec_dict['output_artifact_id'])
            # Парсим input_artifact_ids, если это строка (потому что сохраняли как JSON-строку)
            if exec_dict['input_artifact_ids'] and isinstance(exec_dict['input_artifact_ids'], str):
                exec_dict['input_artifact_ids'] = json.loads(exec_dict['input_artifact_ids'])
            exec_dict['created_at'] = exec_dict['created_at'].isoformat() if exec_dict['created_at'] else None
            exec_dict['updated_at'] = exec_dict['updated_at'].isoformat() if exec_dict['updated_at'] else None
            return exec_dict
        return None
    finally:
        if close_conn:
            await conn.close()

async def update_node_execution_status(
    exec_id: str,
    status: str,
    output_artifact_id: Optional[str] = None,
    tx=None
) -> None:
    """
    Обновляет статус NodeExecution и, если указан, output_artifact_id.
    Также обновляет updated_at.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        if output_artifact_id:
            await conn.execute("""
                UPDATE node_executions
                SET status = $1, output_artifact_id = $2, updated_at = NOW()
                WHERE id = $3
            """, status, output_artifact_id, exec_id)
        else:
            await conn.execute("""
                UPDATE node_executions
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, status, exec_id)
    finally:
        if close_conn:
            await conn.close()

async def find_existing_execution(
    run_id: str,
    node_definition_id: str,
    parent_execution_id: Optional[str],
    idempotency_key: str,
    tx=None
) -> Optional[Dict[str, Any]]:
    """
    Ищет существующее выполнение по уникальным полям (для идемпотентности).
    Возвращает запись, если найдена, иначе None.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        # parent_execution_id может быть NULL, поэтому используем IS NOT DISTINCT FROM
        row = await conn.fetchrow("""
            SELECT * FROM node_executions
            WHERE run_id = $1
              AND node_definition_id = $2
              AND parent_execution_id IS NOT DISTINCT FROM $3
              AND idempotency_key = $4
        """, run_id, node_definition_id, parent_execution_id, idempotency_key)
        if row:
            exec_dict = dict(row)
            exec_dict['id'] = str(exec_dict['id'])
            exec_dict['run_id'] = str(exec_dict['run_id'])
            exec_dict['node_definition_id'] = str(exec_dict['node_definition_id'])
            if exec_dict['parent_execution_id']:
                exec_dict['parent_execution_id'] = str(exec_dict['parent_execution_id'])
            if exec_dict['output_artifact_id']:
                exec_dict['output_artifact_id'] = str(exec_dict['output_artifact_id'])
            if exec_dict['input_artifact_ids'] and isinstance(exec_dict['input_artifact_ids'], str):
                exec_dict['input_artifact_ids'] = json.loads(exec_dict['input_artifact_ids'])
            exec_dict['created_at'] = exec_dict['created_at'].isoformat() if exec_dict['created_at'] else None
            exec_dict['updated_at'] = exec_dict['updated_at'].isoformat() if exec_dict['updated_at'] else None
            return exec_dict
        return None
    finally:
        if close_conn:
            await conn.close()

async def get_validated_execution_for_node(
    run_id: str,
    node_definition_id: str,
    tx=None
) -> Optional[Dict[str, Any]]:
    """
    Возвращает выполнение со статусом VALIDATED для данного узла в рамках run.
    Предполагается, что не более одного (инвариант).
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        row = await conn.fetchrow("""
            SELECT * FROM node_executions
            WHERE run_id = $1
              AND node_definition_id = $2
              AND status = 'VALIDATED'
            LIMIT 1
        """, run_id, node_definition_id)
        if row:
            exec_dict = dict(row)
            exec_dict['id'] = str(exec_dict['id'])
            exec_dict['run_id'] = str(exec_dict['run_id'])
            exec_dict['node_definition_id'] = str(exec_dict['node_definition_id'])
            if exec_dict['parent_execution_id']:
                exec_dict['parent_execution_id'] = str(exec_dict['parent_execution_id'])
            if exec_dict['output_artifact_id']:
                exec_dict['output_artifact_id'] = str(exec_dict['output_artifact_id'])
            if exec_dict['input_artifact_ids'] and isinstance(exec_dict['input_artifact_ids'], str):
                exec_dict['input_artifact_ids'] = json.loads(exec_dict['input_artifact_ids'])
            exec_dict['created_at'] = exec_dict['created_at'].isoformat() if exec_dict['created_at'] else None
            exec_dict['updated_at'] = exec_dict['updated_at'].isoformat() if exec_dict['updated_at'] else None
            return exec_dict
        return None
    finally:
        if close_conn:
            await conn.close()
