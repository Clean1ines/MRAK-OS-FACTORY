import httpx
from typing import Optional
from .config import API_URL, API_TOKEN

class BackendAPIClient:
    def __init__(self, base_url: str = API_URL, token: Optional[str] = API_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def _request(self, method: str, path: str, json=None):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if json is not None:
            headers["Content-Type"] = "application/json"
        url = f"{self.base_url}{path}"
        resp = await self.client.request(method, url, json=json, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def create_run(self, project_id: str, workflow_id: str) -> str:
        data = await self._request("POST", "/api/runs", json={
            "project_id": project_id,
            "workflow_id": workflow_id
        })
        return data["id"]

    async def execute_node(self, run_id: str, node_id: str, idempotency_key: str) -> str:
        data = await self._request("POST", f"/api/runs/{run_id}/nodes/{node_id}/execute", json={
            "idempotency_key": idempotency_key,
            "parent_execution_id": None,
            "input_artifact_ids": []
        })
        return data["id"]

    async def send_message(self, execution_id: str, text: str) -> str:
        # Используем заголовок Accept: application/json, чтобы получить JSON-ответ
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = await self.client.post(
            f"{self.base_url}/api/executions/{execution_id}/messages",
            json={"message": text},
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")