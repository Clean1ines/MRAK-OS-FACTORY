import json
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

async def get_artifacts(project_id: str, artifact_type: Optional[str] = None, logical_key: Optional[str] = None, tx=None) -> List[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        query = 'SELECT id, type, parent_id, content, created_at, updated_at, version, status, content_hash, logical_key, superseded_by, node_execution_id FROM artifacts WHERE project_id = $1'
        params = [project_id]
        idx = 2
        if artifact_type:
            query += f' AND type = ${idx}'
            params.append(artifact_type)
            idx += 1
        if logical_key:
            query += f' AND logical_key = ${idx}'
            params.append(logical_key)
            idx += 1
        query += ' ORDER BY created_at DESC'
        rows = await conn.fetch(query, *params)
        artifacts = []
        for row in rows:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
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

async def get_last_artifact(project_id: str, tx=None) -> Optional[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        if close_conn:
            await conn.close()

async def get_last_validated_artifact(project_id: str, tx=None) -> Optional[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        if close_conn:
            await conn.close()

async def get_last_package(parent_id: str, artifact_type: str, tx=None) -> Optional[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        if close_conn:
            await conn.close()

async def get_last_version_by_parent_and_type(parent_id: str, artifact_type: str, tx=None) -> Optional[Dict[str, Any]]:
    return await get_last_package(parent_id, artifact_type, tx=tx)

async def get_last_version(project_id: str, logical_key: str, tx=None) -> Optional[Dict[str, Any]]:
    """Возвращает последнюю версию артефакта с данным logical_key в проекте."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow("""
            SELECT * FROM artifacts
            WHERE project_id = $1 AND logical_key = $2
            ORDER BY version DESC
            LIMIT 1
        """, project_id, logical_key)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        if close_conn:
            await conn.close()

async def get_active_artifact_by_logical_key(project_id: str, logical_key: str, tx=None) -> Optional[Dict[str, Any]]:
    """Возвращает активную (ACTIVE) версию артефакта с данным logical_key."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow("""
            SELECT * FROM artifacts
            WHERE project_id = $1 AND logical_key = $2 AND status = 'ACTIVE'
            LIMIT 1
        """, project_id, logical_key)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        if close_conn:
            await conn.close()

async def supersede_artifact(old_id: str, new_id: str, tx=None) -> None:
    """Переводит артефакт в статус SUPERSEDED и связывает с новым."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute("""
            UPDATE artifacts
            SET status = 'SUPERSEDED', superseded_by = $1, updated_at = NOW()
            WHERE id = $2
        """, new_id, old_id)
    finally:
        if close_conn:
            await conn.close()

async def save_artifact(
    artifact_type: str,
    content: Dict[str, Any],
    owner: str = "system",
    version: int = 1,
    status: str = 'CREATED',
    content_hash: Optional[str] = None,
    project_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    logical_key: Optional[str] = None,
    tx=None
) -> str:
    """Сохраняет новый артефакт. Версия должна быть целым числом."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
        if logical_key:
            insert_fields.append('logical_key')
            insert_values.append(logical_key)
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

async def update_artifact_status(artifact_id: str, status: str, tx=None) -> None:
    """Обновляет статус артефакта."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('UPDATE artifacts SET status = $1, updated_at = NOW() WHERE id = $2', status, artifact_id)
    finally:
        if close_conn:
            await conn.close()

async def delete_artifact(artifact_id: str, tx=None) -> None:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM artifacts WHERE id = $1', artifact_id)
    finally:
        if close_conn:
            await conn.close()

async def get_artifact(artifact_id: str, tx=None) -> Optional[Dict[str, Any]]:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM artifacts WHERE id = $1', artifact_id)
        if row:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            if isinstance(art['content'], str):
                art['content'] = json.loads(art['content'])
            return art
        return None
    finally:
        if close_conn:
            await conn.close()

async def get_artifacts_by_ids(artifact_ids: List[str], tx=None) -> List[Dict[str, Any]]:
    if not artifact_ids:
        return []
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('SELECT * FROM artifacts WHERE id = ANY($1::uuid[])', artifact_ids)
        artifacts = []
        for row in rows:
            art = dict(row)
            art['id'] = str(art['id'])
            art['parent_id'] = str(art['parent_id']) if art['parent_id'] else None
            art['superseded_by'] = str(art['superseded_by']) if art['superseded_by'] else None
            art['node_execution_id'] = str(art['node_execution_id']) if art['node_execution_id'] else None
            art['created_at'] = art['created_at'].isoformat() if art['created_at'] else None
            art['updated_at'] = art['updated_at'].isoformat() if art['updated_at'] else None
            artifacts.append(art)
        return artifacts
    finally:
        if close_conn:
            await conn.close()

async def update_artifact_node_execution(artifact_id: str, node_execution_id: str, tx=None) -> None:
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute(
            "UPDATE artifacts SET node_execution_id = $1 WHERE id = $2",
            node_execution_id, artifact_id
        )
    finally:
        if close_conn:
            await conn.close()
