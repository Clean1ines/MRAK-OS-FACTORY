import json
import re
from typing import Optional, Dict, Any, List
import db

class ArtifactGenerator:
    def __init__(self, groq_client, prompt_loader, mode_map, type_to_mode):
        self.groq_client = groq_client
        self.prompt_loader = prompt_loader
        self.mode_map = mode_map
        self.type_to_mode = type_to_mode

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
            prompt = f"Parent artifact ({parent_artifact['type']}):\n{json.dumps(parent_artifact['content'])}\n\nUser input:\n{user_input}"
        else:
            prompt = user_input

        try:
            response = self.groq_client.create_completion(
                model=model_id or "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
            )
            result_text = response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")

        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            result_data = {"text": result_text}

        artifact_id = await db.save_artifact(
            artifact_type=artifact_type,
            content=result_data,
            owner="system",
            status="GENERATED",
            project_id=project_id,
            parent_id=parent_artifact['id'] if parent_artifact else None
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
        analysis = await db.get_artifact(analysis_id)
        if not analysis:
            raise ValueError("Analysis not found")
        if analysis['type'] != 'ProductCouncilAnalysis':
            raise ValueError("Artifact is not a ProductCouncilAnalysis")

        idea = None
        if analysis.get('parent_id'):
            idea = await db.get_artifact(analysis['parent_id'])

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

        mode = "15_BUSINESS_REQ_GEN"
        sys_prompt = await self.prompt_loader.get_system_prompt(mode, self.mode_map)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        try:
            response = self.groq_client.create_completion(
                model=model_id or "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": full_input},
                ],
                temperature=0.6,
            )
            result_text = response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")

        requirements = []
        try:
            requirements = json.loads(result_text)
            if not isinstance(requirements, list):
                requirements = [requirements]
        except json.JSONDecodeError:
            json_match = re.search(r'\[\s*\{.*\}\s*\]', result_text, re.DOTALL)
            if json_match:
                requirements = json.loads(json_match.group())
            else:
                raise ValueError(f"Failed to parse JSON from response: {result_text[:200]}")

        return requirements

    async def generate_req_engineering_analysis(
        self,
        parent_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_analysis: Optional[Dict] = None
    ) -> Dict[str, Any]:
        parent = await db.get_artifact(parent_id)
        if not parent:
            raise ValueError("Parent artifact not found")
        if parent['type'] != 'BusinessRequirementPackage':
            raise ValueError("Parent is not a BusinessRequirementPackage")

        # Извлекаем описания бизнес-требований для уменьшения потребления токенов
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
            # Передаём существующий анализ для дополнения
            prompt_parts.append(f"EXISTING_ANALYSIS:\n{json.dumps(existing_analysis)}")

        full_input = "\n\n".join(prompt_parts)

        mode = "16_REQ_ENG_COUNCIL"
        sys_prompt = await self.prompt_loader.get_system_prompt(mode, self.mode_map)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        try:
            response = self.groq_client.create_completion(
                model=model_id or "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": full_input},
                ],
                temperature=0.6,
            )
            result_text = response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")

        try:
            analysis_result = json.loads(result_text)
        except json.JSONDecodeError:
            analysis_result = {"text": result_text}

        return analysis_result

    async def generate_functional_requirements(
        self,
        analysis_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует функциональные требования на основе анализа инженерии требований.
        """
        analysis = await db.get_artifact(analysis_id)
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
            response = self.groq_client.create_completion(
                model=model_id or "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": full_input},
                ],
                temperature=0.6,
            )
            result_text = response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")

        functional_reqs = []
        try:
            functional_reqs = json.loads(result_text)
            if not isinstance(functional_reqs, list):
                functional_reqs = [functional_reqs]
        except json.JSONDecodeError:
            json_match = re.search(r'\[\s*\{.*\}\s*\]', result_text, re.DOTALL)
            if json_match:
                functional_reqs = json.loads(json_match.group())
            else:
                raise ValueError(f"Failed to parse JSON from response: {result_text[:200]}")

        return functional_reqs
