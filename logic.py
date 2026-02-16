from dotenv import load_dotenv
import os
import re
import httpx
from groq import Groq

load_dotenv()


class MrakOrchestrator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.gh_token = os.getenv("GH_TOKEN")
        self.client = Groq(
            api_key=self.api_key, http_client=httpx.Client(timeout=120.0)
        )
        self.base_url = "https://api.groq.com/openai/v1"

        self.mode_map = {
            "01_CORE": "GH_PROMPT_URL",
            "02_UI_UX": "GH_URL_UI_UX",
            "03_SOFT_ENG": "GH_URL_SOFT_ENG",
            "04_FAILURE": "GH_URL_FAILURE",
            "05_ARCHITECT": "GH_URL_ARCHITECT",
            "06_TRANSLATOR": "GH_URL_TRANSLATOR",
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
        env_var = self.mode_map.get(mode, "GH_PROMPT_URL")
        url = os.getenv(env_var)
        if not (self.gh_token and url):
            return "System Error: Config Missing."
        headers = {
            "Authorization": f"token {self.gh_token}",
            "Accept": "application/vnd.github.v3.raw",
        }
        async with httpx.AsyncClient() as c:
            try:
                r = await c.get(url, headers=headers, timeout=15)
                if r.status_code == 200:
                    return r.text.strip()
                return f"Error: {r.status_code}"
            except Exception as e:
                return f"Connection Error: {str(e)}"

    def _pii_filter(self, text: str) -> str:
        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
        text = re.sub(r"(gsk_|sk-)[a-zA-Z0-9]{20,}", "[KEY_REDACTED]", text)
        return text

    def stream_analysis(self, user_input: str, system_prompt: str, model_id: str):
        clean_input = self._pii_filter(user_input)
        try:
            # Получаем сырой ответ для доступа к заголовкам
            raw_res = self.client.chat.completions.with_raw_response.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": clean_input},
                ],
                stream=True,
                temperature=0.6,
            )

            # Извлекаем лимиты
            rt = raw_res.headers.get("x-ratelimit-remaining-tokens", "---")
            rr = raw_res.headers.get("x-ratelimit-remaining-requests", "---")
            yield f"__METADATA__{rt}|{rr}__"

            # Стримим контент
            for chunk in raw_res.parse():
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            err_msg = str(e).lower()
            if "403" in err_msg:
                yield "🔴 **ACCESS_DENIED**: API заблокирован в вашем регионе."
            elif "429" in err_msg:
                yield "🔴 **RATE_LIMIT**: Подождите, лимиты исчерпаны."
            else:
                yield f"🔴 **GROQ_API_ERROR**: {str(e)}"
