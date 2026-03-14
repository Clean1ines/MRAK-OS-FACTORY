from typing import Optional, Dict, Any

from .base import get_connection


async def upsert_client(chat_id: int, project_id: str, crm_contact_id: str, tx=None) -> None:
    """
    Создаёт или обновляет запись telegram-клиента по (chat_id, project_id).
    Обновляет crm_contact_id, если запись уже существует.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        await conn.execute(
            """
            INSERT INTO telegram_clients (chat_id, project_id, crm_contact_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (chat_id, project_id) DO UPDATE
            SET crm_contact_id = EXCLUDED.crm_contact_id,
                updated_at = NOW()
            """,
            chat_id,
            project_id,
            crm_contact_id,
        )
    finally:
        if close_conn:
            await conn.close()


async def get_client_by_chat_and_project(chat_id: int, project_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """
    Возвращает клиента по chat_id и project_id.
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
            SELECT *
            FROM telegram_clients
            WHERE chat_id = $1 AND project_id = $2
            """,
            chat_id,
            project_id,
        )
        if not row:
            return None
        data = dict(row)
        for key in ("id", "project_id", "last_run_id", "last_execution_id"):
            if key in data and data[key] is not None:
                data[key] = str(data[key])
        return data
    finally:
        if close_conn:
            await conn.close()


async def get_client_by_last_run(run_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """
    Возвращает клиента по last_run_id.
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
            SELECT *
            FROM telegram_clients
            WHERE last_run_id = $1
            """,
            run_id,
        )
        if not row:
            return None
        data = dict(row)
        for key in ("id", "project_id", "last_run_id", "last_execution_id"):
            if key in data and data[key] is not None:
                data[key] = str(data[key])
        return data
    finally:
        if close_conn:
            await conn.close()


async def update_last_run_and_execution(
    chat_id: int,
    project_id: str,
    last_run_id: Optional[str],
    last_execution_id: Optional[str],
    tx=None,
) -> None:
    """
    Обновляет last_run_id и last_execution_id для клиента.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        await conn.execute(
            """
            UPDATE telegram_clients
            SET last_run_id = $3,
                last_execution_id = $4,
                updated_at = NOW()
            WHERE chat_id = $1 AND project_id = $2
            """,
            chat_id,
            project_id,
            last_run_id,
            last_execution_id,
        )
    finally:
        if close_conn:
            await conn.close()

