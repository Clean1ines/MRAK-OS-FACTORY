"""
Репозиторий для работы с воркфлоу, узлами и рёбрами.
Все функции поддерживают транзакции через параметр tx.
"""
import json
import logging
import uuid
from typing import Optional, Dict, Any, List

from .base import get_connection

logger = logging.getLogger(__name__)

# ==================== WORKFLOWS ==================== #

async def create_workflow(
    name: str,
    project_id: str,
    description: str = "",
    is_default: bool = False,
    tx=None
) -> str:
    """Создаёт новую запись воркфлоу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        workflow_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO workflows (id, name, description, is_default, project_id)
            VALUES ($1, $2, $3, $4, $5)
        ''', workflow_id, name, description, is_default, project_id)
        logger.info("Created workflow %s for project %s", workflow_id, project_id)
        return workflow_id
    finally:
        if close_conn:
            await conn.close()

async def get_workflow(workflow_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """Возвращает воркфлоу по ID или None."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM workflows WHERE id = $1', workflow_id)
        if row:
            wf = dict(row)
            wf['id'] = str(wf['id'])
            wf['project_id'] = str(wf['project_id']) if wf['project_id'] else None
            wf['created_at'] = wf['created_at'].isoformat() if wf['created_at'] else None
            wf['updated_at'] = wf['updated_at'].isoformat() if wf['updated_at'] else None
            return wf
        logger.debug("Workflow %s not found", workflow_id)
        return None
    finally:
        if close_conn:
            await conn.close()

async def list_workflows(project_id: Optional[str] = None, tx=None) -> List[Dict[str, Any]]:
    """Возвращает список воркфлоу. Если project_id передан, фильтрует по нему."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        if project_id:
            rows = await conn.fetch(
                'SELECT * FROM workflows WHERE project_id = $1 ORDER BY is_default DESC, name',
                project_id
            )
        else:
            rows = await conn.fetch('SELECT * FROM workflows ORDER BY is_default DESC, name')
        workflows = []
        for row in rows:
            wf = dict(row)
            wf['id'] = str(wf['id'])
            wf['project_id'] = str(wf['project_id']) if wf['project_id'] else None
            wf['created_at'] = wf['created_at'].isoformat() if wf['created_at'] else None
            wf['updated_at'] = wf['updated_at'].isoformat() if wf['updated_at'] else None
            workflows.append(wf)
        logger.debug("Found %d workflows for project %s", len(workflows), project_id)
        return workflows
    finally:
        if close_conn:
            await conn.close()

async def update_workflow(
    workflow_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_default: Optional[bool] = None,
    tx=None
) -> None:
    """Обновляет поля воркфлоу (только переданные параметры)."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        set_clauses = []
        values = []
        idx = 1
        if name is not None:
            set_clauses.append(f"name = ${idx}")
            values.append(name)
            idx += 1
        if description is not None:
            set_clauses.append(f"description = ${idx}")
            values.append(description)
            idx += 1
        if is_default is not None:
            set_clauses.append(f"is_default = ${idx}")
            values.append(is_default)
            idx += 1
        if not set_clauses:
            return
        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE workflows SET {', '.join(set_clauses)} WHERE id = ${idx}"
        values.append(workflow_id)
        await conn.execute(query, *values)
        logger.info("Updated workflow %s with %s", workflow_id, {k: v for k, v in locals().items() if k in ('name', 'description', 'is_default') and v is not None})
    finally:
        if close_conn:
            await conn.close()

async def delete_workflow(workflow_id: str, tx=None) -> None:
    """Удаляет воркфлоу (каскадно удалятся узлы и рёбра)."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM workflows WHERE id = $1', workflow_id)
        logger.info("Deleted workflow %s", workflow_id)
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
    tx=None
) -> str:
    """Создаёт новый узел воркфлоу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        record_id = str(uuid.uuid4())
        config_json = json.dumps(config)
        await conn.execute('''
            INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''', record_id, workflow_id, node_id, prompt_key, config_json, position_x, position_y)
        logger.info("Created node %s (record %s) in workflow %s", node_id, record_id, workflow_id)
        return record_id
    except Exception as e:
        logger.error("Error creating node %s: %s", node_id, e, exc_info=True)
        raise
    finally:
        if close_conn:
            await conn.close()

async def get_workflow_nodes(workflow_id: str, tx=None) -> List[Dict[str, Any]]:
    """Возвращает все узлы указанного воркфлоу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
        logger.debug("Retrieved %d nodes for workflow %s", len(nodes), workflow_id)
        return nodes
    finally:
        if close_conn:
            await conn.close()

async def get_workflow_node_by_id(node_record_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """Возвращает узел по его первичному ключу (id из workflow_nodes)."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow('SELECT * FROM workflow_nodes WHERE id = $1', node_record_id)
        if row:
            node = dict(row)
            node['config'] = json.loads(node['config']) if node['config'] else {}
            return node
        logger.debug("Node record %s not found", node_record_id)
        return None
    finally:
        if close_conn:
            await conn.close()

