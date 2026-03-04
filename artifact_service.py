import json
import asyncio
import logging
from typing import Optional, Dict, Any, List

from repositories.artifact_repository import save_artifact
from repositories.base import transaction
from validation import validate_json_output, ValidationError, REQUIRED_FIELDS

logger = logging.getLogger("artifact-service")

class ArtifactService:
    """
    Универсальный сервис для генерации артефактов.
    Все настройки передаются через generation_config (из ноды).
    """

    def __init__(self, groq_client):
        self.groq_client = groq_client

    async def _call_llm_with_retry(
        self,
        sys_prompt: str,
        user_prompt: str,
        model_id: Optional[str],
        artifact_type: str,
        retries: int = 3
    ) -> Any:
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
                    if artifact_type in REQUIRED_FIELDS:
                        raise ValueError("Response is not valid JSON")
                    else:
                        result_data = {"text": result_text}

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

    def _prepare_context(self, config: dict, input_artifacts: List[Dict]) -> Dict[str, str]:
        """Преобразует входные артефакты в переменные для шаблона."""
        context = {}

        all_parts = []
        for art in input_artifacts:
            all_parts.append(f"--- {art['type']} (id: {art['id']}) ---\n{json.dumps(art['content'], indent=2)}")
        context["all_artifacts"] = "\n\n".join(all_parts)

        for req_type in config.get("required_input_types", []):
            art = next((a for a in input_artifacts if a["type"] == req_type), None)
            var_name = req_type[0].lower() + req_type[1:]
            if art:
                context[var_name] = json.dumps(art["content"], indent=2)
            else:
                logger.warning(f"Required input type '{req_type}' not found")
                context[var_name] = ""

        return context

    async def generate_artifact(
        self,
        artifact_type: str,
        input_artifacts: Optional[List[Dict]] = None,
        user_input: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        generation_config: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Генерирует артефакт.
        :param artifact_type: метка типа (будет сохранена в поле type артефакта).
        :param input_artifacts: список входных артефактов.
        :param user_input: пользовательский ввод (feedback).
        :param model_id: идентификатор модели.
        :param project_id: идентификатор проекта.
        :param generation_config: словарь с ключами:
            - system_prompt (str) – обязательный,
            - user_prompt_template (str) – опциональный (по умолчанию "Context:\n{all_artifacts}\n\nUser input:\n{user_input}"),
            - required_input_types (list) – опционально.
        """
        if input_artifacts is None:
            input_artifacts = []
        if generation_config is None:
            generation_config = {}

        system_prompt = generation_config.get("system_prompt")
        if not system_prompt:
            raise ValueError("generation_config must contain 'system_prompt'")

        template = generation_config.get("user_prompt_template")
        if not template:
            template = "Context:\n{all_artifacts}\n\nUser input:\n{user_input}"

        context = self._prepare_context(generation_config, input_artifacts)
        context["user_input"] = user_input

        user_prompt = template.format(**context)

        result_data = await self._call_llm_with_retry(
            sys_prompt=system_prompt,
            user_prompt=user_prompt,
            model_id=model_id,
            artifact_type=artifact_type
        )

        async with transaction() as tx:
            artifact_id = await save_artifact(
                artifact_type=artifact_type,
                content=result_data,
                owner="system",
                status="GENERATED",
                project_id=project_id,
                parent_id=None,
                tx=tx
            )
        logger.info(f"Generated artifact {artifact_id} of type {artifact_type}")
        return artifact_id
