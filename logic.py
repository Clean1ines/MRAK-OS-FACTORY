import os
import re
import httpx
from groq import Groq

class MrakOrchestrator:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key, http_client=httpx.Client(timeout=120.0))

    async def get_system_prompt(self):
        token, url = os.getenv("GH_TOKEN"), os.getenv("GH_PROMPT_URL")
        if not (token and url): return "Вы — полезный ИИ-ассистент."
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3.raw'}
        async with httpx.AsyncClient() as c:
            try:
                r = await c.get(url, headers=headers, timeout=10)
                return r.text.strip() if r.status_code == 200 else "Error loading prompt"
            except: return "Fallback prompt"

    def _pii_filter(self, text: str) -> str:
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]', text)
        text = re.sub(r'(gsk_|sk-)[a-zA-Z0-9]{20,}', '[KEY_REDACTED]', text)
        return text

    def stream_analysis(self, user_input: str, system_prompt: str):
        clean_input = self._pii_filter(user_input)
        stream = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": clean_input}],
            stream=True, temperature=0.6
        )
        for chunk in stream:
            if content := chunk.choices[0].delta.content:
                yield content