# ADDED: Workflow repository
import json
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

# ==================== WORKFLOWS ==================== #

async def create_workflow(name: str, description: str = "", is_default: bool = False, conn=None) -> str:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        workflow_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO workflows (id, name, description, is_default)
            VALUES ($1, $2, $3, $4)
        ''', workflow_id, name, description, is_default)
        return workflow_id
    finally:
        if close_conn:
            await conn.close()

async def get_workflow(workflow_id: str, conn=None) -> Optional[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM workflows WHERE id = $1', workflow_id)
        if row:
            wf = dict(row)
            wf['id'] = str(wf['id'])
            wf['created_at'] = wf['created_at'].isoformat() if wf['created_at'] else None
            wf['updated_at'] = wf['updated_at'].isoformat() if wf['updated_at'] else None
            return wf
        return None
    finally:
        if close_conn:
            await conn.close()

async def list_workflows(conn=None) -> List[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('SELECT * FROM workflows ORDER BY is_default DESC, name')
        workflows = []
        for row in rows:
            wf = dict(row)
            wf['id'] = str(wf['id'])
            wf['created_at'] = wf['created_at'].isoformat() if wf['created_at'] else None
            wf['updated_at'] = wf['updated_at'].isoformat() if wf['updated_at'] else None
            workflows.append(wf)
        return workflows
    finally:
        if close_conn:
            await conn.close()

async def update_workflow(workflow_id: str, **kwargs) -> None:
    conn = kwargs.pop('conn', None)
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        set_clauses = []
        values = []
        idx = 1
        for key, value in kwargs.items():
            if key in ('name', 'description', 'is_default'):
                set_clauses.append(f"{key} = ${idx}")
                values.append(value)
                idx += 1
        if not set_clauses:
            return
        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE workflows SET {', '.join(set_clauses)} WHERE id = ${idx}"
        values.append(workflow_id)
        await conn.execute(query, *values)
    finally:
        if close_conn:
            await conn.close()

async def delete_workflow(workflow_id: str, conn=None) -> None:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM workflows WHERE id = $1', workflow_id)
    finally:
        if close_conn:
            await conn.close()

# ==================== WORKFLOW NODES ==================== #

async def create_workflow_node(
    workflow_id: str,
    node_id: str,
    prompt_key: str,
    config: Dict[str, Any],
    position_x: float,
    position_y: float,
    conn=None
) -> str:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        record_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''', record_id, workflow_id, node_id, prompt_key, json.dumps(config), position_x, position_y)
        return record_id
    finally:
        if close_conn:
            await conn.close()

async def get_workflow_nodes(workflow_id: str, conn=None) -> List[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('SELECT * FROM workflow_nodes WHERE workflow_id = $1', workflow_id)
        nodes = []
        for row in rows:
            node = dict(row)
            node['id'] = str(node['id'])
            node['workflow_id'] = str(node['workflow_id'])
            node['config'] = json.loads(node['config']) if node['config'] else {}
            node['created_at'] = node['created_at'].isoformat() if node['created_at'] else None
            node['updated_at'] = node['updated_at'].isoformat() if node['updated_at'] else None
            nodes.append(node)
        return nodes
    finally:
        if close_conn:
            await conn.close()

async def update_workflow_node(node_record_id: str, **kwargs) -> None:
    conn = kwargs.pop('conn', None)
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        set_clauses = []
        values = []
        idx = 1
        for key, value in kwargs.items():
            if key in ('prompt_key', 'config', 'position_x', 'position_y'):
                set_clauses.append(f"{key} = ${idx}")
                if key == 'config' and value is not None:
                    values.append(json.dumps(value))
                else:
                    values.append(value)
                idx += 1
        if not set_clauses:
            return
        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE workflow_nodes SET {', '.join(set_clauses)} WHERE id = ${idx}"
        values.append(node_record_id)
        await conn.execute(query, *values)
    finally:
        if close_conn:
            await conn.close()

async def delete_workflow_node(node_record_id: str, conn=None) -> None:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM workflow_nodes WHERE id = $1', node_record_id)
    finally:
        if close_conn:
            await conn.close()

# ==================== WORKFLOW EDGES ==================== #

async def create_workflow_edge(
    workflow_id: str,
    source_node: str,
    target_node: str,
    source_output: str = "output",
    target_input: str = "input",
    conn=None
) -> str:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        edge_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO workflow_edges (id, workflow_id, source_node, target_node, source_output, target_input)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', edge_id, workflow_id, source_node, target_node, source_output, target_input)
        return edge_id
    finally:
        if close_conn:
            await conn.close()

async def get_workflow_edges(workflow_id: str, conn=None) -> List[Dict[str, Any]]:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        rows = await conn.fetch('SELECT * FROM workflow_edges WHERE workflow_id = $1', workflow_id)
        edges = []
        for row in rows:
            edge = dict(row)
            edge['id'] = str(edge['id'])
            edge['workflow_id'] = str(edge['workflow_id'])
            edge['created_at'] = edge['created_at'].isoformat() if edge['created_at'] else None
            edges.append(edge)
        return edges
    finally:
        if close_conn:
            await conn.close()

async def delete_workflow_edge(edge_record_id: str, conn=None) -> None:
    close_conn = False
    if conn is None:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM workflow_edges WHERE id = $1', edge_record_id)
    finally:
        if close_conn:
            await conn.close()
