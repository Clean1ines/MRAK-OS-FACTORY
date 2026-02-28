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
