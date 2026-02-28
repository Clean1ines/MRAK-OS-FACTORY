# CHANGED: Remove conn, add optional tx; handle connection
import json
import uuid
import datetime
from typing import Optional, Dict, Any, List
from .base import get_connection
from .artifact_repository import get_artifact

async def create_clarification_session(
    project_id: str,
    target_artifact_type: str,
    tx=None
) -> str:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        session_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO clarification_sessions (id, project_id, target_artifact_type, history, status)
            VALUES ($1, $2, $3, $4, $5)
        ''', session_id, project_id, target_artifact_type, json.dumps([]), 'active')
        return session_id
    finally:
        if close_conn:
            await conn.close()

async def get_clarification_session(session_id: str, tx=None) -> Optional[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM clarification_sessions WHERE id = $1', session_id)
        if row:
            sess = dict(row)
            sess['id'] = str(sess['id'])
            sess['project_id'] = str(sess['project_id']) if sess['project_id'] else None
            sess['final_artifact_id'] = str(sess['final_artifact_id']) if sess['final_artifact_id'] else None
            if isinstance(sess['history'], str):
                sess['history'] = json.loads(sess['history'])
            sess['created_at'] = sess['created_at'].isoformat() if sess['created_at'] else None
            sess['updated_at'] = sess['updated_at'].isoformat() if sess['updated_at'] else None
            return sess
        return None
    finally:
        if close_conn:
            await conn.close()

async def update_clarification_session(
    session_id: str,
    tx=None,
    **kwargs
) -> None:
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
            if key in ('history', 'context_summary', 'status', 'final_artifact_id'):
                set_clauses.append(f"{key} = ${idx}")
                if key == 'history' and value is not None:
                    values.append(json.dumps(value))
                else:
                    values.append(value)
                idx += 1
        if not set_clauses:
            return
        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE clarification_sessions SET {', '.join(set_clauses)} WHERE id = ${idx}"
        values.append(session_id)
        await conn.execute(query, *values)
    finally:
        if close_conn:
            await conn.close()

async def add_message_to_session(
    session_id: str,
    role: str,
    content: str,
    tx=None
) -> None:
    # This function performs two operations: get and update, so it should be called within a transaction.
    # The caller is expected to pass tx if they want atomicity; if not, it creates its own connection (no transaction).
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        session = await get_clarification_session(session_id, tx=tx)  # reuse same tx if provided
        if not session:
            raise ValueError(f"Session {session_id} not found")
        history = session.get('history', [])
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        })
        await update_clarification_session(session_id, tx=tx, history=history)
    finally:
        if close_conn:
            await conn.close()

async def list_active_sessions_for_project(project_id: str, tx=None) -> List[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('''
            SELECT * FROM clarification_sessions
            WHERE project_id = $1 AND status = 'active'
            ORDER BY created_at DESC
        ''', project_id)
        sessions = []
        for row in rows:
            sess = dict(row)
            sess['id'] = str(sess['id'])
            sess['project_id'] = str(sess['project_id'])
            sess['final_artifact_id'] = str(sess['final_artifact_id']) if sess['final_artifact_id'] else None
            if isinstance(sess['history'], str):
                sess['history'] = json.loads(sess['history'])
            sess['created_at'] = sess['created_at'].isoformat() if sess['created_at'] else None
            sess['updated_at'] = sess['updated_at'].isoformat() if sess['updated_at'] else None
            sessions.append(sess)
        return sessions
    finally:
        if close_conn:
            await conn.close()
