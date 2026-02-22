# CHANGED: Added missing json import
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import json  # ADDED
from schemas import StartClarificationRequest, MessageRequest, ClarificationSessionResponse
from orchestrator import MrakOrchestrator
from session_service import SessionService
from use_cases.start_clarification import StartClarificationUseCase
from use_cases.add_message import AddMessageUseCase
import logging

logger = logging.getLogger("MRAK-SERVER")
orch = MrakOrchestrator()
session_service = SessionService()

router = APIRouter(prefix="/api", tags=["clarification"])

@router.post("/clarification/start", response_model=ClarificationSessionResponse)
async def start_clarification(req: StartClarificationRequest):
    use_case = StartClarificationUseCase(orch, session_service)
    try:
        result = await use_case.execute(req)
        return result
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=404)
    except RuntimeError as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/clarification/{session_id}/message", response_model=ClarificationSessionResponse)
async def add_message(session_id: str, req: MessageRequest):
    use_case = AddMessageUseCase(orch, session_service)
    try:
        result = await use_case.execute(session_id, req)
        return result
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=404 if "not found" in str(e) else 400)
    except RuntimeError as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/clarification/{session_id}", response_model=ClarificationSessionResponse)
async def get_clarification_session_endpoint(session_id: str):
    session = await session_service.get_clarification_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)
    return ClarificationSessionResponse(
        id=session['id'],
        project_id=session['project_id'],
        target_artifact_type=session['target_artifact_type'],
        history=session['history'],
        status=session['status'],
        context_summary=json.loads(session['context_summary']) if session.get('context_summary') else None,
        final_artifact_id=session.get('final_artifact_id'),
        created_at=session['created_at'],
        updated_at=session['updated_at']
    )

@router.post("/clarification/{session_id}/complete")
async def complete_clarification_session(session_id: str):
    session = await session_service.get_clarification_session(session_id)
    if not session:
        return JSONResponse(content={"error": "Session not found"}, status_code=404)
    if session['status'] != 'active':
        return JSONResponse(content={"error": "Session already completed"}, status_code=400)

    await session_service.update_clarification_session(session_id, status="completed")
    return JSONResponse(content={"status": "completed", "session_id": session_id})

@router.get("/projects/{project_id}/clarification/active")
async def get_active_sessions(project_id: str):
    sessions = await session_service.list_active_sessions_for_project(project_id)
    return JSONResponse(content=[
        {
            "id": s['id'],
            "target_artifact_type": s['target_artifact_type'],
            "created_at": s['created_at'],
            "updated_at": s['updated_at']
        }
        for s in sessions
    ])
