import asyncpg
from typing import List, Optional
from .base import transaction, get_connection

async def find_relevant_knowledge(
    query_embedding: List[float], 
    limit: int = 3,
    category: Optional[str] = None
) -> List[str]:
    """
    Возвращает тексты наиболее релевантных записей из базы знаний.
    """
    # Преобразуем список в строку, понятную PostgreSQL для типа vector
    embedding_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
    
    conn = await get_connection()
    try:
        if category:
            rows = await conn.fetch("""
                SELECT content, 1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                WHERE category = $3
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, embedding_str, limit, category)
        else:
            rows = await conn.fetch("""
                SELECT content, 1 - (embedding <=> $1::vector) as similarity
                FROM knowledge_base
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, embedding_str, limit)
        return [row['content'] for row in rows]
    finally:
        await conn.close()

async def add_knowledge(content: str, embedding: List[float], category: Optional[str] = None):
    """Добавляет запись в базу знаний (для администрирования)."""
    embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
    async with transaction() as tx:
        await tx.execute("""
            INSERT INTO knowledge_base (content, embedding, category)
            VALUES ($1, $2::vector, $3)
        """, content, embedding_str, category)