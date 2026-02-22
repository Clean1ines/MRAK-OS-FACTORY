# prompt_service.py
# Service for prompt-related operations

import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("PROMPT-SERVICE")

class PromptService:
    def __init__(self, groq_client, prompt_loader, mode_map):
        self.groq_client = groq_client
        self.prompt_loader = prompt_loader
        self.mode_map = mode_map

    async def get_system_prompt(self, mode: str) -> str:
        """Возвращает системный промпт для указанного режима."""
        return await self.prompt_loader.get_system_prompt(mode, self.mode_map)

    async def get_chat_completion(self, messages: List[Dict[str, str]], model_id: str) -> str:
        """Выполняет запрос к LLM без стриминга, возвращает полный текст ответа."""
        try:
            # Используем правильный метод create_completion из groq_client
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
        recent = history[-4:] if len(history) > 4 else history
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])

        sys_prompt = await self.get_system_prompt("02sum_STATE_SYNTHESIZER")
        if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
            logger.error(f"Failed to load State Synthesizer prompt: {sys_prompt}")
            return {
                "clear_context": [],
                "unclear_context": [],
                "user_questions": [],
                "answered_questions": [],
                "next_question": None,
                "completion_score": 0.0
            }

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Analyze this conversation and output JSON state:\n{context}"}
        ]
        try:
            response = await self.get_chat_completion(messages, model_id)
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            state = json.loads(response.strip())
            required_fields = ["clear_context", "unclear_context", "user_questions", "answered_questions", "next_question", "completion_score"]
            for field in required_fields:
                if field not in state:
                    state[field] = [] if field != "completion_score" else 0.0
            return state
        except Exception as e:
            logger.error(f"State synthesis failed: {e}")
            return {
                "clear_context": [],
                "unclear_context": [],
                "user_questions": [],
                "answered_questions": [],
                "next_question": None,
                "completion_score": 0.0
            }
