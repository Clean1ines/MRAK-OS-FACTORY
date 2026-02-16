import os
import re
import logging
import time
import httpx
from typing import Dict, Any, Optional, Generator
from groq import Groq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)

class MrakOrchestrator:
    def __init__(self, api_key: Optional[str] = None, prompt_path: str = "system_prompt.txt"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY не найден!")
            
        # Увеличен таймаут до 120с для тяжелых дампов и отключены системные прокси
        self.client = Groq(
            api_key=self.api_key,
            http_client=httpx.Client(
                timeout=httpx.Timeout(120.0, connect=10.0),
                proxies={}
            ),
            max_retries=2
        )
        self.model = "llama-3.3-70b-versatile"
        self.system_prompt = self._load_prompt(prompt_path)

    def _load_prompt(self, path: str) -> str:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            return "Вы — полезный ИИ-ассистент."
        except Exception as e:
            logging.error(f"Ошибка загрузки промпта: {e}")
            return "Вы — полезный ИИ-ассистент."

    def _pii_filter(self, text: str) -> str:
        if not isinstance(text, str): return ""
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]', text)
        text = re.sub(r'(gsk_|sk-)[a-zA-Z0-9]{20,}', '[KEY_REDACTED]', text)
        return text

    def process_request_stream(self, user_prompt: str) -> Generator[Dict[str, Any], None, None]:
        if not user_prompt or not user_prompt.strip():
            yield {"success": False, "error": "Запрос пуст."}
            return

        clean_prompt = self._pii_filter(user_prompt)
        start_time = time.perf_counter()
        full_content = ""

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": clean_prompt}
                ],
                temperature=0.6,
                stream=True
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_content += content
                    yield {
                        "success": True,
                        "full_content": full_content,
                        "elapsed": time.perf_counter() - start_time
                    }
        except Exception as e:
            logging.error(f"Stream Error: {e}")
            yield {"success": False, "error": str(e)}