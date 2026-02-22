# ADDED: Artifact repository
import json
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

async def get_artifacts(project_id: str, artifact_type: Optional[str] = None, conn=None) -> List[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
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
        if close_conn:
            await conn.close()

async def get_last_artifact(project_id: str, conn=None) -> Optional[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
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
        if close_conn:
            await conn.close()

async def get_last_validated_artifact(project_id: str, conn=None) -> Optional[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
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
        if close_conn:
            await conn.close()

async def get_last_package(parent_id: str, artifact_type: str, conn=None) -> Optional[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
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
        if close_conn:
            await conn.close()

async def get_last_version_by_parent_and_type(parent_id: str, artifact_type: str, conn=None) -> Optional[Dict[str, Any]]:
    return await get_last_package(parent_id, artifact_type, conn=conn)

async def save_artifact(
    artifact_type: str,
    content: Dict[str, Any],
    owner: str = "system",
    version: str = "1.0",
    status: str = "DRAFT",
    content_hash: Optional[str] = None,
    project_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    conn=None
) -> str:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
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
        if close_conn:
            await conn.close()

async def update_artifact_status(artifact_id: str, status: str, conn=None) -> None:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('UPDATE artifacts SET status = $1, updated_at = NOW() WHERE id = $2', status, artifact_id)
    finally:
        if close_conn:
            await conn.close()

async def delete_artifact(artifact_id: str, conn=None) -> None:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM artifacts WHERE id = $1', artifact_id)
    finally:
        if close_conn:
            await conn.close()

async def get_artifact(artifact_id: str, conn=None) -> Optional[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
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
        if close_conn:
            await conn.close()
