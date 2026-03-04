"""
Глобальные зависимости для внедрения в роутеры.
"""
from artifact_service import ArtifactService
from use_cases.execute_node import ExecuteNodeUseCase

_artifact_service: ArtifactService = None
_execute_use_case: ExecuteNodeUseCase = None

def init_dependencies(artifact_service: ArtifactService):
    global _artifact_service, _execute_use_case
    _artifact_service = artifact_service
    _execute_use_case = ExecuteNodeUseCase(_artifact_service)

def get_artifact_service() -> ArtifactService:
    if _artifact_service is None:
        raise RuntimeError("ArtifactService not initialized")
    return _artifact_service

def get_execute_use_case() -> ExecuteNodeUseCase:
    if _execute_use_case is None:
        raise RuntimeError("ExecuteNodeUseCase not initialized")
    return _execute_use_case
