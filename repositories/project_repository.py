import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

# Константа для владельца по умолчанию (временная, пока нет аутентификации)
DEFAULT_OWNER_ID = "default-owner"

async def get_projects(owner_id: Optional[str] = None, tx=None) -> List[Dict[str, Any]]:
    """
    Return all projects, optionally filtered by owner_id.
    If owner_id is None, returns all projects (for backward compatibility).
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        if owner_id:
            rows = await conn.fetch('''
                SELECT id, name, description, created_at, updated_at
                FROM projects
                WHERE owner_id = $1
                ORDER BY created_at DESC
            ''', owner_id)
        else:
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

async def create_project(name: str, description: str = "", owner_id: str = DEFAULT_OWNER_ID, tx=None) -> str:
    """Create a new project for a given owner and return its ID."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        project_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO projects (id, name, description, owner_id)
            VALUES ($1, $2, $3, $4)
        ''', project_id, name, description, owner_id)
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

async def check_name_exists(name: str, owner_id: str, exclude_id: Optional[str] = None, tx=None) -> bool:
    """
    Check if a project with the given name exists for the given owner.

    Args:
        name: Project name.
        owner_id: Owner identifier.
        exclude_id: If provided, exclude this project ID from the check (for updates).
        tx: Optional transaction.

    Returns:
        True if a project with the same name and owner exists (and not equal to exclude_id), else False.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        if exclude_id:
            query = "SELECT 1 FROM projects WHERE name = $1 AND owner_id = $2 AND id != $3 LIMIT 1"
            result = await conn.fetchval(query, name, owner_id, exclude_id)
        else:
            query = "SELECT 1 FROM projects WHERE name = $1 AND owner_id = $2 LIMIT 1"
            result = await conn.fetchval(query, name, owner_id)
        return result is not None
    finally:
        if close_conn:
            await conn.close()

async def update_project(project_id: str, name: str, description: str, owner_id: str = DEFAULT_OWNER_ID, tx=None) -> bool:
    """
    Update an existing project.

    Args:
        project_id: ID of the project to update.
        name: New name.
        description: New description.
        owner_id: Owner ID (should match the project's owner; used for consistency).
        tx: Optional transaction.

    Returns:
        True if the project was updated, False if not found.
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
            WHERE id = $3 AND owner_id = $4
        ''', name, description, project_id, owner_id)
        # asyncpg returns "UPDATE <count>"
        return result.split()[-1] != '0'
    finally:
        if close_conn:
            await conn.close()
