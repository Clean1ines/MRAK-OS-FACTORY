# CHANGED: Use services directly, remove orchestrator
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
import logging
from services import prompt_service, llm_stream_service

logger = logging.getLogger("MRAK-SERVER")

router = APIRouter(prefix="/api", tags=["modes"])

@router.get("/models")
async def get_models():
    models = prompt_service.groq_client.get_active_models()
    return JSONResponse(content=models)

@router.get("/modes")
async def get_available_modes():
    return [
        {"id": "01_CORE", "name": "01: CORE_SYSTEM", "default": True},
        {"id": "02_IDEA_CLARIFIER", "name": "02: IDEA_CLARIFIER"},
        {"id": "03_PRODUCT_COUNCIL", "name": "03: PRODUCT_COUNCIL"},
        {"id": "04_BUSINESS_REQ_GEN", "name": "04: BUSINESS_REQ_GEN"},
        {"id": "05_REQ_ENG_COUNCIL", "name": "05: REQ_ENG_COUNCIL"},
        {"id": "06_SYSTEM_REQ_GEN", "name": "06: SYSTEM_REQ_GEN"},
        {"id": "07_QA_COUNCIL", "name": "07: QA_COUNCIL"},
        {"id": "08_ARCHITECTURE_COUNCIL", "name": "08: ARCHITECTURE_COUNCIL"},
        {"id": "09_CODE_TASK_GEN", "name": "09: CODE_TASK_GEN"},
        {"id": "10_CODE_GEN", "name": "10: CODE_GEN"},
        {"id": "11_TEST_GEN", "name": "11: TEST_GEN"},
        {"id": "12_FAILURE_DETECTOR", "name": "12: FAILURE_DETECTOR"},
        {"id": "13_SELF_ANALYSIS_FACTORY", "name": "13: SELF_ANALYSIS_FACTORY"},
        {"id": "14_PROMPT_ENGINEERING_COUNCIL", "name": "14: PROMPT_ENGINEERING_COUNCIL"},
        {"id": "15_ALGORITHM_COUNCIL", "name": "15: ALGORITHM_COUNCIL"},
        {"id": "16_UI_UX_COUNCIL", "name": "16: UI_UX_COUNCIL"},
        {"id": "17_SOFT_ENG_COUNCIL", "name": "17: SOFT_ENG_COUNCIL"},
        {"id": "18_TRANSLATOR", "name": "18: TRANSLATOR"},
        {"id": "19_INTEGRATION_PLAN", "name": "19: INTEGRATION_PLAN"},
        {"id": "20_SECURITY_REQ_GEN", "name": "20: SECURITY_REQ_GEN"},
        {"id": "21_THREAT_MODELING_ASSISTANT", "name": "21: THREAT_MODELING_ASSISTANT"},
        {"id": "22_INFRASTRUCTURE_SPEC_GEN", "name": "22: INFRASTRUCTURE_SPEC_GEN"},
        {"id": "23_OBSERVABILITY_SPEC_GEN", "name": "23: OBSERVABILITY_SPEC_GEN"},
        {"id": "24_TECH_DESIGN_DOC_GEN", "name": "24: TECH_DESIGN_DOC_GEN"},
        {"id": "25_USER_DOC_GEN", "name": "25: USER_DOC_GEN"},
        {"id": "26_API_DOC_GEN", "name": "26: API_DOC_GEN"},
        {"id": "27_UAT_SCRIPT_GEN", "name": "27: UAT_SCRIPT_GEN"},
        {"id": "28_JIRA_ISSUE_FORMATTER", "name": "28: JIRA_ISSUE_FORMATTER"},
        {"id": "29_PROJECT_STATUS_REPORTER", "name": "29: PROJECT_STATUS_REPORTER"},
        {"id": "30_INCIDENT_POST_MORTEM_GEN", "name": "30: INCIDENT_POST_MORTEM_GEN"},
        {"id": "31_KNOWLEDGE_QUERY_ASSISTANT", "name": "31: KNOWLEDGE_QUERY_ASSISTANT"},
        {"id": "32_CHANGE_IMPACT_ANALYZER", "name": "32: CHANGE_IMPACT_ANALYZER"},
        {"id": "33_FEATURE_TO_USER_STORY_GEN", "name": "33: FEATURE_TO_USER_STORY_GEN"},
        {"id": "34_RESEARCH_METODOLOGY_GEN", "name": "34: RESEARCH_METODOLOGY_GEN"},
        {"id": "35_ANALYSIS_SUMMARIZER", "name": "35: ANALYSIS_SUMMARIZER"},
        {"id": "36_REQUIREMENT_SUMMARIZER", "name": "36: REQUIREMENT_SUMMARIZER"},
        {"id": "37_SYSTEM_REQUIREMENTS_SUMMARIZER", "name": "37: SYSTEM_REQUIREMENTS_SUMMARIZER"},
        {"id": "38_CODE_CONTEXT_SUMMARIZER", "name": "38: CODE_CONTEXT_SUMMARIZER"},
        {"id": "02sum_STATE_SYNTHESIZER", "name": "02sum: STATE_SYNTHESIZER"},
    ]

@router.post("/analyze")
async def analyze(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON received: {e}")
        return JSONResponse(content={"error": "Invalid JSON body"}, status_code=400)

    prompt = data.get("prompt")
    mode = data.get("mode", "01_CORE")
    model = data.get("model")
    project_id = data.get("project_id")

    if not prompt:
        return JSONResponse(content={"error": "Prompt is required"}, status_code=400)

    if not model:
        model = "llama-3.3-70b-versatile"

    sys_prompt = await prompt_service.get_system_prompt(mode)

    if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
        logger.error(f"Prompt fetch failed for mode {mode}: {sys_prompt}")
        async def error_stream():
            yield f"🔴 **SYSTEM_CRITICAL_ERROR**: {sys_prompt}\n"
            yield "Check your .env (GITHUB_TOKEN) and repository URLs."
        return StreamingResponse(error_stream(), media_type="text/plain")

    logger.info(f"Starting stream: Mode={mode}, Model={model}, Project={project_id}")

    return StreamingResponse(
        llm_stream_service.stream_analysis(prompt, sys_prompt, model, mode, project_id=project_id),
        media_type="text/plain",
    )
