# ADDED: Add message use case
import json
import logging
from schemas import MessageRequest, ClarificationSessionResponse
from orchestrator import MrakOrchestrator
from session_service import SessionService
import db

logger = logging.getLogger(__name__)

class AddMessageUseCase:
    def __init__(self, orch: MrakOrchestrator, session_service: SessionService):
        self.orch = orch
        self.session_service = session_service

    async def execute(self, session_id: str, req: MessageRequest) -> ClarificationSessionResponse:
        session = await self.session_service.get_clarification_session(session_id)
        if not session:
            raise ValueError("Session not found")

        if session['status'] != 'active':
            raise ValueError("Session is not active")

        await self.session_service.add_message_to_session(session_id, "user", req.message)

        session = await self.session_service.get_clarification_session(session_id)
        history = session['history']

        mode = self.orch.type_to_mode.get(session['target_artifact_type'])
        if not mode:
            raise ValueError(f"No prompt mode found for artifact type {session['target_artifact_type']}")

        sys_prompt = await self.orch.get_system_prompt(mode)
        if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
            raise RuntimeError(sys_prompt)

        context_summary = session.get('context_summary')
        if context_summary:
            try:
                state = json.loads(context_summary)
                recent = history[-2:] if len(history) >= 2 else history
                recent_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])
                enhanced_system = sys_prompt + f"\n\nCurrent conversation state:\n{json.dumps(state, ensure_ascii=False, indent=2)}\n\nLatest messages:\n{recent_text}"
                messages = [{"role": "system", "content": enhanced_system}]
            except Exception as e:
                logger.error(f"Failed to parse context_summary: {e}")
                messages = [{"role": "system", "content": sys_prompt}]
                for msg in history:
                    messages.append({"role": msg['role'], "content": msg['content']})
        else:
            messages = [{"role": "system", "content": sys_prompt}]
            for msg in history:
                messages.append({"role": msg['role'], "content": msg['content']})

        model = "llama-3.3-70b-versatile"
        try:
            assistant_message = await self.orch.get_chat_completion(messages, model)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError("Failed to generate assistant message") from e

        await self.session_service.add_message_to_session(session_id, "assistant", assistant_message)

        session = await self.session_service.get_clarification_session(session_id)
        state = await self.orch.synthesize_conversation_state(session['history'])
        await self.session_service.update_clarification_session(session_id, context_summary=json.dumps(state))

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
