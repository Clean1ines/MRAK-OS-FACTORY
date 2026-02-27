# CHANGED: Remove conn parameter, add optional tx; handle connection creation
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

async def get_projects(tx=None) -> List[Dict[str, Any]]:
    """Return all projects."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('''
            SELECT id, name, description, created_at, updated_at
            FROM projects
            ORDER BY created_at DESC
        ''')
        projects = []
        for row in rows:
            proj = dict(row)
            proj['id'] = str(proj['id'])
            proj['created_at'] = proj['created_at'].isoformat() if proj['created_at'] else None
            proj['updated_at'] = proj['updated_at'].isoformat() if proj['updated_at'] else None
            projects.append(proj)
        return projects
    finally:
        if close_conn:
            await conn.close()

async def create_project(name: str, description: str = "", tx=None) -> str:
    """Create a new project and return its ID."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        project_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO projects (id, name, description)
            VALUES ($1, $2, $3)
        ''', project_id, name, description)
        return project_id
    finally:
        if close_conn:
            await conn.close()

async def get_project(project_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """Return a project by ID."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM projects WHERE id = $1', project_id)
        if row:
            proj = dict(row)
            proj['id'] = str(proj['id'])
            proj['created_at'] = proj['created_at'].isoformat() if proj['created_at'] else None
            proj['updated_at'] = proj['updated_at'].isoformat() if proj['updated_at'] else None
            return proj
        return None
    finally:
        if close_conn:
            await conn.close()

async def delete_project(project_id: str, tx=None) -> None:
    """Delete a project (cascade)."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM projects WHERE id = $1', project_id)
    finally:
        if close_conn:
            await conn.close()

async def check_name_exists(name: str, exclude_id: Optional[str] = None, tx=None) -> bool:
    """
    Проверяет, существует ли проект с указанным именем.

    Args:
        name: Имя для проверки.
        exclude_id: ID проекта, который следует исключить из проверки (для обновления).
        tx: Опциональная транзакция.

    Returns:
        True, если проект с таким именем уже существует (и не равен exclude_id), иначе False.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        if exclude_id:
            query = "SELECT 1 FROM projects WHERE name = $1 AND id != $2 LIMIT 1"
            result = await conn.fetchval(query, name, exclude_id)
        else:
            query = "SELECT 1 FROM projects WHERE name = $1 LIMIT 1"
            result = await conn.fetchval(query, name)
        return result is not None
    finally:
        if close_conn:
            await conn.close()

async def update_project(project_id: str, name: str, description: str, tx=None) -> bool:
    """
    Обновляет существующий проект.

    Args:
        project_id: ID проекта.
        name: Новое имя.
        description: Новое описание.
        tx: Опциональная транзакция.

    Returns:
        True, если проект был обновлён (затронута хотя бы одна строка), иначе False.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        result = await conn.execute('''
            UPDATE projects
            SET name = $1, description = $2, updated_at = NOW()
            WHERE id = $3
        ''', name, description, project_id)
        # asyncpg возвращает строку вида "UPDATE <count>"
        return result.split()[-1] != '0'
    finally:
        if close_conn:
            await conn.close()