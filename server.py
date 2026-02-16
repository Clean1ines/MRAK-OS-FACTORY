from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from logic import MrakOrchestrator
import os

app = FastAPI()
orch = MrakOrchestrator()


@app.get("/api/models")
async def get_models():
    return JSONResponse(content=orch.get_active_models())


@app.post("/api/analyze")
async def analyze(request: Request):
    data = await request.json()
    prompt = data.get("prompt")
    mode = data.get("mode", "01_CORE")
    model = data.get("model")

    if not prompt:
        return JSONResponse(content={"error": "Empty prompt"}, status_code=400)

    sys_prompt = await orch.get_system_prompt(mode)

    return StreamingResponse(
        orch.stream_analysis(prompt, sys_prompt, model), media_type="text/plain"
    )


app.mount("/", StaticFiles(directory=".", html=True), name="static")
