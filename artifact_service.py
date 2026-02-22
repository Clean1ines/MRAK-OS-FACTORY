# CHANGED: Use transactions where multiple operations occur
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from repositories.artifact_repository import save_artifact, get_artifact
from repositories.base import transaction  # ADDED
from validation import validate_json_output, ValidationError

logger = logging.getLogger("artifact-service")

class ArtifactService:
    def __init__(self, groq_client, prompt_loader, mode_map, type_to_mode):
        self.groq_client = groq_client
        self.prompt_loader = prompt_loader
        self.mode_map = mode_map
        self.type_to_mode = type_to_mode

    async def _call_llm_with_retry(self, sys_prompt: str, user_prompt: str,
                                    model_id: str, artifact_type: str,
                                    retries: int = 3) -> Any:
        # (unchanged)
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

        try:
            result_data = await self._call_llm_with_retry(sys_prompt, user_prompt, model_id, artifact_type)
        except ValidationError as e:
            logger.error(f"Validation failed for {artifact_type}: {e}")
            raise

        # Save in a transaction (optional but good for consistency)
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

    async def generate_business_requirements(
        self,
        analysis_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        # Read and write should be atomic
        async with transaction() as tx:
            analysis = await get_artifact(analysis_id, tx=tx)
            if not analysis:
                raise ValueError("Analysis not found")
            if analysis['type'] != 'ProductCouncilAnalysis':
                raise ValueError("Artifact is not a ProductCouncilAnalysis")

            idea = None
            if analysis.get('parent_id'):
                idea = await get_artifact(analysis['parent_id'], tx=tx)

            # Build prompt (doesn't use DB)
            prompt_parts = []
            if idea:
                prompt_parts.append(f"RAW_IDEA:\n{json.dumps(idea['content'])}")
            else:
                prompt_parts.append("RAW_IDEA:\n(not provided)")

            prompt_parts.append(f"PRODUCT_COUNCIL_ANALYSIS:\n{json.dumps(analysis['content'])}")

            if user_feedback:
                prompt_parts.append(f"USER_FEEDBACK:\n{user_feedback}")

            if existing_requirements:
                existing_descs = [req.get('description', '') for req in existing_requirements]
                prompt_parts.append(f"EXISTING_REQUIREMENTS:\n{json.dumps(existing_descs)}")

            full_input = "\n\n".join(prompt_parts)

        # LLM call outside transaction
        mode = "04_BUSINESS_REQ_GEN"
        sys_prompt = await self.prompt_loader.get_system_prompt(mode, self.mode_map)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        try:
            result_data = await self._call_llm_with_retry(
                sys_prompt, full_input, model_id, "BusinessRequirementPackage"
            )
        except ValidationError as e:
            logger.error(f"Failed to generate business requirements: {e}")
            raise

        # Save in transaction
        if not isinstance(result_data, list):
            result_data = [result_data] if result_data else []

        # We could save the artifact here, but the original method didn't save – it returned the data.
        # Actually the original method returns the list, and the caller saves it separately.
        # So we don't save here; just return.
        return result_data

    async def generate_req_engineering_analysis(
        self,
        parent_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_analysis: Optional[Dict] = None
    ) -> Dict[str, Any]:
        async with transaction() as tx:
            parent = await get_artifact(parent_id, tx=tx)
            if not parent:
                raise ValueError("Parent artifact not found")
            if parent['type'] != 'BusinessRequirementPackage':
                raise ValueError("Parent is not a BusinessRequirementPackage")

            # Extract descriptions
            parent_content = parent['content']
            if isinstance(parent_content, dict) and 'requirements' in parent_content:
                reqs = parent_content['requirements']
            else:
                reqs = parent_content
            descriptions = [r.get('description', '') for r in reqs if isinstance(r, dict)]

        prompt_parts = []
        prompt_parts.append(f"BUSINESS_REQUIREMENTS_DESCRIPTIONS:\n{json.dumps(descriptions)}")
        if user_feedback:
            prompt_parts.append(f"USER_FEEDBACK:\n{user_feedback}")
        if existing_analysis:
            prompt_parts.append(f"EXISTING_ANALYSIS:\n{json.dumps(existing_analysis)}")

        full_input = "\n\n".join(prompt_parts)

        mode = "05_REQ_ENG_COUNCIL"
        sys_prompt = await self.prompt_loader.get_system_prompt(mode, self.mode_map)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        try:
            result_data = await self._call_llm_with_retry(
                sys_prompt, full_input, model_id, "ReqEngineeringAnalysis"
            )
        except ValidationError as e:
            logger.error(f"Failed to generate req engineering analysis: {e}")
            raise

        # Optionally save? Original just returns. We'll keep same.
        return result_data

    async def generate_functional_requirements(
        self,
        analysis_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        async with transaction() as tx:
            analysis = await get_artifact(analysis_id, tx=tx)
            if not analysis:
                raise ValueError("Analysis not found")
            if analysis['type'] != 'ReqEngineeringAnalysis':
                raise ValueError("Parent is not a ReqEngineeringAnalysis")

        prompt_parts = []
        prompt_parts.append(f"REQ_ENGINEERING_ANALYSIS:\n{json.dumps(analysis['content'])}")
        if user_feedback:
            prompt_parts.append(f"USER_FEEDBACK:\n{user_feedback}")
        if existing_requirements:
            existing_descs = [r.get('description', '') for r in existing_requirements]
            prompt_parts.append(f"EXISTING_FUNCTIONAL_REQUIREMENTS:\n{json.dumps(existing_descs)}")

        full_input = "\n\n".join(prompt_parts)

        mode = "17_FUNCTIONAL_REQ_GEN"
        sys_prompt = await self.prompt_loader.get_system_prompt(mode, self.mode_map)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        try:
            result_data = await self._call_llm_with_retry(
                sys_prompt, full_input, model_id, "FunctionalRequirementPackage"
            )
        except ValidationError as e:
            logger.error(f"Failed to generate functional requirements: {e}")
            raise

        if not isinstance(result_data, list):
            result_data = [result_data] if result_data else []
        return result_data
