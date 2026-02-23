# CHANGED: Remove conn, add optional tx; handle connection
import json
from typing import Optional, Dict, Any, List
from .base import get_connection

async def get_artifact_types(tx=None) -> List[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('SELECT * FROM public.artifact_types ORDER BY type')
        types = []
        for row in rows:
            t = dict(row)
            t['schema'] = json.loads(t['schema']) if isinstance(t['schema'], str) else t['schema']
            types.append(t)
        return types
    finally:
        if close_conn:
            await conn.close()

async def get_artifact_type(artifact_type: str, tx=None) -> Optional[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM public.artifact_types WHERE type = $1', artifact_type)
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
    tx=None
) -> str:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('''
            INSERT INTO public.artifact_types (type, schema, allowed_parents, requires_clarification, icon)
            VALUES ($1, $2, $3, $4, $5)
        ''', type, json.dumps(schema), allowed_parents, requires_clarification, icon)
        return type
    finally:
        if close_conn:
            await conn.close()

async def update_artifact_type(type: str, tx=None, **kwargs) -> None:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
        query = f"UPDATE public.artifact_types SET {', '.join(set_clauses)} WHERE type = ${idx}"
        values.append(type)
        await conn.execute(query, *values)
    finally:
        if close_conn:
            await conn.close()

async def delete_artifact_type(type: str, tx=None) -> None:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM public.artifact_types WHERE type = $1', type)
    finally:
        if close_conn:
            await conn.close()
