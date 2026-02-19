import httpx
from groq import Groq
import os

class GroqClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = Groq(
            api_key=self.api_key, http_client=httpx.Client(timeout=120.0)
        )
        self.base_url = "https://api.groq.com/openai/v1"

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

    def create_completion(self, model, messages, stream=False, temperature=0.6):
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            temperature=temperature,
        )
