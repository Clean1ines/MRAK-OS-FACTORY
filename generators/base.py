# ADDED: Base class for artifact generators
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from repositories.artifact_repository import save_artifact, get_artifact
from validation import validate_json_output, ValidationError

logger = logging.getLogger("artifact-generator")

class BaseArtifactGenerator(ABC):
    """Base class for all artifact generators."""

    def __init__(self, groq_client, prompt_loader, mode_map, type_to_mode):
        self.groq_client = groq_client
        self.prompt_loader = prompt_loader
        self.mode_map = mode_map
        self.type_to_mode = type_to_mode

    async def _call_llm_with_retry(self, sys_prompt: str, user_prompt: str,
                                    model_id: str, artifact_type: str,
                                    retries: int = 3) -> Any:
        """
        Вызывает LLM, парсит JSON и валидирует результат.
        При невалидном результате повторяет до retries раз с экспоненциальной задержкой.
        Возвращает распарсенный и валидный JSON.
        """
        attempt = 0
        last_error = None
        while attempt <= retries:
            try:
                response = self.groq_client.create_completion(
                    model=model_id or "llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.6,
                )
                result_text = response.choices[0].message.content

                try:
                    result_data = json.loads(result_text)
                except json.JSONDecodeError:
                    # Если не JSON, возможно, это текст – для некоторых типов допустимо
                    if artifact_type in validation.REQUIRED_FIELDS:
                        raise ValueError("Response is not valid JSON")
                    else:
                        return {"text": result_text}

                valid, msg = validate_json_output(result_data, artifact_type)
                if not valid:
                    raise ValueError(f"Validation failed: {msg}")

                return result_data

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt+1}/{retries+1} failed for {artifact_type}: {e}")
                attempt += 1
                if attempt <= retries:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    break

        raise ValidationError(f"Failed to generate valid {artifact_type} after {retries+1} attempts. Last error: {last_error}")

    @abstractmethod
    async def generate(self, **kwargs) -> Any:
        """Generate the artifact. Must be implemented by subclasses."""
        pass
