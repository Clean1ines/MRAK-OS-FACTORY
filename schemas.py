# ADDED: Pydantic models shared between server and routers
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

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
