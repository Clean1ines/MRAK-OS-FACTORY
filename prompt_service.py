# CHANGED: Delegates state synthesis to ConversationStateSynthesizer
import json
import logging
from typing import List, Dict, Any, Optional

from domain.conversation_state import ConversationStateSynthesizer  # ADDED

logger = logging.getLogger("PROMPT-SERVICE")

class PromptService:
    def __init__(self, groq_client, prompt_loader, mode_map):
        self.groq_client = groq_client
        self.prompt_loader = prompt_loader
        self.mode_map = mode_map
        # ADDED: instantiate synthesizer with self
        self.state_synthesizer = ConversationStateSynthesizer(self)

    async def get_system_prompt(self, mode: str) -> str:
        """Возвращает системный промпт для указанного режима."""
        return await self.prompt_loader.get_system_prompt(mode, self.mode_map)

    async def get_chat_completion(self, messages: List[Dict[str, str]], model_id: str) -> str:
        """Выполняет запрос к LLM без стриминга, возвращает полный текст ответа."""
        try:
            completion = self.groq_client.create_completion(
                model=model_id,
                messages=messages,
                temperature=0.6,
                stream=False
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def synthesize_conversation_state(
        self,
        history: List[Dict],
        model_id: str = "llama-3.3-70b-versatile"
    ) -> Dict[str, Any]:
        """
        Анализирует последние сообщения диалога и возвращает структурированное состояние.
        Использует промпт 02sum_STATE_SYNTHESIZER.
        """
        # CHANGED: delegate to synthesizer
        return await self.state_synthesizer.synthesize(history, model_id)
