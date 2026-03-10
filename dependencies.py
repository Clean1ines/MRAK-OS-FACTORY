"""
Глобальные зависимости для внедрения в роутеры.
"""
from artifact_service import ArtifactService
from use_cases.execute_node import ExecuteNodeUseCase
from prompt_loader import PromptLoader          # ADDED
from prompt_service import PromptService        # ADDED
from session_service import SessionService      # ADDED
from services.llm_stream_service import LLMStreamService # FIXED import path
from groq_client import GroqClient              # (опционально)

_artifact_service: ArtifactService = None
_execute_use_case: ExecuteNodeUseCase = None

# ADDED: новые глобальные переменные
_llm_stream_service: LLMStreamService = None
_prompt_service: PromptService = None
_session_service: SessionService = None

def init_dependencies(
    artifact_service: ArtifactService,
    prompt_service: PromptService,           # ADDED
    llm_stream_service: LLMStreamService,    # ADDED
    session_service: SessionService          # ADDED
):
    global _artifact_service, _execute_use_case
    global _prompt_service, _llm_stream_service, _session_service  # ADDED
    _artifact_service = artifact_service
    # ExecuteNodeUseCase теперь требует prompt_service и session_service
    _execute_use_case = ExecuteNodeUseCase(artifact_service, prompt_service, session_service)
    _prompt_service = prompt_service
    _llm_stream_service = llm_stream_service
    _session_service = session_service

def get_artifact_service() -> ArtifactService:
    if _artifact_service is None:
        raise RuntimeError("ArtifactService not initialized")
    return _artifact_service

def get_execute_use_case() -> ExecuteNodeUseCase:
    if _execute_use_case is None:
        raise RuntimeError("ExecuteNodeUseCase not initialized")
    return _execute_use_case

# ADDED: новые геттеры
def get_llm_stream_service() -> LLMStreamService:
    if _llm_stream_service is None:
        raise RuntimeError("LLMStreamService not initialized")
    return _llm_stream_service

def get_prompt_service() -> PromptService:
    if _prompt_service is None:
        raise RuntimeError("PromptService not initialized")
    return _prompt_service

def get_session_service() -> SessionService:
    if _session_service is None:
        raise RuntimeError("SessionService not initialized")
    return _session_service