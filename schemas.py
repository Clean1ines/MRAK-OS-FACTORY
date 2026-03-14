# CHANGED: Pydantic V2 migration + all models consolidated (Project, Workflow, Artifact, Run, NodeExecution, etc.)
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator

# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    """Базовая схема проекта с валидацией имени."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name, 1-100 characters")
    description: str = Field(default="", description="Project description")

    @field_validator('name')
    @classmethod
    def validate_name_chars(cls, v: str) -> str:
        """Запрещаем символы, опасные для инъекций или path traversal."""
        if re.search(r'[<>:"/\\|?*\[\]{}()&$#@!~`;\']', v):
            raise ValueError('Name contains forbidden characters')
        if '..' in v:
            raise ValueError('Name cannot contain ".."')
        return v.strip()

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

# ==================== Artifact Schemas (with versioning) ====================

class ArtifactCreate(BaseModel):
    project_id: str
    artifact_type: str
    content: str
    parent_id: Optional[str] = None
    generate: bool = False
    model: Optional[str] = None
    logical_key: Optional[str] = Field(None, description="Логический ключ для версионирования (например, ADR-007)")

class GenerateArtifactRequest(BaseModel):
    artifact_type: str
    parent_id: Optional[str] = None
    feedback: str = ""
    model: Optional[str] = None
    project_id: str
    existing_content: Optional[Any] = None
    logical_key: Optional[str] = Field(None, description="Логический ключ для версионирования")

class SavePackageRequest(BaseModel):
    project_id: str
    parent_id: Optional[str] = None
    artifact_type: str
    content: Any
    logical_key: Optional[str] = Field(None, description="Логический ключ для версионирования")

class ValidateArtifactRequest(BaseModel):
    artifact_id: str
    status: str  # "VALIDATED" или "REJECTED"

# ==================== Workflow / NextStep (simple mode, kept for compatibility) ====================

class NextStepResponse(BaseModel):
    next_stage: str
    prompt_type: str
    parent_id: Optional[str]
    description: str

# ==================== Workflow Models ====================

class WorkflowNodeCreate(BaseModel):
    node_id: str
    prompt_key: str
    config: Dict[str, Any] = {}
    position_x: float
    position_y: float
    # ADDED for dialogue support: optional field, if not provided, DB default (false) will be used
    requires_dialogue: Optional[bool] = Field(None, description="Whether this node requires dialogue")

class WorkflowEdgeCreate(BaseModel):
    source_node: str
    target_node: str
    source_output: str = "output"
    target_input: str = "input"

class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    is_default: bool = False
    project_id: str
    nodes: List[WorkflowNodeCreate] = Field(default_factory=list)
    edges: List[WorkflowEdgeCreate] = Field(default_factory=list)

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    nodes: Optional[List[WorkflowNodeCreate]] = None
    edges: Optional[List[WorkflowEdgeCreate]] = None

class WorkflowNodeUpdate(BaseModel):
    prompt_key: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    is_default: bool
    project_id: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

class WorkflowDetailResponse(BaseModel):
    workflow: WorkflowResponse
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

# ==================== Clarification Models (temporarily disabled) ====================

class StartClarificationRequest(BaseModel):
    project_id: str
    target_artifact_type: str
    model: Optional[str] = None

class MessageRequest(BaseModel):
    message: str
    # FIX: add optional model field to match frontend payload
    model: Optional[str] = None

class ClarificationSessionResponse(BaseModel):
    id: str
    project_id: str
    target_artifact_type: str
    history: List[Dict[str, Any]]
    status: str
    context_summary: Optional[Dict[str, Any]] = None
    final_artifact_id: Optional[str] = None
    created_at: str
    updated_at: str


# ==================== Telegram / Manager Schemas ====================

class TelegramRegisterRequest(BaseModel):
    chat_id: int
    email: str
    project_id: str


class ManagerReplyRequest(BaseModel):
    message: str

# ==================== Run & NodeExecution Models (ADR-001) ====================

class RunStatus(str, Enum):
    OPEN = "OPEN"
    FROZEN = "FROZEN"
    ARCHIVED = "ARCHIVED"

class NodeExecutionStatus(str, Enum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VALIDATED = "VALIDATED"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"

class RunCreate(BaseModel):
    project_id: str
    workflow_id: str
    # created_by будет добавлен автоматически из сессии

class RunResponse(BaseModel):
    id: str
    project_id: str
    workflow_id: str
    status: RunStatus
    created_at: datetime
    created_by: Optional[str] = None
    frozen_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

class NodeExecutionCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=255)
    parent_execution_id: Optional[str] = None
    input_artifact_ids: Optional[List[str]] = None

# в schemas.py, класс NodeExecutionResponse
class NodeExecutionResponse(BaseModel):
    id: str
    run_id: str
    node_definition_id: str
    parent_execution_id: Optional[str] = None
    status: NodeExecutionStatus
    input_artifact_ids: Optional[List[str]] = None
    output_artifact_id: Optional[str] = None
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    # Новые поля (опционально)
    attempt: Optional[int] = Field(None, description="Номер попытки выполнения")
    max_attempts: Optional[int] = Field(None, description="Максимальное количество попыток")
    base_idempotency_key: Optional[str] = Field(None, description="Базовый ключ идемпотентности (без суффикса попытки)")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )

# ==================== Execute Step Request (ADR-003) ====================
class ExecuteStepRequest(BaseModel):
    """Запрос на выполнение шага воркфлоу с поддержкой Run и идемпотентности."""
    node_id: str
    run_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    parent_execution_id: Optional[str] = None
    input_artifact_ids: Optional[List[str]] = Field(default_factory=list)
    feedback: str = ""
    model: Optional[str] = None

# ==================== Validation Response (ADR-004) ====================
class ValidateExecutionResponse(BaseModel):
    id: str
    status: NodeExecutionStatus
    superseded_id: Optional[str] = None
    previous_active_id: Optional[str] = None
    next_execution_id: Optional[str] = Field(None, description="ID of the next execution automatically started")