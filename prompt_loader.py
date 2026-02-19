import os
import httpx

class PromptLoader:
    def __init__(self, gh_token):
        self.gh_token = gh_token

    async def get_system_prompt(self, mode: str, mode_map: dict):
        if mode == "07_BYPASS":
            return "You are a helpful assistant."

        env_var = mode_map.get(mode, "SYSTEM_PROMPT_URL")
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
