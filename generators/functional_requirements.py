# ADDED: Generator for FunctionalRequirementPackage
import json
import logging
from typing import Optional, Dict, Any, List

from .base import BaseArtifactGenerator
from repositories.artifact_repository import get_artifact
from repositories.base import transaction

logger = logging.getLogger("artifact-generator.functional-requirements")

class FunctionalRequirementsGenerator(BaseArtifactGenerator):
    """Generator for FunctionalRequirementPackage artifacts."""

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
