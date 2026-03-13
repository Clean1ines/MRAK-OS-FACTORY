# use_cases/add_message.py
import json
import logging
from schemas import MessageRequest, ClarificationSessionResponse
from prompt_service import PromptService
from session_service import SessionService
from services import TYPE_TO_MODE
import db

logger = logging.getLogger(__name__)

class AddMessageUseCase:
    def __init__(self, prompt_service: PromptService, session_service: SessionService):
        self.prompt_service = prompt_service
        self.session_service = session_service

    async def execute(self, session_id: str, req: MessageRequest) -> ClarificationSessionResponse:
        session = await self.session_service.get_clarification_session(session_id)
        if not session:
            raise ValueError("Session not found")

        if session['status'] != 'active':
            raise ValueError("Session is not active")

        # Сохраняем сообщение пользователя
        await self.session_service.add_message_to_session(session_id, "user", req.message)

        # Обновлённая сессия с историей
        session = await self.session_service.get_clarification_session(session_id)
        history = session['history']

        # Определяем системный промпт
        system_prompt = None
        context_summary = session.get('context_summary')

        # Если context_summary – простая строка (не JSON), используем её как системный промпт
        if context_summary and not (context_summary.startswith('{') or context_summary.startswith('[')):
            system_prompt = context_summary
        else:
            # Иначе используем старую логику с TYPE_TO_MODE (для обратной совместимости)
            mode = TYPE_TO_MODE.get(session['target_artifact_type'])
            if not mode:
                raise ValueError(f"No prompt mode found for artifact type {session['target_artifact_type']}")
            sys_prompt = await self.prompt_service.get_system_prompt(mode)
            if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
                raise RuntimeError(sys_prompt)
            system_prompt = sys_prompt

        # Формируем сообщения для LLM: системный + вся история
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg['role'], "content": msg['content']})

        model = "llama-3.3-70b-versatile"
        try:
            assistant_message = await self.prompt_service.get_chat_completion(messages, model)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError("Failed to generate assistant message") from e

        # Сохраняем ответ ассистента
        await self.session_service.add_message_to_session(session_id, "assistant", assistant_message)

        # Синтезируем состояние (если нужно)
        session = await self.session_service.get_clarification_session(session_id)
        state = await self.prompt_service.synthesize_conversation_state(session['history'], model)
        await self.session_service.update_clarification_session(session_id, context_summary=json.dumps(state))

        session = await self.session_service.get_clarification_session(session_id)

        return ClarificationSessionResponse(
            id=session['id'],
            project_id=session['project_id'],
            target_artifact_type=session['target_artifact_type'],
            history=session['history'],
            status=session['status'],
            context_summary=json.loads(session['context_summary']) if session.get('context_summary') and (session['context_summary'].startswith('{') or session['context_summary'].startswith('[')) else None,
            final_artifact_id=session.get('final_artifact_id'),
            created_at=session['created_at'],
            updated_at=session['updated_at']
        )