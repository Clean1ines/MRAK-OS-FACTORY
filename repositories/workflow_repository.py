# CHANGED: Remove conn, add optional tx; handle connection
# ADDED: sync_workflow_graph для синхронизации узлов и рёбер
# CHANGED: Добавлен project_id в create_workflow и фильтрация в list_workflows
# FIXED: Порядок аргументов в create_workflow (project_id сделан обязательным и перенесён перед необязательными)
# FIXED: Преобразование UUID project_id в строку в get_workflow и list_workflows
# ADDED: Подробное логирование через print для отладки проблемы с сохранением узлов
import json
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

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
        print(f"✅ [create_workflow] Created workflow {workflow_id} for project {project_id}")
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
            print(f"✅ [get_workflow] Found workflow {workflow_id}")
            return wf
        print(f"❌ [get_workflow] Workflow {workflow_id} not found")
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
        print(f"✅ [list_workflows] Found {len(workflows)} workflows for project {project_id}")
        return workflows
    finally:
        if close_conn:
            await conn.close()

async def update_workflow(workflow_id: str, tx=None, **kwargs) -> None:
    """Обновляет поля воркфлоу (name, description, is_default)."""
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
        print(f"✅ [update_workflow] Updated workflow {workflow_id} with {kwargs}")
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
        print(f"✅ [delete_workflow] Deleted workflow {workflow_id}")
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
        print(f"✅ [create_workflow_node] Created node {node_id} with record_id {record_id} in workflow {workflow_id}")
        return record_id
    except Exception as e:
        print(f"❌ [create_workflow_node] Error creating node {node_id}: {e}")
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
        print(f"✅ [get_workflow_nodes] Retrieved {len(nodes)} nodes for workflow {workflow_id}")
        return nodes
    finally:
        if close_conn:
            await conn.close()

async def update_workflow_node(node_record_id: str, tx=None, **kwargs) -> None:
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
        print(f"✅ [update_workflow_node] Updated node {node_record_id} with {kwargs}")
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
        print(f"✅ [delete_workflow_node] Deleted node {node_record_id}")
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
        print(f"✅ [create_workflow_edge] Created edge {edge_id} from {source_node} to {target_node}")
        return edge_id
    except Exception as e:
        print(f"❌ [create_workflow_edge] Error creating edge: {e}")
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
        print(f"✅ [get_workflow_edges] Retrieved {len(edges)} edges for workflow {workflow_id}")
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
        print(f"✅ [delete_workflow_edge] Deleted edge {edge_record_id}")
    finally:
        if close_conn:
            await conn.close()

# ==================== SYNC ==================== #

async def sync_workflow_graph(workflow_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], tx) -> None:
    """Синхронизирует узлы и рёбра воркфлоу с переданными списками."""
    print(f"🔵 [sync_workflow_graph] START for workflow {workflow_id}")
    print(f"    nodes received: {len(nodes)}")
    print(f"    edges received: {len(edges)}")

    # 1. Текущие узлы
    current_nodes = await get_workflow_nodes(workflow_id, tx=tx)
    print(f"    current nodes in DB: {len(current_nodes)}")
    node_map = {n['node_id']: n for n in current_nodes}
    print(f"    node_map keys: {list(node_map.keys())}")

    # 2. Обработка узлов из запроса
    for node_data in nodes:
        node_id = node_data['node_id']
        print(f"    processing node {node_id}")
        if node_id in node_map:
            print(f"      -> updating existing node")
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
            print(f"      -> creating new node")
            await create_workflow_node(
                workflow_id,
                node_id,
                prompt_key=node_data['prompt_key'],
                config=node_data.get('config', {}),
                position_x=node_data['position_x'],
                position_y=node_data['position_y'],
                tx=tx
            )

    # 3. Удаляем узлы, оставшиеся в node_map
    if node_map:
        print(f"    nodes to delete (not in request): {list(node_map.keys())}")
        for node_record in node_map.values():
            print(f"      deleting node {node_record['node_id']} (record {node_record['id']})")
            await delete_workflow_node(node_record['id'], tx=tx)

    # 4. Удаляем все существующие рёбра
    current_edges = await get_workflow_edges(workflow_id, tx=tx)
    print(f"    current edges in DB: {len(current_edges)}")
    for edge in current_edges:
        print(f"      deleting edge {edge['id']}")
        await delete_workflow_edge(edge['id'], tx=tx)

    # 5. Вставляем новые рёбра
    for edge_data in edges:
        print(f"    creating edge from {edge_data['source_node']} to {edge_data['target_node']}")
        await create_workflow_edge(
            workflow_id,
            source_node=edge_data['source_node'],
            target_node=edge_data['target_node'],
            source_output=edge_data.get('source_output', 'output'),
            target_input=edge_data.get('target_input', 'input'),
            tx=tx
        )

    print(f"🔵 [sync_workflow_graph] END for workflow {workflow_id}")
