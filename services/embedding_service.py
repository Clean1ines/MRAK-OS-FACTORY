import asyncio
from typing import List
from fastembed import TextEmbedding
import logging

logger = logging.getLogger(__name__)

# Ленивая загрузка модели (один раз)
_model = None

def _get_model():
    global _model
    if _model is None:
        # Используем небольшую мультиязычную модель (можно заменить на другую)
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")  # для английского
        # Если нужна поддержка русского, используйте "intfloat/multilingual-e5-small"
    return _model

async def embed_text(text: str) -> List[float]:
    """
    Асинхронно получает эмбеддинг текста.
    FastEmbed работает синхронно, поэтому запускаем в отдельном потоке.
    """
    loop = asyncio.get_event_loop()
    model = _get_model()
    # model.embed возвращает генератор, берём первый элемент
    embedding = await loop.run_in_executor(
        None, 
        lambda: list(model.embed([text]))[0]
    )
    return embedding.tolist()