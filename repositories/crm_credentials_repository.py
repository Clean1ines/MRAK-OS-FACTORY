from typing import Optional, Dict, Any

from .base import get_connection


async def get(project_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """
    Возвращает запись crm_credentials для проекта или None.
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
            FROM crm_credentials
            WHERE project_id = $1
            """,
            project_id,
        )
        if not row:
            return None

        data = dict(row)
        # Приводим UUID-поля к строкам, если они есть
        for key in ("id", "project_id"):
            if key in data and data[key] is not None:
                data[key] = str(data[key])
        return data
    finally:
        if close_conn:
            await conn.close()


async def save(project_id: str, crm_type: str, encrypted_data: str, tx=None) -> None:
    """
    Создаёт новую запись crm_credentials для проекта.

    Предполагается одна запись на project_id. При наличии записи БД должна
    выбросить ошибку (уникальный индекс) или поведение должно быть обёрнуто выше.
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
            INSERT INTO crm_credentials (project_id, crm_type, encrypted_data)
            VALUES ($1, $2, $3)
            """,
            project_id,
            crm_type,
            encrypted_data,
        )
    finally:
        if close_conn:
            await conn.close()


async def update(
    project_id: str,
    crm_type: Optional[str] = None,
    encrypted_data: Optional[str] = None,
    tx=None,
) -> bool:
    """
    Частично обновляет запись crm_credentials для проекта.

    Возвращает True, если запись была обновлена, иначе False.
    """
    if crm_type is None and encrypted_data is None:
        return False

    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True

    try:
        set_clauses = []
        params = []

        if crm_type is not None:
            set_clauses.append("crm_type = ${}".format(len(params) + 1))
            params.append(crm_type)
        if encrypted_data is not None:
            set_clauses.append("encrypted_data = ${}".format(len(params) + 1))
            params.append(encrypted_data)

        # project_id всегда последний параметр
        params.append(project_id)
        query = f"""
            UPDATE crm_credentials
            SET {", ".join(set_clauses)}, updated_at = NOW()
            WHERE project_id = ${len(params)}
        """
        result = await conn.execute(query, *params)
        # asyncpg возвращает строку вида "UPDATE <count>"
        return result.split()[-1] != "0"
    finally:
        if close_conn:
            await conn.close()

