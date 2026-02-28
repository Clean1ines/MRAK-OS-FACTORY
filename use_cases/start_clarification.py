import json
import logging
from schemas import StartClarificationRequest, ClarificationSessionResponse
from session_service import SessionService
from prompt_service import PromptService
from repositories.base import transaction
import db
from services import TYPE_TO_MODE

logger = logging.getLogger(__name__)

class StartClarificationUseCase:
    def __init__(self, prompt_service: PromptService, session_service: SessionService):
        self.prompt_service = prompt_service
        self.session_service = session_service

    async def execute(self, req: StartClarificationRequest) -> ClarificationSessionResponse:
        async with transaction() as tx:
            project = await db.get_project(req.project_id, tx=tx)
            if not project:
                raise ValueError("Project not found")

        mode = TYPE_TO_MODE.get(req.target_artifact_type)
        if not mode:
            raise ValueError(f"No prompt mode found for artifact type {req.target_artifact_type}")

        sys_prompt = await self.prompt_service.get_system_prompt(mode)
        if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
            raise RuntimeError(sys_prompt)

        session_id = await self.session_service.create_clarification_session(
            req.project_id, req.target_artifact_type
        )

        model = req.model or "llama-3.3-70b-versatile"
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": "Начни уточняющий диалог. Задай первый вопрос, чтобы понять идею пользователя."}
        ]
        try:
            assistant_message = await self.prompt_service.get_chat_completion(messages, model)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError("Failed to generate first message") from e

        await self.session_service.add_message_to_session(session_id, "assistant", assistant_message)

        session = await self.session_service.get_clarification_session(session_id)
        if session:
            state = await self.prompt_service.synthesize_conversation_state(session['history'], model)
            await self.session_service.update_clarification_session(
                session_id, context_summary=json.dumps(state)
            )

        session = await self.session_service.get_clarification_session(session_id)
        return ClarificationSessionResponse(
            id=session['id'],
            project_id=session['project_id'],
            target_artifact_type=session['target_artifact_type'],
            history=session['history'],
            status=session['status'],
            context_summary=json.loads(session['context_summary']) if session.get('context_summary') else None,
            final_artifact_id=session.get('final_artifact_id'),
            created_at=session['created_at'],
            updated_at=session['updated_at']
        )
