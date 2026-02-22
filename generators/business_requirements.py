# ADDED: Generator for BusinessRequirementPackage
import json
import logging
from typing import Optional, Dict, Any, List

from .base import BaseArtifactGenerator
from repositories.artifact_repository import get_artifact
from repositories.base import transaction

logger = logging.getLogger("artifact-generator.business-requirements")

class BusinessRequirementsGenerator(BaseArtifactGenerator):
    """Generator for BusinessRequirementPackage artifacts."""

    async def generate(self,
                       analysis_id: str,
                       user_feedback: str = "",
                       model_id: Optional[str] = None,
                       project_id: Optional[str] = None,
                       existing_requirements: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        # Read analysis in transaction
        async with transaction() as tx:
            analysis = await get_artifact(analysis_id, tx=tx)
            if not analysis:
                raise ValueError("Analysis not found")
            if analysis['type'] != 'ProductCouncilAnalysis':
                raise ValueError("Artifact is not a ProductCouncilAnalysis")

            idea = None
            if analysis.get('parent_id'):
                idea = await get_artifact(analysis['parent_id'], tx=tx)

        # Build prompt (no DB)
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

        if not isinstance(result_data, list):
            result_data = [result_data] if result_data else []

        # Note: The original method did not save the artifact; it returned the data.
        # The caller (orchestrator) is responsible for saving. We follow the same pattern.
        return result_data
