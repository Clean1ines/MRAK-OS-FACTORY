from dotenv import load_dotenv
import os
import re
import asyncio
import json
from typing import Optional, Dict, Any, List

import db
from groq_client import GroqClient
from prompt_loader import PromptLoader
from artifact_generator import ArtifactGenerator

load_dotenv()


class MrakOrchestrator:
    def __init__(self, api_key=None):
        self.gh_token = os.getenv("GITHUB_TOKEN")
        self.groq_client = GroqClient(api_key)
        self.prompt_loader = PromptLoader(self.gh_token)

        self.mode_map = {
            "01_CORE": "SYSTEM_PROMPT_URL",
            "02_UI_UX": "GH_URL_UI_UX",
            "03_SOFT_ENG": "GH_URL_SOFT_ENG",
            "04_FAILURE": "GH_URL_FAILURE",
            "06_TRANSLATOR": "GH_URL_TRANSLATOR",
            "07_INTEGRATION_PLAN": "GH_URL_INTEGRATION_PLAN",
            "08_PROMPT_COUNCIL": "GH_URL_PROMPT_COUNCIL",
            "09_ALGO_COUNCIL": "GH_URL_ALGO_COUNCIL",
            "10_FULL_CODE_GEN": "GH_URL_FULL_CODE_GEN",
            "11_REQ_COUNCIL": "GH_URL_REQ_COUNCIL",
            "12_SELF_ANALYSIS_FACTORY": "GH_URL_SELF_ANALYSIS_FACTORY",
            "13_ARTIFACT_OUTPUT": "GH_URL_MPROMPT",
            "14_PRODUCT_COUNCIL": "GH_URL_PRODUCT_COUNCIL",
            "15_BUSINESS_REQ_GEN": "GH_URL_BUSINESS_REQ_GEN",
            "16_REQ_ENG_COUNCIL": "GH_URL_REQ_ENG_COUNCIL",
        }

        self.type_to_mode = {
            "BusinessIdea": "14_PRODUCT_COUNCIL",
            "ProductCouncilAnalysis": None,
            "BusinessRequirementPackage": "15_BUSINESS_REQ_GEN",
            "ReqEngineeringAnalysis": "16_REQ_ENG_COUNCIL",
            "FunctionalRequirementPackage": None,
            "CodeArtifact": "10_FULL_CODE_GEN",
        }

        self.artifact_generator = ArtifactGenerator(
            self.groq_client,
            self.prompt_loader,
            self.mode_map,
            self.type_to_mode
        )

    def get_active_models(self):
        return self.groq_client.get_active_models()

    async def get_system_prompt(self, mode: str):
        return await self.prompt_loader.get_system_prompt(mode, self.mode_map)

    def _pii_filter(self, text: str) -> str:
        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
        text = re.sub(r"(gsk_|sk-)[a-zA-Z0-9]{20,}", "[KEY_REDACTED]", text)
        return text

    async def generate_artifact(self, artifact_type: str, user_input: str,
                                 parent_artifact: Optional[Dict[str, Any]] = None,
                                 model_id: Optional[str] = None,
                                 project_id: Optional[str] = None) -> Optional[str]:
        return await self.artifact_generator.generate_artifact(
            artifact_type, user_input, parent_artifact, model_id, project_id
        )

    async def generate_business_requirements(
        self,
        analysis_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        return await self.artifact_generator.generate_business_requirements(
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
        """
        Генерирует анализ инженерии требований на основе бизнес-требований (пакета).
        """
        parent = await db.get_artifact(parent_id)
        if not parent:
            raise ValueError("Parent artifact not found")
        if parent['type'] != 'BusinessRequirementPackage':
            raise ValueError("Parent is not a BusinessRequirementPackage")

        # Формируем входные данные для промпта
        prompt_parts = []
        prompt_parts.append(f"BUSINESS_REQUIREMENTS_PACKAGE:\n{json.dumps(parent['content'])}")
        if user_feedback:
            prompt_parts.append(f"USER_FEEDBACK:\n{user_feedback}")
        if existing_analysis:
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

        # Пытаемся распарсить JSON
        try:
            analysis_result = json.loads(result_text)
        except json.JSONDecodeError:
            # Если не JSON, сохраняем как текст (но ожидаем JSON)
            analysis_result = {"text": result_text}

        return analysis_result

    async def stream_analysis(self, user_input: str, system_prompt: str, model_id: str, mode: str, project_id: Optional[str] = None):
        clean_input = self._pii_filter(user_input)
        full_response = ""
        try:
            raw_res = self.groq_client.client.chat.completions.with_raw_response.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": clean_input},
                ],
                stream=True,
                temperature=0.6,
            )

            rt = raw_res.headers.get("x-ratelimit-remaining-tokens", "---")
            rr = raw_res.headers.get("x-ratelimit-remaining-requests", "---")
            yield f"__METADATA__{rt}|{rr}__"

            for chunk in raw_res.parse():
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            if full_response:
                artifact_data = {
                    "user_input": clean_input,
                    "system_prompt": system_prompt[:500] + ("..." if len(system_prompt) > 500 else ""),
                    "model": model_id,
                    "mode": mode,
                    "response": full_response,
                    "metadata": {
                        "tokens_remaining": rt,
                        "requests_remaining": rr
                    }
                }
                asyncio.create_task(
                    db.save_artifact(
                        artifact_type="LLMResponse",
                        content=artifact_data,
                        owner="system",
                        status="GENERATED",
                        project_id=project_id
                    )
                )
        except Exception as e:
            err_msg = str(e).lower()
            if "403" in err_msg:
                yield "🔴 **ACCESS_DENIED**: API заблокирован в вашем регионе."
            elif "429" in err_msg:
                yield "🔴 **RATE_LIMIT**: Подождите, лимиты исчерпаны."
            else:
                yield f"🔴 **GROQ_API_ERROR**: {str(e)}"

    async def generate_functional_requirements(
        self,
        parent_id: str,
        user_feedback: str = "",
        model_id: Optional[str] = None,
        project_id: Optional[str] = None,
        existing_requirements: Optional[List[Dict]] = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует функциональные требования на основе анализа инженерии требований и/или бизнес-требований.
        """
        parent = await db.get_artifact(parent_id)
        if not parent:
            raise ValueError("Parent artifact not found")
        # Родителем может быть ReqEngineeringAnalysis или BusinessRequirementPackage
        # Формируем входные данные
        prompt_parts = []
        prompt_parts.append(f"PARENT_ARTIFACT:\n{json.dumps(parent['content'])}")
        if user_feedback:
            prompt_parts.append(f"USER_FEEDBACK:\n{user_feedback}")
        if existing_requirements:
            prompt_parts.append(f"EXISTING_REQUIREMENTS:\n{json.dumps(existing_requirements)}")

        full_input = "\n\n".join(prompt_parts)

        # Нужен режим для функциональных требований, например 17_FUNC_REQ_GEN
        mode = "17_FUNC_REQ_GEN"  # предположим, что такой режим будет
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
            requirements = json.loads(result_text)
            if not isinstance(requirements, list):
                requirements = [requirements]
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse JSON from response: {result_text[:200]}")

        return requirements
