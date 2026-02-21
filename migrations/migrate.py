import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()  # загружает переменные из .env

async def migrate():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("DATABASE_URL not set in environment")
        return
    print("Migrating DB:", DATABASE_URL)
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("ALTER TABLE artifacts ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_file_path ON artifacts ((content->>'file_path')) WHERE type = 'CodeFile';")
        print("Migration completed.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
