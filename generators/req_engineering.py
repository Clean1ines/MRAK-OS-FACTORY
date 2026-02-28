# ADDED: Generator for ReqEngineeringAnalysis
import json
import logging
from typing import Optional, Dict, Any, List

from .base import BaseArtifactGenerator
from repositories.artifact_repository import get_artifact
from repositories.base import transaction

logger = logging.getLogger("artifact-generator.req-engineering")

class ReqEngineeringGenerator(BaseArtifactGenerator):
    """Generator for ReqEngineeringAnalysis artifacts."""

    async def generate(self,
                       parent_id: str,
                       user_feedback: str = "",
                       model_id: Optional[str] = None,
                       project_id: Optional[str] = None,
                       existing_analysis: Optional[Dict] = None) -> Dict[str, Any]:
        # Read parent in transaction
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

        return result_data
