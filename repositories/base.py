# CHANGED: transaction() now returns Transaction instance directly (not a coroutine)
import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mrak_user:mrak_pass@localhost:5432/mrak_db")

async def get_connection():
    """Return a new database connection."""
    return await asyncpg.connect(DATABASE_URL)

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

def transaction():
    """Return a Transaction context manager (synchronous factory)."""
    return Transaction()
