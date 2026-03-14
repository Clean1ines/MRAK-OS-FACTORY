"""
Репозиторий для работы с таблицей execution_queue.
"""
import uuid
from typing import Optional, Dict, Any
import json
from .base import get_connection

async def enqueue(node_execution_id: Optional[str] = None, task_type: str = "node_execution", payload: Optional[Dict[str, Any]] = None, tx=None) -> str:
    """
    Добавляет задачу в очередь со статусом PENDING.

    По умолчанию используется тип 'node_execution' и ссылка на node_execution_id.
    Для других типов задач (например, notify_manager) node_execution_id может быть None,
    а дополнительные данные передаются в payload.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        job_id = str(uuid.uuid4())
        payload_json = json.dumps(payload) if payload is not None else None
        await conn.execute(
            """
            INSERT INTO execution_queue (id, node_execution_id, status, task_type, payload, created_at, updated_at)
            VALUES ($1, $2, 'PENDING', $3, $4, NOW(), NOW())
            """,
            job_id,
            node_execution_id,
            task_type,
            payload_json,
        )
        return job_id
    finally:
        if close_conn:
            await conn.close()


async def claim_job(worker_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """
    Захватывает одну PENDING-задачу, переводит в PROCESSING и возвращает её.
    Использует FOR UPDATE SKIP LOCKED для минимизации блокировок.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow(
            """
            UPDATE execution_queue
            SET status = 'PROCESSING',
                locked_by = $1,
                locked_at = NOW(),
                updated_at = NOW()
            WHERE id = (
                SELECT id
                FROM execution_queue
                WHERE status = 'PENDING'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *
            """,
            worker_id,
        )
        if row:
            job = dict(row)
            job["id"] = str(job["id"])
            if job.get("node_execution_id") is not None:
                job["node_execution_id"] = str(job["node_execution_id"])
            if job.get("payload") and isinstance(job["payload"], str):
                try:
                    job["payload"] = json.loads(job["payload"])
                except json.JSONDecodeError:
                    # оставляем как есть, если формат неожиданный
                    pass
            job["created_at"] = job["created_at"].isoformat() if job["created_at"] else None
            job["updated_at"] = job["updated_at"].isoformat() if job["updated_at"] else None
            job["locked_at"] = job["locked_at"].isoformat() if job["locked_at"] else None
            return job
        return None
    finally:
        if close_conn:
            await conn.close()


async def complete_job(job_id: str, success: bool, tx=None) -> None:
    """Помечает задачу как DONE (success=True) или FAILED (success=False)."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        status = 'DONE' if success else 'FAILED'
        await conn.execute("""
            UPDATE execution_queue
            SET status = $1, updated_at = NOW()
            WHERE id = $2
        """, status, job_id)
    finally:
        if close_conn:
            await conn.close()


async def reset_stuck_jobs(timeout_minutes: int = 10, tx=None) -> int:
    """
    Возвращает в PENDING задачи, зависшие в PROCESSING дольше timeout_minutes.
    Возвращает количество сброшенных задач.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch("""
            UPDATE execution_queue
            SET status = 'PENDING', locked_by = NULL, locked_at = NULL, updated_at = NOW()
            WHERE status = 'PROCESSING' AND locked_at < NOW() - $1 * INTERVAL '1 minute'
            RETURNING id
        """, timeout_minutes)
        return len(rows)
    finally:
        if close_conn:
            await conn.close()