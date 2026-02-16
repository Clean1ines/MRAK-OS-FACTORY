import os
import re
import httpx
from groq import Groq


class MrakOrchestrator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.gh_token = os.getenv("GH_TOKEN")
        self.client = Groq(
            api_key=self.api_key, http_client=httpx.Client(timeout=120.0)
        )

        self.mode_map = {
            "01_CORE": "GH_PROMPT_URL",
            "02_UI_UX": "GH_URL_UI_UX",
            "03_SOFT_ENG": "GH_URL_SOFT_ENG",
            "04_FAILURE": "GH_URL_FAILURE",
            "05_ARCHITECT": "GH_URL_ARCHITECT",
            "06_TRANSLATOR": "GH_URL_TRANSLATOR",
        }

    async def get_system_prompt(self, mode: str):
        if mode == "07_BYPASS":
            return "You are a helpful assistant."
        env_var = self.mode_map.get(mode, "GH_PROMPT_URL")
        url = os.getenv(env_var)
        if not (self.gh_token and url):
            return "System Error: Configuration missing."

        headers = {
            "Authorization": f"token {self.gh_token}",
            "Accept": "application/vnd.github.v3.raw",
        }
        async with httpx.AsyncClient() as c:
            try:
                r = await c.get(url, headers=headers, timeout=10)
                return (
                    r.text.strip()
                    if r.status_code == 200
                    else f"Error: {r.status_code}"
                )
            except:
                return "Connection Error"

    def _pii_filter(self, text: str) -> str:
        # Унифицируем плейсхолдеры для тестов
        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", text)
        text = re.sub(r"(gsk_|sk-)[a-zA-Z0-9]{20,}", "[KEY_REDACTED]", text)
        return text

    def stream_analysis(self, user_input: str, system_prompt: str, model_id: str):
        clean_input = self._pii_filter(user_input)

        with self.client.chat.completions.with_raw_response.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": clean_input},
            ],
            stream=True,
            temperature=0.6,
        ) as response:
            rem_tokens = response.headers.get("x-ratelimit-remaining-tokens", "---")
            rem_req = response.headers.get("x-ratelimit-remaining-requests", "---")

            yield f"__METADATA__{rem_tokens}|{rem_req}__"

            completion = response.parse()
            for chunk in completion:
                if content := chunk.choices[0].delta.content:
                    yield content
