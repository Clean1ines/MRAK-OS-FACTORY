import os
import httpx
from pathlib import Path

class PromptLoader:
    def __init__(self, gh_token):
        self.gh_token = gh_token
        self.prompts_dir = Path(__file__).parent / "prompts"

    async def get_system_prompt(self, mode: str, mode_map: dict):
        # Сначала пытаемся загрузить из локальной папки
        local_path = self.prompts_dir / mode / f"{mode}.txt"
        # Для 01-core особый путь: prompts/01-core/01-core-prompt.txt
        if mode == "01_CORE":
            local_path = self.prompts_dir / "01-core" / "01-core-prompt.txt"

        if local_path.exists():
            try:
                return local_path.read_text().strip()
            except Exception as e:
                return f"System Error: Cannot read local prompt file: {e}"

        # Если локального файла нет, пробуем загрузить из GitHub
        env_var = mode_map.get(mode, "SYSTEM_PROMPT_URL")
        url = os.getenv(env_var)

        if not url:
            return f"System Error: URL for mode {mode} not found in environment and local file missing."

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
