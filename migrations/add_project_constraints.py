#!/usr/bin/env python3
"""
Миграция: добавляет колонку owner_id и уникальное ограничение (name, owner_id) в таблицу projects.
Запускать после add_projects_name_unique.sql.
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
        # Проверяем, есть ли уже колонка owner_id (чтобы не выполнять дважды)
        owner_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'projects' AND column_name = 'owner_id'
            )
        """)
        if owner_exists:
            print("Column 'owner_id' already exists. Skipping migration.")
            return

        print("Adding owner_id column...")
        await conn.execute("""
            ALTER TABLE projects
            ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'default-owner'
        """)

        # Обновляем существующие строки (на всякий случай)
        await conn.execute("UPDATE projects SET owner_id = 'default-owner' WHERE owner_id IS NULL")

        print("Creating unique constraint (name, owner_id)...")
        await conn.execute("""
            ALTER TABLE projects
            ADD CONSTRAINT projects_name_owner_unique UNIQUE (name, owner_id)
        """)

        # Удаляем старое ограничение на одно имя (если оно есть)
        await conn.execute("""
            ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_name_unique
        """)

        print("✅ Migration completed: added owner_id and composite unique constraint.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
