# session_service.py
# ADDED: Service for managing clarification sessions

import json
from typing import Optional, Dict, Any, List
import db

class SessionService:
    """Сервис для работы с сессиями уточнения."""

    async def create_clarification_session(
        self,
        project_id: str,
        target_artifact_type: str
    ) -> str:
        """Создаёт новую сессию уточнения, возвращает её ID."""
        return await db.create_clarification_session(project_id, target_artifact_type)

    async def get_clarification_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает сессию по ID."""
        return await db.get_clarification_session(session_id)

    async def update_clarification_session(self, session_id: str, **kwargs) -> None:
        """Обновляет поля сессии."""
        await db.update_clarification_session(session_id, **kwargs)

    async def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """Добавляет сообщение в историю сессии."""
        await db.add_message_to_session(session_id, role, content)

    async def list_active_sessions_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """Возвращает все активные сессии для проекта."""
        return await db.list_active_sessions_for_project(project_id)
