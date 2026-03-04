from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import db
from repositories.base import transaction
from schemas import (
    ArtifactCreate, GenerateArtifactRequest, SavePackageRequest,
    ValidateArtifactRequest
)
from validation import ValidationError
from use_cases.generate_artifact import GenerateArtifactUseCase
from use_cases.save_artifact_package import SaveArtifactPackageUseCase
from utils.hash import compute_content_hash
from dependencies import get_artifact_service
from artifact_service import ArtifactService
import logging

logger = logging.getLogger("MRAK-SERVER")

router = APIRouter(prefix="/api", tags=["artifacts"])

# Вспомогательная функция для создания generation_config (временный костыль)
def _make_generation_config(artifact_type: str) -> dict:
    # TODO: в будущем generation_config должен браться из ноды
    return {
        "system_prompt": f"You are generating a {artifact_type}.",
        "user_prompt_template": "Context:\n{all_artifacts}\n\nUser input:\n{user_input}",
        "required_input_types": []
    }

@router.get("/projects/{project_id}/artifacts")
async def list_artifacts(project_id: str, type: Optional[str] = None):
    artifacts = await db.get_artifacts(project_id, type)
    return JSONResponse(content=artifacts)

@router.post("/artifact")
async def create_artifact(
    artifact: ArtifactCreate,
    artifact_service: ArtifactService = Depends(get_artifact_service)
):
    try:
        if artifact.generate:
            input_artifacts = []
            if artifact.parent_id:
                async with transaction() as tx:
                    parent = await db.get_artifact(artifact.parent_id, tx=tx)
                    if not parent:
                        return JSONResponse(content={"error": "Parent artifact not found"}, status_code=404)
                    input_artifacts = [parent]

            generation_config = _make_generation_config(artifact.artifact_type)

            new_id = await artifact_service.generate_artifact(
                artifact_type=artifact.artifact_type,
                input_artifacts=input_artifacts,
                user_input=artifact.content,
                model_id=artifact.model,
                project_id=artifact.project_id,
                generation_config=generation_config
            )
            return JSONResponse(content={"id": new_id, "generated": True})
        else:
            content_data = {"text": artifact.content}
            async with transaction() as tx:
                new_id = await db.save_artifact(
                    artifact_type=artifact.artifact_type,
                    content=content_data,
                    owner="user",
                    status="DRAFT",
                    project_id=artifact.project_id,
                    parent_id=artifact.parent_id,
                    tx=tx
                )
            return JSONResponse(content={"id": new_id, "generated": False})
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=422)
    except Exception as e:
        logger.error(f"Error creating artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/latest_artifact")
async def latest_artifact(parent_id: str, type: str):
    pkg = await db.get_last_version_by_parent_and_type(parent_id, type)
    if pkg:
        return JSONResponse(content={
            "exists": True,
            "artifact_id": pkg['id'],
            "content": pkg['content']
        })
    else:
        return JSONResponse(content={"exists": False})

@router.post("/validate_artifact")
async def validate_artifact(req: ValidateArtifactRequest):
    try:
        async with transaction() as tx:
            await db.update_artifact_status(req.artifact_id, req.status, tx=tx)
        return JSONResponse(content={"status": "updated"})
    except Exception as e:
        logger.error(f"Error validating artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.delete("/artifact/{artifact_id}")
async def delete_artifact_endpoint(artifact_id: str):
    try:
        async with transaction() as tx:
            await db.delete_artifact(artifact_id, tx=tx)
        return JSONResponse(content={"status": "deleted"})
    except Exception as e:
        logger.error(f"Error deleting artifact: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/generate_artifact")
async def generate_artifact_endpoint(
    req: GenerateArtifactRequest,
    artifact_service: ArtifactService = Depends(get_artifact_service)
):
    try:
        input_artifacts = []
        if req.parent_id:
            async with transaction() as tx:
                parent = await db.get_artifact(req.parent_id, tx=tx)
                if parent:
                    input_artifacts = [parent]
        generation_config = _make_generation_config(req.artifact_type)
        new_id = await artifact_service.generate_artifact(
            artifact_type=req.artifact_type,
            input_artifacts=input_artifacts,
            user_input=req.feedback,
            model_id=req.model,
            project_id=req.project_id,
            generation_config=generation_config
        )
        async with transaction() as tx:
            artifact = await db.get_artifact(new_id, tx=tx)
        if artifact:
            return JSONResponse(content={"result": artifact['content']})
        else:
            return JSONResponse(content={"result": {"id": new_id}})
    except ValidationError as e:
        return JSONResponse(content={"error": str(e)}, status_code=422)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/save_artifact_package")
async def save_artifact_package(req: SavePackageRequest):
    use_case = SaveArtifactPackageUseCase()
    try:
        result = await use_case.execute(req)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error saving package: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/projects/{project_id}/messages")
async def get_project_messages(project_id: str):
    artifacts = await db.get_artifacts(project_id, artifact_type="LLMResponse")
    artifacts.sort(key=lambda x: x['created_at'])
    return JSONResponse(content=artifacts)

# ==================== ТИПЫ АРТЕФАКТОВ (без изменений) ====================
@router.get("/artifact-types")
async def list_artifact_types():
    async with transaction() as tx:
        rows = await tx.fetch("SELECT * FROM artifact_types ORDER BY type")
    types = []
    for row in rows:
        types.append({
            "type": row["type"],
            "schema": row["schema"],
            "allowed_parents": row["allowed_parents"],
            "requires_clarification": row["requires_clarification"],
            "icon": row["icon"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        })
    return JSONResponse(content=types)

@router.get("/artifact-types/{type}")
async def get_artifact_type(type: str):
    t = await db.get_artifact_type(type)
    if not t:
        return JSONResponse(content={"error": "Type not found"}, status_code=404)
    return JSONResponse(content=t)

@router.post("/artifact-types", status_code=201)
async def create_artifact_type_endpoint(req: dict):
    required = ["type", "schema"]
    for field in required:
        if field not in req:
            return JSONResponse(content={"error": f"Missing field {field}"}, status_code=400)
    async with transaction() as tx:
        await db.create_artifact_type(
            type=req["type"],
            schema=req["schema"],
            allowed_parents=req.get("allowed_parents", []),
            requires_clarification=req.get("requires_clarification", False),
            icon=req.get("icon"),
            tx=tx
        )
    return JSONResponse(content={"type": req["type"]})

@router.put("/artifact-types/{type}")
async def update_artifact_type_endpoint(type: str, req: dict):
    existing = await db.get_artifact_type(type)
    if not existing:
        return JSONResponse(content={"error": "Type not found"}, status_code=404)
    async with transaction() as tx:
        await db.update_artifact_type(type, tx=tx, **req)
    return JSONResponse(content={"status": "updated"})

@router.delete("/artifact-types/{type}")
async def delete_artifact_type_endpoint(type: str):
    existing = await db.get_artifact_type(type)
    if not existing:
        return JSONResponse(content={"error": "Type not found"}, status_code=404)
    async with transaction() as tx:
        await db.delete_artifact_type(type, tx=tx)
    return JSONResponse(content={"status": "deleted"})
