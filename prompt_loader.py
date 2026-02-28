import json
import os
from pathlib import Path

class PromptLoader:
    def __init__(self, gh_token):
        self.gh_token = gh_token
        self.base_dir = Path(__file__).parent
        self.catalog = self._load_catalog()

    def _load_catalog(self):
        catalog_path = self.base_dir / "prompts" / "catalog.json"
        if catalog_path.exists():
            with open(catalog_path, "r") as f:
                data = json.load(f)
                return {item["id"]: item for item in data.get("prompts", [])}
        return {}

    async def get_system_prompt(self, mode: str, mode_map: dict):
        """
        Возвращает системный промпт для указанного режима.
        Если промпт не найден локально, возвращает заглушку.
        Никаких запросов к GitHub не производится.
        """
        # mode_map: например {"01_CORE": "01-core-prompt"}
        prompt_id = mode_map.get(mode)
        if not prompt_id:
            return f"[Mode '{mode}' not implemented]"

        # Ищем в каталоге
        entry = self.catalog.get(prompt_id)
        if not entry:
            return f"[Prompt '{prompt_id}' not found in catalog]"

        file_path = self.base_dir / entry["file"]
        if not file_path.exists():
            return f"[Prompt file {file_path} not found]"

        try:
            return file_path.read_text().strip()
        except Exception as e:
            return f"[Error reading prompt file: {e}]"
