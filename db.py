import os
import json
import asyncpg
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mrak_user:mrak_pass@localhost:5432/mrak_db")

async def init_db():
    """Создаёт таблицы, если их нет."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Включаем расширение pgvector
        await conn.execute('CREATE EXTENSION IF NOT EXISTS vector;')
        # Таблица артефактов
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS artifacts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                type VARCHAR(50) NOT NULL,
                version VARCHAR(20) NOT NULL DEFAULT '1.0',
                status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
                owner VARCHAR(100),
                content JSONB NOT NULL,
                embedding vector(384),  -- размерность для all-MiniLM-L6-v2, можно изменить
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        ''')
        # Таблица связей (опционально, для будущего)
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
    finally:
        await conn.close()

async def save_artifact(artifact_type: str, content: Dict[str, Any], owner: str = "system", version: str = "1.0", status: str = "DRAFT") -> str:
    """Сохраняет артефакт в БД и возвращает его ID."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        artifact_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO artifacts (id, type, version, status, owner, content)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', artifact_id, artifact_type, version, status, owner, json.dumps(content))
        return artifact_id
    finally:
        await conn.close()

async def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    """Получает артефакт по ID."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('SELECT * FROM artifacts WHERE id = $1', artifact_id)
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()

# Для векторов пока не реализуем, отложим до фазы 5.3
