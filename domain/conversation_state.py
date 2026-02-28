# CHANGED: Fixed parse_response to set next_question=None when missing
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ConversationStateSynthesizer:
    """Analyzes conversation history and produces a structured state."""

    def __init__(self, prompt_service):
        """
        :param prompt_service: Instance of PromptService used to get system prompts and call LLM.
        """
        self.prompt_service = prompt_service

    def build_prompt(self, history: List[Dict]) -> str:
        """Build the user prompt from recent history."""
        recent = history[-4:] if len(history) > 4 else history
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent])

    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into a state dictionary."""
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        try:
            state = json.loads(response.strip())
        except json.JSONDecodeError:
            logger.error(f"Failed to parse state JSON: {response[:100]}...")
            return self._default_state()
        required_fields = [
            "clear_context", "unclear_context", "user_questions",
            "answered_questions", "next_question", "completion_score"
        ]
        for field in required_fields:
            if field not in state:
                if field == "completion_score":
                    state[field] = 0.0
                elif field == "next_question":
                    state[field] = None
                else:
                    state[field] = []
        return state

    def _default_state(self) -> Dict[str, Any]:
        """Return a default empty state."""
        return {
            "clear_context": [],
            "unclear_context": [],
            "user_questions": [],
            "answered_questions": [],
            "next_question": None,
            "completion_score": 0.0
        }

    async def synthesize(
        self,
        history: List[Dict],
        model_id: str = "llama-3.3-70b-versatile"
    ) -> Dict[str, Any]:
        """
        Analyze conversation history and return structured state.
        Uses prompt mode '02sum_STATE_SYNTHESIZER'.
        """
        context = self.build_prompt(history)

        sys_prompt = await self.prompt_service.get_system_prompt("02sum_STATE_SYNTHESIZER")
        if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
            logger.error(f"Failed to load State Synthesizer prompt: {sys_prompt}")
            return self._default_state()

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Analyze this conversation and output JSON state:\n{context}"}
        ]
        try:
            response = await self.prompt_service.get_chat_completion(messages, model_id)
            return self.parse_response(response)
        except Exception as e:
            logger.error(f"State synthesis failed: {e}")
            return self._default_state()
