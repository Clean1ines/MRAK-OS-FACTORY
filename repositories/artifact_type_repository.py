# ADDED: Artifact type repository
import json
from typing import Optional, Dict, Any, List
from .base import get_connection

async def get_artifact_types(conn=None) -> List[Dict[str, Any]]:
    """Возвращает все типы артефактов."""
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('SELECT * FROM artifact_types ORDER BY type')
        types = []
        for row in rows:
            t = dict(row)
            t['schema'] = json.loads(t['schema']) if isinstance(t['schema'], str) else t['schema']
            types.append(t)
        return types
    finally:
        if close_conn:
            await conn.close()

async def get_artifact_type(artifact_type: str, conn=None) -> Optional[Dict[str, Any]]:
    """Возвращает метаданные для конкретного типа."""
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM artifact_types WHERE type = $1', artifact_type)
        if row:
            t = dict(row)
            t['schema'] = json.loads(t['schema']) if isinstance(t['schema'], str) else t['schema']
            return t
        return None
    finally:
        if close_conn:
            await conn.close()

async def create_artifact_type(
    type: str,
    schema: Dict[str, Any],
    allowed_parents: List[str] = [],
    requires_clarification: bool = False,
    icon: Optional[str] = None,
    conn=None
) -> str:
    """Создаёт новый тип артефакта (для администрирования)."""
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('''
            INSERT INTO artifact_types (type, schema, allowed_parents, requires_clarification, icon)
            VALUES ($1, $2, $3, $4, $5)
        ''', type, json.dumps(schema), allowed_parents, requires_clarification, icon)
        return type
    finally:
        if close_conn:
            await conn.close()

async def update_artifact_type(type: str, **kwargs) -> None:
    """Обновляет метаданные типа артефакта."""
    conn = kwargs.pop('conn', None)
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        set_clauses = []
        values = []
        idx = 1
        for key, value in kwargs.items():
            if key in ('schema', 'allowed_parents', 'requires_clarification', 'icon'):
                set_clauses.append(f"{key} = ${idx}")
                if key == 'schema':
                    values.append(json.dumps(value))
                elif key == 'allowed_parents':
                    values.append(value)
                else:
                    values.append(value)
                idx += 1
        if not set_clauses:
            return
        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE artifact_types SET {', '.join(set_clauses)} WHERE type = ${idx}"
        values.append(type)
        await conn.execute(query, *values)
    finally:
        if close_conn:
            await conn.close()

async def delete_artifact_type(type: str, conn=None) -> None:
    """Удаляет тип артефакта."""
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM artifact_types WHERE type = $1', type)
    finally:
        if close_conn:
            await conn.close()