async def update_workflow_node(
    node_record_id: str,
    prompt_key: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    position_x: Optional[float] = None,
    position_y: Optional[float] = None,
    tx=None
) -> None:
    """Обновляет поля узла по его первичному ключу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        set_clauses = []
        values = []
        idx = 1
        if prompt_key is not None:
            set_clauses.append(f"prompt_key = ${idx}")
            values.append(prompt_key)
            idx += 1
        if config is not None:
            set_clauses.append(f"config = ${idx}")
            values.append(json.dumps(config))
            idx += 1
        if position_x is not None:
            set_clauses.append(f"position_x = ${idx}")
            values.append(position_x)
            idx += 1
        if position_y is not None:
            set_clauses.append(f"position_y = ${idx}")
            values.append(position_y)
            idx += 1
        if not set_clauses:
            return
        set_clauses.append("updated_at = NOW()")
        query = f"UPDATE workflow_nodes SET {', '.join(set_clauses)} WHERE id = ${idx}"
        values.append(node_record_id)
        await conn.execute(query, *values)
        logger.info("Updated node %s", node_record_id)
    finally:
        if close_conn:
            await conn.close()

async def delete_workflow_node(node_record_id: str, tx=None) -> None:
    """Удаляет узел по его первичному ключу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM workflow_nodes WHERE id = $1', node_record_id)
        logger.info("Deleted node %s", node_record_id)
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
    tx=None
) -> str:
    """Создаёт новое ребро воркфлоу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        edge_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO workflow_edges (id, workflow_id, source_node, target_node, source_output, target_input)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', edge_id, workflow_id, source_node, target_node, source_output, target_input)
        logger.info("Created edge %s from %s to %s", edge_id, source_node, target_node)
        return edge_id
    except Exception as e:
        logger.error("Error creating edge: %s", e, exc_info=True)
        raise
    finally:
        if close_conn:
            await conn.close()

async def get_workflow_edges(workflow_id: str, tx=None) -> List[Dict[str, Any]]:
    """Возвращает все рёбра указанного воркфлоу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
        logger.debug("Retrieved %d edges for workflow %s", len(edges), workflow_id)
        return edges
    finally:
        if close_conn:
            await conn.close()

async def delete_workflow_edge(edge_record_id: str, tx=None) -> None:
    """Удаляет ребро по его первичному ключу."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        await conn.execute('DELETE FROM workflow_edges WHERE id = $1', edge_record_id)
        logger.info("Deleted edge %s", edge_record_id)
    finally:
        if close_conn:
            await conn.close()

# ==================== SYNC ==================== #

async def sync_workflow_graph(workflow_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], tx) -> None:
    """
    Синхронизирует узлы и рёбра воркфлоу с переданными списками.
    Предполагается, что внешние ключи от edges к nodes настроены с ON DELETE CASCADE
    или отсутствуют, поэтому порядок операций безопасен.
    """
    logger.info("Syncing graph for workflow %s: %d nodes, %d edges", workflow_id, len(nodes), len(edges))

    # 1. Удаляем все существующие рёбра (чтобы избежать проблем с FK при удалении узлов)
    current_edges = await get_workflow_edges(workflow_id, tx=tx)
    for edge in current_edges:
        await delete_workflow_edge(edge['id'], tx=tx)

    # 2. Текущие узлы
    current_nodes = await get_workflow_nodes(workflow_id, tx=tx)
    node_map = {n['node_id']: n for n in current_nodes}

    # 3. Обработка узлов из запроса
    for node_data in nodes:
        node_id = node_data['node_id']
        if node_id in node_map:
            # Обновить существующий
            record_id = node_map[node_id]['id']
            await update_workflow_node(
                record_id,
                tx=tx,
                prompt_key=node_data['prompt_key'],
                config=node_data.get('config', {}),
                position_x=node_data['position_x'],
                position_y=node_data['position_y']
            )
            del node_map[node_id]
        else:
            # Создать новый
            await create_workflow_node(
                workflow_id,
                node_id,
                prompt_key=node_data['prompt_key'],
                config=node_data.get('config', {}),
                position_x=node_data['position_x'],
                position_y=node_data['position_y'],
                tx=tx
            )

    # 4. Удаляем узлы, оставшиеся в node_map (их нет в запросе)
    for node_record in node_map.values():
        await delete_workflow_node(node_record['id'], tx=tx)

    # 5. Вставляем новые рёбра (после того как все узлы созданы/обновлены)
    for edge_data in edges:
        await create_workflow_edge(
            workflow_id,
            source_node=edge_data['source_node'],
            target_node=edge_data['target_node'],
            source_output=edge_data.get('source_output', 'output'),
            target_input=edge_data.get('target_input', 'input'),
            tx=tx
        )

    logger.info("Graph sync completed for workflow %s", workflow_id)