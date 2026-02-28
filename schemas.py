# schemas.py
import re
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    """Базовая схема проекта с валидацией имени."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name, 1-100 characters")
    description: str = Field(default="", description="Project description")

    @validator('name')
    def validate_name_chars(cls, v):
        """Запрещаем символы, опасные для инъекций или path traversal."""
        # Разрешены: буквы, цифры, пробел, дефис, подчёркивание, точка
        # Запрещены: / \ .. < > : ; " ' ` | ? * [ ] { } ( ) & $ # @ ! ~
        if re.search(r'[<>:"/\\|?*\[\]{}()&$#@!~`;\']', v):
            raise ValueError('Name contains forbidden characters')
        # Дополнительно проверяем на двойные точки (..) — признак path traversal
        if '..' in v:
            raise ValueError('Name cannot contain ".."')
        return v.strip()  # убираем лишние пробелы в начале/конце

class ProjectCreate(ProjectBase):
    """Схема для создания нового проекта."""
    pass

class ProjectUpdate(ProjectBase):
    """Схема для обновления проекта (PUT — все поля обязательны)."""
    # Можно оставить как есть, все поля наследуются обязательными.
    pass

class ProjectResponse(ProjectBase):
    """Схема для ответа с данными проекта."""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True  # позволяет работать с dict/row
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ArtifactCreate(BaseModel):
    project_id: str
    artifact_type: str
    content: str
    parent_id: Optional[str] = None
    generate: bool = False
    model: Optional[str] = None

class GenerateArtifactRequest(BaseModel):
    artifact_type: str
    parent_id: str
    feedback: str = ""
    model: Optional[str] = None
    project_id: str
    existing_content: Optional[Any] = None

class SavePackageRequest(BaseModel):
    project_id: str
    parent_id: str
    artifact_type: str
    content: Any

class ValidateArtifactRequest(BaseModel):
    artifact_id: str
    status: str  # "VALIDATED" или "REJECTED"

class NextStepResponse(BaseModel):
    next_stage: str
    prompt_type: str
    parent_id: Optional[str]
    description: str

class StartClarificationRequest(BaseModel):
    project_id: str
    target_artifact_type: str
    model: Optional[str] = None

class MessageRequest(BaseModel):
    message: str

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

class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    is_default: bool = False

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None

class WorkflowNodeCreate(BaseModel):
    node_id: str
    prompt_key: str
    config: Dict[str, Any] = {}
    position_x: float
    position_y: float

class WorkflowNodeUpdate(BaseModel):
    prompt_key: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None

class WorkflowEdgeCreate(BaseModel):
    source_node: str
    target_node: str
    source_output: str = "output"
    target_input: str = "input"

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    is_default: bool
    created_at: str
    updated_at: str

class WorkflowDetailResponse(BaseModel):
    workflow: WorkflowResponse
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
