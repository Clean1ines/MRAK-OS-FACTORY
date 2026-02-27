#!/usr/bin/env python3
"""
Миграция: очистка дубликатов проектов и добавление уникального ограничения на name.
Выполняется до применения ограничения, чтобы избежать ошибки из-за существующих дубликатов.
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
        # Проверяем, есть ли уже ограничение (если есть, пропускаем)
        has_constraint = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'projects_name_unique'
            )
        """)
        if has_constraint:
            print("✅ Unique constraint 'projects_name_unique' already exists. Skipping.")
            return

        # Находим дублирующиеся имена
        duplicates = await conn.fetch("""
            SELECT name, COUNT(*) as cnt
            FROM projects
            GROUP BY name
            HAVING COUNT(*) > 1
        """)
        if not duplicates:
            print("No duplicate project names found. Proceeding to add constraint.")
        else:
            print(f"Found {len(duplicates)} duplicate names. Cleaning up...")
            for d in duplicates:
                print(f"  - {d['name']}: {d['cnt']} copies")

            # 1. Создаём временную таблицу с проектами, которые оставляем (самый старый по created_at)
            await conn.execute("""
                CREATE TEMP TABLE keep_projects AS
                SELECT DISTINCT ON (name) id, name
                FROM projects
                ORDER BY name, created_at ASC
            """)

            # 2. Обновляем ссылки в artifacts
            result = await conn.execute("""
                UPDATE artifacts a
                SET project_id = k.id
                FROM projects p
                JOIN keep_projects k ON p.name = k.name
                WHERE a.project_id = p.id
                  AND p.id != k.id
            """)
            print(f"  Updated {result.split()[-1]} artifacts")

            # 3. Обновляем ссылки в clarification_sessions
            result = await conn.execute("""
                UPDATE clarification_sessions cs
                SET project_id = k.id
                FROM projects p
                JOIN keep_projects k ON p.name = k.name
                WHERE cs.project_id = p.id
                  AND p.id != k.id
            """)
            print(f"  Updated {result.split()[-1]} clarification sessions")

            # 4. Удаляем дубликаты проектов
            result = await conn.execute("""
                DELETE FROM projects
                WHERE id NOT IN (SELECT id FROM keep_projects)
            """)
            print(f"  Deleted {result.split()[-1]} duplicate projects")

            # 5. Удаляем временную таблицу
            await conn.execute("DROP TABLE keep_projects")

            print("✅ Duplicate cleanup completed.")

        # 6. Добавляем уникальное ограничение
        await conn.execute("ALTER TABLE projects ADD CONSTRAINT projects_name_unique UNIQUE (name)")
        print("✅ Unique constraint 'projects_name_unique' added successfully.")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
