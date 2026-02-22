# CHANGED: Updated imports to use repositories
import json
from typing import Optional, Dict, Any, List
# CHANGED: import from session_repository
from repositories.session_repository import (
    create_clarification_session as db_create,
    get_clarification_session as db_get,
    update_clarification_session as db_update,
    add_message_to_session as db_add_message,
    list_active_sessions_for_project as db_list_active
)

class SessionService:
    """Сервис для работы с сессиями уточнения."""

    async def create_clarification_session(
        self,
        project_id: str,
        target_artifact_type: str
    ) -> str:
        """Создаёт новую сессию уточнения, возвращает её ID."""
        return await db_create(project_id, target_artifact_type)

    async def get_clarification_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает сессию по ID."""
        return await db_get(session_id)

    async def update_clarification_session(self, session_id: str, **kwargs) -> None:
        """Обновляет поля сессии."""
        await db_update(session_id, **kwargs)

    async def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """Добавляет сообщение в историю сессии."""
        await db_add_message(session_id, role, content)

    async def list_active_sessions_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Возвращает все активные сессии для проекта."""
        return await db_list_active(project_id)
