"""
Репозиторий для работы с таблицей node_executions.
"""
import json
from typing import Optional, Dict, Any, List
from .base import get_connection

def _row_to_dict(row) -> Dict[str, Any]:
    """Преобразует строку asyncpg в словарь с корректными типами."""
    if not row:
        return None
    data = dict(row)
    for key in ['id', 'run_id', 'node_definition_id', 'parent_execution_id', 'output_artifact_id', 'superseded_by_id']:
        if key in data and data[key] is not None:
            data[key] = str(data[key])
    if data.get('input_artifact_ids') and isinstance(data['input_artifact_ids'], str):
        data['input_artifact_ids'] = json.loads(data['input_artifact_ids'])
    for key in ['created_at', 'updated_at']:
        if key in data and data[key] is not None:
            data[key] = data[key].isoformat()
    return data

async def create_node_execution(
    run_id: str,
    node_definition_id: str,
    parent_execution_id: Optional[str],
    idempotency_key: str,
    input_artifact_ids: Optional[List[str]] = None,
    tx=None
) -> str:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
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
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow("SELECT * FROM node_executions WHERE id = $1", exec_id)
        return _row_to_dict(row)
    finally:
        if close_conn:
            await conn.close()

async def update_node_execution_status(
    exec_id: str,
    status: str,
    output_artifact_id: Optional[str] = None,
    tx=None
) -> None:
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
              AND parent_execution_id IS NOT DISTINCT FROM $3
              AND idempotency_key = $4
        """, run_id, node_definition_id, parent_execution_id, idempotency_key)
        return _row_to_dict(row)
    finally:
        if close_conn:
            await conn.close()

async def get_validated_execution_for_node(
    run_id: str,
    node_definition_id: str,
    tx=None
) -> Optional[Dict[str, Any]]:
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
        return _row_to_dict(row)
    finally:
        if close_conn:
            await conn.close()

async def get_active_execution_for_node(
    run_id: str,
    node_definition_id: str,
    tx=None,
    for_update: bool = False
) -> Optional[Dict[str, Any]]:
    """Возвращает VALIDATED выполнение для данного узла с опцией блокировки."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        query = """
            SELECT * FROM node_executions
            WHERE run_id = $1 AND node_definition_id = $2 AND status = 'VALIDATED'
            LIMIT 1
        """
        if for_update:
            query += " FOR UPDATE"
        row = await conn.fetchrow(query, run_id, node_definition_id)
        return _row_to_dict(row)
    finally:
        if close_conn:
            await conn.close()

async def supersede_execution(old_id: str, new_id: str, tx=None) -> None:
    """Переводит выполнение в SUPERSEDED и устанавливает superseded_by_id."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute("""
            UPDATE node_executions
            SET status = 'SUPERSEDED', superseded_by_id = $1, updated_at = NOW()
            WHERE id = $2
        """, new_id, old_id)
    finally:
        if close_conn:
            await conn.close()

async def validate_execution(exec_id: str, tx=None) -> None:
    """Переводит выполнение в VALIDATED."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute("""
            UPDATE node_executions
            SET status = 'VALIDATED', updated_at = NOW()
            WHERE id = $1
        """, exec_id)
    finally:
        if close_conn:
            await conn.close()
