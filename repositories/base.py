# ADDED: Base database utilities and transaction context manager (stub)
import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://mrak_user:mrak_pass@localhost:5432/mrak_db")

async def get_connection():
    """Return a new database connection."""
    return await asyncpg.connect(DATABASE_URL)

# Stub transaction context manager (to be implemented in TASK‑101)
class Transaction:
    """Placeholder for transaction context manager."""
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def transaction():
    """Return a Transaction context manager (stub)."""
    conn = await get_connection()
    return Transaction(conn)
