#!/usr/bin/env python3
"""
Миграция для добавления таблицы clarification_sessions.
Запускать отдельно после проверки бэкапа.
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("DATABASE_URL not set")
        return

    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Проверяем, существует ли уже таблица
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'clarification_sessions'
            )
        """)
        if exists:
            print("Table 'clarification_sessions' already exists. Skipping creation.")
            return

        print("Creating table clarification_sessions...")
        await conn.execute("""
            CREATE TABLE clarification_sessions (
                id UUID PRIMARY KEY,
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                target_artifact_type TEXT NOT NULL,
                history JSONB NOT NULL DEFAULT '[]'::jsonb,
                status TEXT NOT NULL DEFAULT 'active',
                context_summary TEXT,
                final_artifact_id UUID REFERENCES artifacts(id) ON DELETE SET NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        print("Creating indexes...")
        await conn.execute("CREATE INDEX idx_clarification_sessions_project ON clarification_sessions(project_id)")
        await conn.execute("CREATE INDEX idx_clarification_sessions_status ON clarification_sessions(status)")
        print("Table created successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())