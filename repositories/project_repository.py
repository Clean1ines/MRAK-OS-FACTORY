# ADDED: Project repository
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

async def get_projects(conn=None) -> List[Dict[str, Any]]:
    close_conn = False
    if conn is None:
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

async def create_project(name: str, description: str = "", conn=None) -> str:
    close_conn = False
    if conn is None:
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

async def get_project(project_id: str, conn=None) -> Optional[Dict[str, Any]]:
    close_conn = False
    if conn is None:
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

async def delete_project(project_id: str, conn=None) -> None:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM projects WHERE id = $1', project_id)
    finally:
        if close_conn:
            await conn.close()
