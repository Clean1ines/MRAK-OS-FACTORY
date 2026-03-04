from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from typing import Optional
from repositories.base import transaction

router = APIRouter(prefix="/api", tags=["truth"])

@router.get("/projects/{project_id}/truth")
async def get_project_truth(
    project_id: str,
    as_of: Optional[datetime] = Query(None, description="Исторический срез на указанное время (ISO 8601)")
):
    """
    Возвращает текущее активное состояние архитектурных решений проекта.
    Если указан параметр as_of, возвращает состояние на указанный момент времени.
    """
    async with transaction() as tx:
        if as_of:
            # Исторический срез через оконную функцию
            rows = await tx.conn.fetch("""
                WITH ranked AS (
                    SELECT
                        ne.id AS execution_id,
                        ne.node_definition_id,
                        ne.output_artifact_id AS artifact_id,
                        ne.validated_at,
                        a.logical_key AS artifact_logical_key,
                        a.version AS artifact_version,
                        ROW_NUMBER() OVER (PARTITION BY ne.node_definition_id ORDER BY ne.validated_at DESC) AS rn
                    FROM node_executions ne
                    LEFT JOIN artifacts a ON ne.output_artifact_id = a.id
                    WHERE ne.project_id = $1
                      AND ne.validated_at <= $2
                )
                SELECT
                    ranked.execution_id,
                    ranked.node_definition_id,
                    ranked.artifact_id,
                    ranked.validated_at,
                    ranked.artifact_logical_key,
                    ranked.artifact_version,
                    wn.node_id,
                    wn.prompt_key as node_type,
                    wn.config->>'title' as node_title
                FROM ranked
                JOIN workflow_nodes wn ON ranked.node_definition_id = wn.id
                WHERE ranked.rn = 1
            """, project_id, as_of)
        else:
            # Текущее состояние из snapshot
            rows = await tx.conn.fetch("""
                SELECT
                    ts.execution_id,
                    ts.node_definition_id,
                    ts.artifact_id,
                    ts.validated_at,
                    ts.artifact_logical_key,
                    ts.artifact_version,
                    wn.node_id,
                    wn.prompt_key as node_type,
                    wn.config->>'title' as node_title
                FROM project_truth_snapshot ts
                JOIN workflow_nodes wn ON ts.node_definition_id = wn.id
                WHERE ts.project_id = $1
            """, project_id)

    result = {
        "project_id": project_id,
        "as_of": (as_of or datetime.now(timezone.utc)).isoformat().replace('+00:00', 'Z'),
        "nodes": []
    }
    for row in rows:
        node_info = {
            "node_id": str(row["node_definition_id"]),
            "node_name": row.get("node_title") or row.get("node_id"),
            "node_type": row.get("node_type", "unknown"),
            "execution_id": str(row["execution_id"]),
            "validated_at": row["validated_at"].isoformat(),
            "artifact": {
                "id": str(row["artifact_id"]),
                "logical_key": row["artifact_logical_key"],
                "version": row["artifact_version"],
                "status": "ACTIVE"
            }
        }
        result["nodes"].append(node_info)
    return JSONResponse(content=result)