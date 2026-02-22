# session_service.py
# ADDED: Service for clarification sessions (to be populated later)

class SessionService:
    def __init__(self, db):
        self.db = db

    async def create_clarification_session(self, project_id, target_artifact_type):
        """Placeholder – will be implemented in later steps."""
        pass

    async def get_clarification_session(self, session_id):
        """Placeholder – will be implemented in later steps."""
        pass

    async def update_clarification_session(self, session_id, **kwargs):
        """Placeholder – will be implemented in later steps."""
        pass

    async def add_message_to_session(self, session_id, role, content):
        """Placeholder – will be implemented in later steps."""
        pass

    async def list_active_sessions_for_project(self, project_id):
        """Placeholder – will be implemented in later steps."""
        pass
