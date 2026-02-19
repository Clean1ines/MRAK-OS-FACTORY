from dotenv import load_dotenv
import os
import re
import httpx
import asyncio
from groq import Groq
from typing import Optional, Dict, Any

import db

load_dotenv()


class MrakOrchestrator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.gh_token = os.getenv("GITHUB_TOKEN")
        self.client = Groq(
            api_key=self.api_key, http_client=httpx.Client(timeout=120.0)
        )
        self.base_url = "https://api.groq.com/openai/v1"

        # Маппинг режимов на переменные окружения с URL
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
            "15_BUSINESS_REQ_GEN": "GH_URL_BUSINESS_REQ_GEN",   # Новый режим
            "16_REQ_ENG_COUNCIL": "GH_URL_REQ_ENG_COUNCIL",     # Новый режим
        }

        # Маппинг типа артефакта на режим промпта для генерации
        self.type_to_mode = {
            "BusinessIdea": "14_PRODUCT_COUNCIL",          # идея -> совет титанов
            "ProductCouncilAnalysis": None,                 # анализ не генерируется (это результат)
            "BusinessRequirement": "15_BUSINESS_REQ_GEN",   # анализ -> бизнес-требования
            "ReqEngineeringAnalysis": "16_REQ_ENG_COUNCIL", # бизнес-требования -> анализ инженерии
            "FunctionalRequirement": None,                  # может генерироваться отдельно
            "CodeArtifact": "10_FULL_CODE_GEN",             # требования -> код
        }

    def get_active_models(self):
        fallback_models = [
            {"id": "openai/gpt-oss-120b"},
            {"id": "llama-3.3-70b-versatile"},
            {"id": "llama-3.1-8b-instant"},
            {"id": "groq/compound"},
            {"id": "qwen/qwen3-32b"},
        ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/models", headers=headers, timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    active = [
                        {"id": m["id"]}
                        for m in data.get("data", [])
                        if "whisper" not in m["id"]
                    ]
                    return active if active else fallback_models
                return fallback_models
        except Exception:
            return fallback_models

    async def get_system_prompt(self, mode: str):
        if mode == "07_BYPASS":
            return "You are a helpful assistant."

        env_var = self.mode_map.get(mode, "SYSTEM_PROMPT_URL")
        url = os.getenv(env_var)

        if not url:
            return f"System Error: URL for mode {mode} not found in environment."

        headers = {
            "Accept": "application/vnd.github.v3.raw",
        }
        if self.gh_token:
            headers["Authorization"] = f"token {self.gh_token}"

        async with httpx.AsyncClient() as c:
            try:
                r = await c.get(url, headers=headers, timeout=15)
                if r.status_code == 200:
                    return r.text.strip()
                return f"Error fetching prompt: {r.status_code} for mode {mode}"
            except Exception as e:
                return f"Connection Error: {str(e)}"

    def _pii_filter(self, text: str) -> str:
        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
        text = re.sub(r"(gsk_|sk-)[a-zA-Z0-9]{20,}", "[KEY_REDACTED]", text)
        return text

    async def generate_artifact(
        self,
        artifact_type: str,
        user_input: str,
        parent_artifact: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Генерирует артефакт указанного типа на основе входных данных и родительского артефакта.
        Возвращает ID созданного артефакта или None.
        """
        mode = self.type_to_mode.get(artifact_type)
        if not mode:
            raise ValueError(f"No generation mode defined for artifact type {artifact_type}")

        # Получаем системный промпт
        sys_prompt = await self.get_system_prompt(mode)
        if sys_prompt.startswith("Error") or sys_prompt.startswith("System Error"):
            raise Exception(f"Failed to get system prompt: {sys_prompt}")

        # Формируем входной текст для LLM
        if parent_artifact:
            # Если есть родитель, передаём его содержимое как контекст
            prompt = f"Parent artifact ({parent_artifact['type']}):\n{json.dumps(parent_artifact['content'])}\n\nUser input:\n{user_input}"
        else:
            prompt = user_input

        # Вызываем LLM и получаем полный ответ (не потоковый)
        try:
            response = self.client.chat.completions.create(
                model=model_id or "llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": self._pii_filter(prompt)},
                ],
                temperature=0.6,
            )
            result_text = response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM call failed: {e}")

        # Пытаемся распарсить JSON, если ожидается структурированный ответ
        try:
            # Пробуем найти JSON в ответе (если промпт возвращает JSON)
            # В простом случае считаем, что результат — это и есть JSON
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            # Если не JSON, сохраняем как текст
            result_data = {"text": result_text}

        # Сохраняем результат как новый артефакт
        artifact_id = await db.save_artifact(
            artifact_type=artifact_type,
            content=result_data,
            owner="system",
            status="GENERATED",
            project_id=project_id,
            parent_id=parent_artifact['id'] if parent_artifact else None
        )
        return artifact_id

    async def stream_analysis(self, user_input: str, system_prompt: str, model_id: str, mode: str, project_id: Optional[str] = None):
        """(без изменений)"""
        clean_input = self._pii_filter(user_input)
        full_response = ""
        try:
            raw_res = self.client.chat.completions.with_raw_response.create(
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
