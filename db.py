import os
import json
import asyncpg
from typing import Optional, Dict, Any, List
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mrak_user:mrak_pass@localhost:5432/mrak_db")

async def init_db():
    """Создаёт таблицы, если их нет, без удаления старых данных."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('CREATE EXTENSION IF NOT EXISTS vector;')
        
        # Таблица проектов
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')
        
        # Таблица артефактов с parent_id
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS artifacts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                parent_id UUID REFERENCES artifacts(id) ON DELETE SET NULL,
                type VARCHAR(50) NOT NULL,
                version VARCHAR(20) NOT NULL DEFAULT '1.0',
                status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                owner VARCHAR(100),
                content JSONB NOT NULL,
                content_hash VARCHAR(64),
                embedding vector(384),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')
        
        # Таблица связей (можно оставить, но parent_id покрывает простые иерархии)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS links (
                from_id UUID REFERENCES artifacts(id) ON DELETE CASCADE,
                to_id UUID REFERENCES artifacts(id) ON DELETE CASCADE,
                link_type VARCHAR(50) NOT NULL,
                description TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (from_id, to_id, link_type)
            );
        ''')
        
        # Индекс для поиска по пути
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_artifacts_file_path ON artifacts ((content->>'file_path')) WHERE type = 'CodeFile';
        ''')
        
        print("DEBUG: Tables initialized (projects, artifacts with parent_id)")
    finally:
        await conn.close()

async def get_projects() -> List[Dict[str, Any]]:
    """Возвращает список всех проектов с преобразованием UUID и datetime в строки."""
    conn = await asyncpg.connect(DATABASE_URL)
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
    conn = await asyncpg.connect(DATABASE_URL)
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
    conn = await asyncpg.connect(DATABASE_URL)
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

async def get_artifacts(project_id: str, artifact_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Возвращает список артефактов проекта с преобразованием дат."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        query = 'SELECT id, type, parent_id, content, created_at, updated_at FROM artifacts WHERE project_id = $1'
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
            # Для отображения в списке можно добавить краткое содержание
            content = art['content']
            if isinstance(content, dict):
                art['summary'] = content.get('text', '')[:100] if 'text' in content else str(content)[:100]
            else:
                art['summary'] = str(content)[:100]
            artifacts.append(art)
        return artifacts
    finally:
        await conn.close()

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
    """Сохраняет артефакт в БД и возвращает его ID."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        artifact_id = str(uuid.uuid4())
        # Базовые поля
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

async def find_artifact_by_path(file_path: str, artifact_type: str = "CodeFile", project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Ищет артефакт по типу и пути (хранится в content->>'file_path'). Если указан project_id, учитывает его."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        query = '''
            SELECT * FROM artifacts 
            WHERE type = $1 AND content->>'file_path' = $2
        '''
        params = [artifact_type, file_path]
        if project_id:
            query += ' AND project_id = $3'
            params.append(project_id)
        query += ' ORDER BY version DESC LIMIT 1'
        row = await conn.fetchrow(query, *params)
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()

async def update_artifact(artifact_id: str, new_content: Dict[str, Any], new_version: str, new_hash: str) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            UPDATE artifacts
            SET content = $1, version = $2, content_hash = $3, updated_at = NOW()
            WHERE id = $4
        ''', json.dumps(new_content), new_version, new_hash, artifact_id)
    finally:
        await conn.close()

async def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('SELECT * FROM artifacts WHERE id = $1', artifact_id)
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()

async def get_last_package(parent_id: str, artifact_type: str) -> Optional[Dict[str, Any]]:
    """Возвращает последний артефакт указанного типа с заданным parent_id (по убыванию version)."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('''
            SELECT * FROM artifacts 
            WHERE parent_id = $1 AND type = $2
            ORDER BY version DESC
            LIMIT 1
        ''', parent_id, artifact_type)
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()
