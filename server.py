from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from logic import MrakOrchestrator
import os

app = FastAPI()
orch = MrakOrchestrator()

@app.post("/api/analyze")
async def analyze(request: Request):
    data = await request.json()
    mode = data.get("mode", "01_CORE")
    sys_prompt = await orch.get_system_prompt(mode)
    return StreamingResponse(
        orch.stream_analysis(data['prompt'], sys_prompt), 
        media_type="text/plain"
    )

app.mount("/", StaticFiles(directory=".", html=True), name="static")