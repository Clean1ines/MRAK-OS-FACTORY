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
        "02_IDEA_CLARIFIER": "GH_URL_IDEA_CLARIFIER",
        "03_PRODUCT_COUNCIL": "GH_URL_PRODUCT_COUNCIL",
        "04_BUSINESS_REQ_GEN": "GH_URL_BUSINESS_REQ_GEN",
        "05_REQ_ENG_COUNCIL": "GH_URL_REQ_ENG_COUNCIL",
        "06_SYSTEM_REQ_GEN": "GH_URL_SYSTEM_REQ_GEN",
        "07_QA_COUNCIL": "GH_URL_QA_COUNCIL",
        "08_ARCHITECTURE_COUNCIL": "GH_URL_ARCHITECTURE_COUNCIL",
        "09_CODE_TASK_GEN": "GH_URL_CODE_TASK_GEN",
        "10_CODE_GEN": "GH_URL_CODE_GEN",
        "11_TEST_GEN": "GH_URL_TEST_GEN",
        "12_FAILURE_DETECTOR": "GH_URL_FAILURE_DETECTOR",
        "13_SELF_ANALYSIS_FACTORY": "GH_URL_SELF_ANALYSIS_FACTORY",
        "14_PROMPT_ENGINEERING_COUNCIL": "GH_URL_PROMPT_ENGINEERING_COUNCIL",
        "15_ALGORITHM_COUNCIL": "GH_URL_ALGORITHM_COUNCIL",
        "16_UI_UX_COUNCIL": "GH_URL_UI_UX_COUNCIL",
        "17_SOFT_ENG_COUNCIL": "GH_URL_SOFT_ENG_COUNCIL",
        "18_TRANSLATOR": "GH_URL_TRANSLATOR",
        "19_INTEGRATION_PLAN": "GH_URL_INTEGRATION_PLAN",
        "20_SECURITY_REQ_GEN": "GH_URL_SECURITY_REQ_GEN",
        "21_THREAT_MODELING_ASSISTANT": "GH_URL_THREAT_MODELING_ASSISTANT",
        "22_INFRASTRUCTURE_SPEC_GEN": "GH_URL_INFRASTRUCTURE_SPEC_GEN",
        "23_OBSERVABILITY_SPEC_GEN": "GH_URL_OBSERVABILITY_SPEC_GEN",
        "24_TECH_DESIGN_DOC_GEN": "GH_URL_TECH_DESIGN_DOC_GEN",
        "25_USER_DOC_GEN": "GH_URL_USER_DOC_GEN",
        "26_API_DOC_GEN": "GH_URL_API_DOC_GEN",
        "27_UAT_SCRIPT_GEN": "GH_URL_UAT_SCRIPT_GEN",
        "28_JIRA_ISSUE_FORMATTER": "GH_URL_JIRA_ISSUE_FORMATTER",
        "29_PROJECT_STATUS_REPORTER": "GH_URL_PROJECT_STATUS_REPORTER",
        "30_INCIDENT_POST_MORTEM_GEN": "GH_URL_INCIDENT_POST_MORTEM_GEN",
        "31_KNOWLEDGE_QUERY_ASSISTANT": "GH_URL_KNOWLEDGE_QUERY_ASSISTANT",
        "32_CHANGE_IMPACT_ANALYZER": "GH_URL_CHANGE_IMPACT_ANALYZER",
        "33_FEATURE_TO_USER_STORY_GEN": "GH_URL_FEATURE_TO_USER_STORY_GEN",
        "34_RESEARCH_METODOLOGY_GEN": "GH_URL_RESEARCH_METODOLOGY_GEN",
        "35_ANALYSIS_SUMMARIZER": "GH_URL_ANALYSIS_SUMMARIZER",
        "36_REQUIREMENT_SUMMARIZER": "GH_URL_REQUIREMENT_SUMMARIZER",
        "37_SYSTEM_REQUIREMENTS_SUMMARIZER": "GH_URL_SYSTEM_REQUIREMENTS_SUMMARIZER",
        "38_CODE_CONTEXT_SUMMARIZER": "GH_URL_CODE_CONTEXT_SUMMARIZER",
    }

        self.type_to_mode = {
            "BusinessIdea": "03_PRODUCT_COUNCIL",
            "ProductCouncilAnalysis": None,
            "BusinessRequirementPackage": "04_BUSINESS_REQ_GEN",
            "ReqEngineeringAnalysis": "05_REQ_ENG_COUNCIL",
            "FunctionalRequirementPackage": "17_FUNCTIONAL_REQ_GEN",
            "CodeArtifact": "10_CODE_GEN",
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
        return await self.artifact_generator.generate_req_engineering_analysis(
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
        return await self.artifact_generator.generate_functional_requirements(
            analysis_id=analysis_id,
            user_feedback=user_feedback,
            model_id=model_id,
            project_id=project_id,
            existing_requirements=existing_requirements
        )

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
