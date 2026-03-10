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
    for key in ['id', 'run_id', 'node_definition_id', 'parent_execution_id', 'output_artifact_id', 'superseded_by_id', 'retry_parent_id']:
        if key in data and data[key] is not None:
            data[key] = str(data[key])
    if data.get('input_artifact_ids') and isinstance(data['input_artifact_ids'], str):
        data['input_artifact_ids'] = json.loads(data['input_artifact_ids'])
    for key in ['created_at', 'updated_at', 'validated_at', 'locked_at']:
        if key in data and data[key] is not None:
            data[key] = data[key].isoformat()
    return data

async def create_node_execution(
    run_id: str,
    node_definition_id: str,
    parent_execution_id: Optional[str],
    idempotency_key: str,
    input_artifact_ids: Optional[List[str]] = None,
    attempt: int = 1,
    max_attempts: int = 3,
    retry_parent_id: Optional[str] = None,
    clarification_session_id: Optional[str] = None,  # ADDED for dialogue support
    tx=None
) -> str:
    """
    Создаёт запись о выполнении узла с учётом попыток.
    base_idempotency_key устанавливается равным idempotency_key.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        input_artifacts_json = json.dumps(input_artifact_ids) if input_artifact_ids is not None else None
        # ADDED clarification_session_id to INSERT
        exec_id = await conn.fetchval("""
            INSERT INTO node_executions (
                run_id, node_definition_id, parent_execution_id,
                idempotency_key, input_artifact_ids, base_idempotency_key,
                attempt, max_attempts, retry_parent_id, clarification_session_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """, run_id, node_definition_id, parent_execution_id,
            idempotency_key, input_artifacts_json, idempotency_key,
            attempt, max_attempts, retry_parent_id, clarification_session_id)
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
    """
    Ищет существующее выполнение по идемпотентному ключу.
    Если передан tx, используется его соединение, иначе создаётся новое.
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
    """Переводит выполнение в VALIDATED и фиксирует validated_at."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute("""
            UPDATE node_executions
            SET status = 'VALIDATED', validated_at = NOW(), updated_at = NOW()
            WHERE id = $1
        """, exec_id)
    finally:
        if close_conn:
            await conn.close()

# ========== Новые функции для поддержки повторных попыток ==========

async def find_last_attempt_by_base_key(
    run_id: str,
    node_definition_id: str,
    parent_execution_id: Optional[str],
    base_idempotency_key: str,
    tx=None
) -> Optional[Dict[str, Any]]:
    """Возвращает последнюю попытку (с максимальным attempt) по base_key."""
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
              AND base_idempotency_key = $4
            ORDER BY attempt DESC
            LIMIT 1
        """, run_id, node_definition_id, parent_execution_id, base_idempotency_key)
        return _row_to_dict(row) if row else None
    finally:
        if close_conn:
            await conn.close()

async def create_retry_attempt(
    failed_execution: Dict[str, Any],
    tx=None
) -> str:
    """Создаёт новую попытку на основе неудачного выполнения."""
    new_attempt = failed_execution['attempt'] + 1
    return await create_node_execution(
        run_id=failed_execution['run_id'],
        node_definition_id=failed_execution['node_definition_id'],
        parent_execution_id=failed_execution['parent_execution_id'],
        idempotency_key=failed_execution['idempotency_key'],
        input_artifact_ids=failed_execution['input_artifact_ids'],
        attempt=new_attempt,
        max_attempts=failed_execution['max_attempts'],
        retry_parent_id=failed_execution['id'],
        tx=tx
    )

# ========== Функции для работы с диалоговыми узлами ==========

async def get_next_node_for_execution(execution_id: str, tx=None) -> Optional[str]:
    """
    Возвращает node_definition_id (UUID) следующего узла после данного выполнения,
    или None, если это конечный узел.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        # 1. Получаем run_id и текущий node_definition_id
        row = await conn.fetchrow("""
            SELECT run_id, node_definition_id FROM node_executions WHERE id = $1
        """, execution_id)
        if not row:
            return None
        run_id = row['run_id']
        current_node_uuid = row['node_definition_id']

        # 2. Получаем workflow_id из runs
        run_row = await conn.fetchrow("SELECT workflow_id FROM runs WHERE id = $1", run_id)
        if not run_row:
            return None
        workflow_id = run_row['workflow_id']

        # 3. Получаем node_id (текстовый) для текущего узла
        node_row = await conn.fetchrow(
            "SELECT node_id FROM workflow_nodes WHERE id = $1",
            current_node_uuid
        )
        if not node_row:
            return None
        current_node_text = node_row['node_id']

        # 4. Ищем исходящее ребро из этого узла
        edge_row = await conn.fetchrow("""
            SELECT target_node FROM workflow_edges
            WHERE workflow_id = $1 AND source_node = $2
        """, workflow_id, current_node_text)
        if not edge_row:
            return None
        target_node_text = edge_row['target_node']

        # 5. Получаем UUID целевого узла
        target_node_uuid_row = await conn.fetchrow("""
            SELECT id FROM workflow_nodes
            WHERE workflow_id = $1 AND node_id = $2
        """, workflow_id, target_node_text)
        if not target_node_uuid_row:
            return None
        return str(target_node_uuid_row['id'])
    finally:
        if close_conn:
            await conn.close()