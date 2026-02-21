import os
import json
import asyncpg
from typing import Optional, Dict, Any, List
import uuid
import datetime  # ADDED: for timestamps in clarification sessions

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mrak_user:mrak_pass@localhost:5432/mrak_db")

async def get_connection():
    return await asyncpg.connect(DATABASE_URL)

# ==================== ПРОЕКТЫ ====================

async def get_projects() -> List[Dict[str, Any]]:
    conn = await get_connection()
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
        await conn.close()

async def create_project(name: str, description: str = "") -> str:
    conn = await get_connection()
    try:
        project_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO projects (id, name, description)
            VALUES ($1, $2, $3)
        ''', project_id, name, description)
        return project_id
    finally:
        await conn.close()

async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    conn = await get_connection()
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
        await conn.close()

async def delete_project(project_id: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute('DELETE FROM projects WHERE id = $1', project_id)
    finally:
        await conn.close()

# ==================== АРТЕФАКТЫ ====================

async def get_artifacts(project_id: str, artifact_type: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = await get_connection()
    try:
        query = 'SELECT id, type, parent_id, content, created_at, updated_at, version, status, content_hash FROM artifacts WHERE project_id = $1'
        params = [project_id]
        if artifact_type:
            query += ' AND type = $2'
            params.append(artifact_type)
        query += ' ORDER BY created_at DESC'
        rows = await conn.fetch(query, *params)
        artifacts = []
        for row in rows:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            content = art['content']
            if isinstance(content, dict):
                art['summary'] = content.get('text', '')[:100] if 'text' in content else json.dumps(content)[:100]
            else:
                art['summary'] = str(content)[:100]
            artifacts.append(art)
        return artifacts
    finally:
        await conn.close()

async def get_last_artifact(project_id: str) -> Optional[Dict[str, Any]]:
    conn = await get_connection()
    try:
        row = await conn.fetchrow('''
            SELECT * FROM artifacts
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        ''', project_id)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        await conn.close()

async def get_last_validated_artifact(project_id: str) -> Optional[Dict[str, Any]]:
    conn = await get_connection()
    try:
        row = await conn.fetchrow('''
            SELECT * FROM artifacts
            WHERE project_id = $1 AND status = 'VALIDATED'
            ORDER BY created_at DESC
            LIMIT 1
        ''', project_id)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        await conn.close()

async def get_last_package(parent_id: str, artifact_type: str) -> Optional[Dict[str, Any]]:
    conn = await get_connection()
    try:
        row = await conn.fetchrow('''
            SELECT * FROM artifacts 
            WHERE parent_id = $1 AND type = $2
            ORDER BY version DESC
            LIMIT 1
        ''', parent_id, artifact_type)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        await conn.close()

async def get_last_version_by_parent_and_type(parent_id: str, artifact_type: str) -> Optional[Dict[str, Any]]:
    return await get_last_package(parent_id, artifact_type)

async def save_artifact(
    artifact_type: str,
    content: Dict[str, Any],
    owner: str = "system",
    version: str = "1.0",
    status: str = "DRAFT",
    content_hash: Optional[str] = None,
    project_id: Optional[str] = None,
    parent_id: Optional[str] = None
) -> str:
    conn = await get_connection()
    try:
        artifact_id = str(uuid.uuid4())
        insert_fields = ['id', 'type', 'version', 'status', 'owner', 'content']
        insert_values = [artifact_id, artifact_type, version, status, owner, json.dumps(content)]
        placeholders = ['$1', '$2', '$3', '$4', '$5', '$6']
        idx = 6

        if project_id:
            insert_fields.append('project_id')
            insert_values.append(project_id)
            idx += 1
            placeholders.append(f'${idx}')
        if parent_id:
            insert_fields.append('parent_id')
            insert_values.append(parent_id)
            idx += 1
            placeholders.append(f'${idx}')
        if content_hash:
            insert_fields.append('content_hash')
            insert_values.append(content_hash)
            idx += 1
            placeholders.append(f'${idx}')

        query = f'''
            INSERT INTO artifacts ({', '.join(insert_fields)})
            VALUES ({', '.join(placeholders)})
        '''
        await conn.execute(query, *insert_values)
        return artifact_id
    finally:
        await conn.close()

async def update_artifact_status(artifact_id: str, status: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute('UPDATE artifacts SET status = $1, updated_at = NOW() WHERE id = $2', status, artifact_id)
    finally:
        await conn.close()

async def delete_artifact(artifact_id: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute('DELETE FROM artifacts WHERE id = $1', artifact_id)
    finally:
        await conn.close()

async def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    conn = await get_connection()
    try:
        row = await conn.fetchrow('SELECT * FROM artifacts WHERE id = $1', artifact_id)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        await conn.close()

# ==================== СЕССИИ УТОЧНЕНИЯ ==================== #
# ADDED: New functions for clarification sessions

async def create_clarification_session(
    project_id: str,
    target_artifact_type: str
) -> str:
    """Создаёт новую сессию уточнения, возвращает её ID."""
    conn = await get_connection()
    try:
        session_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO clarification_sessions (id, project_id, target_artifact_type, history, status)
            VALUES ($1, $2, $3, $4, $5)
        ''', session_id, project_id, target_artifact_type, json.dumps([]), 'active')
        return session_id
    finally:
        await conn.close()

async def get_clarification_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Возвращает сессию по ID."""
    conn = await get_connection()
    try:
        row = await conn.fetchrow('SELECT * FROM clarification_sessions WHERE id = $1', session_id)
        if row:
            sess = dict(row)
            sess['id'] = str(sess['id'])
            sess['project_id'] = str(sess['project_id']) if sess['project_id'] else None
            sess['final_artifact_id'] = str(sess['final_artifact_id']) if sess['final_artifact_id'] else None
            # history хранится как JSONB, парсим
            if isinstance(sess['history'], str):
                sess['history'] = json.loads(sess['history'])
            sess['created_at'] = sess['created_at'].isoformat() if sess['created_at'] else None
            sess['updated_at'] = sess['updated_at'].isoformat() if sess['updated_at'] else None
            return sess
        return None
    finally:
        await conn.close()

async def update_clarification_session(
    session_id: str,
    **kwargs
) -> None:
    """Обновляет поля сессии (кроме id и project_id). Допустимые ключи: history, status, context_summary, final_artifact_id."""
    if not kwargs:
        return
    conn = await get_connection()
    try:
        set_clauses = []
        values = []
        idx = 1
        for key, value in kwargs.items():
            if key in ('history', 'context_summary', 'status', 'final_artifact_id'):
                set_clauses.append(f"{key} = ${idx}")
                # Если history, нужно сериализовать в JSON
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
        await conn.close()

async def add_message_to_session(
    session_id: str,
    role: str,  # 'user' или 'assistant'
    content: str
) -> None:
    """Добавляет сообщение в историю сессии."""
    session = await get_clarification_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
    history = session.get('history', [])
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now().isoformat()  # NOW datetime is defined
    })
    await update_clarification_session(session_id, history=history)

async def list_active_sessions_for_project(project_id: str) -> List[Dict[str, Any]]:
    """Возвращает все активные сессии для проекта."""
    conn = await get_connection()
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
        await conn.close()