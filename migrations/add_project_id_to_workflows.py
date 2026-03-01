#!/usr/bin/env python3
"""
Миграция: добавляет колонку project_id в таблицу workflows,
внешний ключ на projects(id) с каскадным удалением.
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
        # Проверяем, существует ли уже колонка
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'workflows' AND column_name = 'project_id'
            )
        """)
        if column_exists:
            print("Column 'project_id' already exists. Skipping.")
            return

        # Добавляем колонку, сначала как NULL
        print("Adding project_id column...")
        await conn.execute("""
            ALTER TABLE workflows ADD COLUMN project_id UUID
        """)

        # Устанавливаем значение по умолчанию для существующих записей – берём первый проект
        project_exists = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM projects LIMIT 1)")
        if project_exists:
            first_project = await conn.fetchrow("SELECT id FROM projects ORDER BY created_at LIMIT 1")
            if first_project:
                default_project_id = first_project['id']
                await conn.execute("UPDATE workflows SET project_id = $1 WHERE project_id IS NULL", default_project_id)
                print(f"Set project_id = {default_project_id} for existing workflows.")
        else:
            print("No projects exist. Workflows with NULL project_id will remain NULL until assigned.")

        # Теперь делаем колонку NOT NULL и добавляем внешний ключ
        print("Setting project_id NOT NULL and adding foreign key...")
        await conn.execute("""
            ALTER TABLE workflows ALTER COLUMN project_id SET NOT NULL
        """)
        await conn.execute("""
            ALTER TABLE workflows
            ADD CONSTRAINT workflows_project_id_fkey
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        """)

        print("✅ Migration completed: added project_id column and foreign key.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
