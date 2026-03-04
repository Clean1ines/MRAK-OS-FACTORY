# services/__init__.py
import os
from dotenv import load_dotenv
from groq_client import GroqClient
from prompt_loader import PromptLoader
from prompt_service import PromptService
from services.llm_stream_service import LLMStreamService

load_dotenv()

gh_token = os.getenv("GITHUB_TOKEN")
groq_client = GroqClient()
prompt_loader = PromptLoader(gh_token)
prompt_service = PromptService(groq_client, prompt_loader, {})  # mode_map пустой для совместимости
llm_stream_service = LLMStreamService(groq_client, prompt_loader)
