#!/usr/bin/env python3
"""
Универсальный скрипт для применения всех миграций в правильном порядке.
Поддерживает SQL-файлы (с несколькими командами) и Python-скрипты.
Ведёт таблицу schema_migrations для отслеживания применённых миграций.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv()

MIGRATIONS_DIR = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not set in environment")
    sys.exit(1)

# migrations/run_all.py (фрагмент с порядком)
MIGRATION_ORDER = [
    "add_workflow_tables.sql",
    "fix_artifacts_schema.sql",
    "add_artifact_types.sql",
    "add_clarification_sessions.py",
    "cleanup_duplicate_projects.py",   # ← добавить здесь
    "add_projects_name_unique.sql",
    "add_project_constraints.py",    # теперь можно применять после очистки
    "add_default_workflow.sql",
]

async def ensure_migrations_table(conn):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


async def is_migration_applied(conn, filename):
    return await conn.fetchval(
        "SELECT 1 FROM schema_migrations WHERE filename = $1", filename
    ) is not None


async def mark_migration_applied(conn, filename):
    await conn.execute(
        "INSERT INTO schema_migrations (filename) VALUES ($1)", filename
    )


async def run_sql_file(conn, filename):
    """Выполняет SQL-команды из файла, игнорируя комментарии и пустые строки."""
    filepath = MIGRATIONS_DIR / filename
    print(f"📄 Applying SQL migration: {filename}")
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    # Разделяем на команды по точке с запятой
    raw_commands = sql.split(';')
    for raw_cmd in raw_commands:
        cmd = raw_cmd.strip()
        # Пропускаем пустые команды и однострочные комментарии
        if not cmd or cmd.startswith('--'):
            continue
        # Удаляем встроенные комментарии (всё после -- в этой строке) – упрощённо
        # Если команда содержит -- внутри строки, это может сломать, но в наших миграциях таких нет
        if '--' in cmd:
            # Обрезаем до первого вхождения --, но только если оно не в кавычках – упрощаем
            cmd = cmd.split('--', 1)[0].strip()
        if not cmd:
            continue
        try:
            await conn.execute(cmd)
        except Exception as e:
            print(f"❌ Error executing command in {filename}:\n{cmd}")
            raise e
    print(f"✅ {filename} applied")


async def run_python_migration(filename):
    filepath = MIGRATIONS_DIR / filename
    print(f"🐍 Applying Python migration: {filename}")
    env = os.environ.copy()
    result = subprocess.run([sys.executable, str(filepath)], env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Python migration {filename} failed:")
        print(result.stderr)
        raise RuntimeError(f"Migration {filename} failed with code {result.returncode}")
    print(result.stdout)
    print(f"✅ {filename} applied")


async def main():
    print("🚀 Starting unified migration runner")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        await ensure_migrations_table(conn)

        for filename in MIGRATION_ORDER:
            if await is_migration_applied(conn, filename):
                print(f"⏭️  Skipping already applied migration: {filename}")
                continue

            if filename.endswith(".sql"):
                await run_sql_file(conn, filename)
            elif filename.endswith(".py"):
                await conn.close()
                await run_python_migration(filename)
                conn = await asyncpg.connect(DATABASE_URL)
                await ensure_migrations_table(conn)
            else:
                print(f"⚠️  Unknown file type: {filename}, skipping")

            await mark_migration_applied(conn, filename)

        print("🎉 All migrations applied successfully")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())