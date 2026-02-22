# CHANGED: Restored validation and retries in generate_artifact
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List

from repositories.artifact_repository import save_artifact, get_artifact
from repositories.base import transaction
from validation import validate_json_output, ValidationError

from generators import (
    BusinessRequirementsGenerator,
    ReqEngineeringGenerator,
    FunctionalRequirementsGenerator,
)

logger = logging.getLogger("artifact-service")

class ArtifactService:
    def __init__(self, groq_client, prompt_loader, mode_map, type_to_mode):
        self.groq_client = groq_client
        self.prompt_loader = prompt_loader
        self.mode_map = mode_map
        self.type_to_mode = type_to_mode

        # Instantiate generators
        self.business_req_gen = BusinessRequirementsGenerator(
            groq_client, prompt_loader, mode_map, type_to_mode
        )
        self.req_engineering_gen = ReqEngineeringGenerator(
            groq_client, prompt_loader, mode_map, type_to_mode
        )
        self.functional_req_gen = FunctionalRequirementsGenerator(
            groq_client, prompt_loader, mode_map, type_to_mode
        )

    async def generate_artifact(
        self,
        artifact_type: str,
        user_input: str,
        parent_artifact: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[str]:
        mode = self.type_to_mode.get(artifact_type)
        if not mode:
            raise ValueError(f"No generation mode defined for artifact type {artifact_type}")

        sys_prompt = await self.prompt_loader.get_system_prompt(mode, self.mode_map)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        if parent_artifact:
            user_prompt = f"Parent artifact ({parent_artifact['type']}):\n{json.dumps(parent_artifact['content'])}\n\nUser input:\n{user_input}"
        else:
            user_prompt = user_input

        # Retry logic with validation (copied from old _call_llm_with_retry)
        attempt = 0
        retries = 3
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

                # Try to parse JSON
                try:
                    result_data = json.loads(result_text)
                except json.JSONDecodeError:
                    # If not JSON, maybe it's text – for structured types this is an error
                    if artifact_type in validation.REQUIRED_FIELDS:
                        raise ValueError("Response is not valid JSON")
                    else:
                        result_data = {"text": result_text}

                # Validate for structured types
                valid, msg = validate_json_output(result_data, artifact_type)
                if not valid:
                    raise ValueError(f"Validation failed: {msg}")

                # Save in transaction
                async with transaction() as tx:
                    artifact_id = await save_artifact(
                        artifact_type=artifact_type,
                        content=result_data,
                        owner="system",
                        status="GENERATED",
                        project_id=project_id,
                        parent_id=parent_artifact['id'] if parent_artifact else None,
                        tx=tx
                    )
                return artifact_id

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

    async def generate_business_requirements(
        self,
        analysis_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        return await self.business_req_gen.generate(
            analysis_id=analysis_id,
            user_feedback=user_feedback,
            model_id=model_id,
            project_id=project_id,
            existing_requirements=existing_requirements
        )

    async def generate_req_engineering_analysis(
        self,
        parent_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_analysis: Optional[Dict] = None
    ) -> Dict[str, Any]:
        return await self.req_engineering_gen.generate(
            parent_id=parent_id,
            user_feedback=user_feedback,
            model_id=model_id,
            project_id=project_id,
            existing_analysis=existing_analysis
        )

    async def generate_functional_requirements(
        self,
        analysis_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        return await self.functional_req_gen.generate(
            analysis_id=analysis_id,
            user_feedback=user_feedback,
            model_id=model_id,
            project_id=project_id,
            existing_requirements=existing_requirements
        )
