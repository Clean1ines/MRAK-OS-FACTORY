from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from logic import MrakOrchestrator
import logging

# Настройка базового логирования для мониторинга в Render/Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MRAK-SERVER")

app = FastAPI(title="MRAK-OS Factory API")
orch = MrakOrchestrator()


@app.get("/api/models")
async def get_models():
    """Возвращает список доступных нейросетевых моделей."""
    models = orch.get_active_models()
    return JSONResponse(content=models)


@app.post("/api/analyze")
async def analyze(request: Request):
    """
    Основной эндпоинт для потоковой обработки запросов.
    Поддерживает динамическую смену системных промптов через GitHub.
    """
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON received: {e}")
        return JSONResponse(content={"error": "Invalid JSON body"}, status_code=400)

    prompt = data.get("prompt")
    mode = data.get("mode", "01_CORE")
    model = data.get("model")

    if not prompt:
        return JSONResponse(content={"error": "Prompt is required"}, status_code=400)

    if not model:
        # Fallback на модель по умолчанию, если фронтенд не прислал ID
        model = "llama-3.3-70b-versatile"

    # Асинхронная подгрузка промпта из GitHub репозитория
    sys_prompt = await orch.get_system_prompt(mode)

    # Проверка на системные ошибки (отсутствие токена, 404 на GitHub и т.д.)
    if sys_prompt.startswith("System Error") or sys_prompt.startswith("Error"):
        logger.error(f"Prompt fetch failed for mode {mode}: {sys_prompt}")

        async def error_stream():
            yield f"🔴 **SYSTEM_CRITICAL_ERROR**: {sys_prompt}\n"
            yield "Check your .env (GITHUB_TOKEN) and repository URLs."

        return StreamingResponse(error_stream(), media_type="text/plain")

    logger.info(f"Starting stream: Mode={mode}, Model={model}")

    return StreamingResponse(
        orch.stream_analysis(prompt, sys_prompt, model),
        media_type="text/plain",
    )


# StaticFiles монтируется последним. 
# directory="." означает, что index.html ищется в корне проекта.
app.mount("/", StaticFiles(directory=".", html=True), name="static")