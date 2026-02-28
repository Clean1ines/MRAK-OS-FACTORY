# CHANGED: Added SET search_path after connection
import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mrak_user:mrak_pass@localhost:5432/mrak_db")

print(f"🔍 BACKEND CONNECTING TO: {DATABASE_URL}") 

async def get_connection():
    """Return a new database connection with search_path set to public."""
    conn = await asyncpg.connect(DATABASE_URL)
    # Принудительно устанавливаем схему
    await conn.execute("SET search_path TO public")
    return conn

class Transaction:
    """Async context manager for database transactions."""
    def __init__(self):
        self.conn = None

    async def __aenter__(self):
        self.conn = await get_connection()
        await self.conn.execute("BEGIN")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type is None:
                    await self.conn.execute("COMMIT")
                else:
                    await self.conn.execute("ROLLBACK")
            finally:
                await self.conn.close()
    
    # ADDED: Делегируем методы подключения
    async def fetch(self, query, *args):
        return await self.conn.fetch(query, *args)
    
    async def fetchrow(self, query, *args):
        return await self.conn.fetchrow(query, *args)
    
    async def fetchval(self, query, *args):
        return await self.conn.fetchval(query, *args)
    
    async def execute(self, query, *args):
        return await self.conn.execute(query, *args)

def transaction():
    """Return a Transaction context manager."""
    return Transaction()  # НЕ async def!