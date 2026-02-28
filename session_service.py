# CHANGED: Use transactions where multiple operations occur
import json
from typing import Optional, Dict, Any, List
from repositories.session_repository import (
    create_clarification_session as db_create,
    get_clarification_session as db_get,
    update_clarification_session as db_update,
    add_message_to_session as db_add_message,
    list_active_sessions_for_project as db_list_active
)
from repositories.base import transaction

class SessionService:
    """Сервис для работы с сессиями уточнения."""

    async def create_clarification_session(
        self,
        project_id: str,
        target_artifact_type: str
    ) -> str:
        # Single operation, transaction optional
        async with transaction() as tx:
            return await db_create(project_id, target_artifact_type, tx=tx)

    async def get_clarification_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        # Read-only, no transaction needed
        return await db_get(session_id)

    async def update_clarification_session(self, session_id: str, **kwargs) -> None:
        async with transaction() as tx:
            await db_update(session_id, tx=tx, **kwargs)

    async def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        # Multiple operations (get + update), must be atomic
        async with transaction() as tx:
            await db_add_message(session_id, role, content, tx=tx)

    async def list_active_sessions_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        # Read-only
        return await db_list_active(project_id)
