# CHANGED: Remove conn, add optional tx; handle connection
# ADDED: sync_workflow_graph для синхронизации узлов и рёбер
import json
import uuid
from typing import Optional, Dict, Any, List
from .base import get_connection

# ==================== WORKFLOWS ==================== #

async def create_workflow(name: str, description: str = "", is_default: bool = False, tx=None) -> str:
    """Создаёт новую запись воркфлоу.

    Args:
        name: Название воркфлоу.
        description: Описание.
        is_default: Флаг воркфлоу по умолчанию.
        tx: Опциональный объект транзакции.

    Returns:
        Сгенерированный UUID воркфлоу.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
            wf['created_at'] = wf['created_at'].isoformat() if wf['created_at'] else None
            wf['updated_at'] = wf['updated_at'].isoformat() if wf['updated_at'] else None
            return wf
        return None
    finally:
        if close_conn:
            await conn.close()

async def list_workflows(tx=None) -> List[Dict[str, Any]]:
    """Возвращает список всех воркфлоу, отсортированный по is_default и имени."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
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
        await conn.execute('''
            INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        ''', record_id, workflow_id, node_id, prompt_key, json.dumps(config), position_x, position_y)
        return record_id
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
        return edge_id
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
    finally:
        if close_conn:
            await conn.close()

# ==================== SYNC ==================== #

async def sync_workflow_graph(workflow_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], tx) -> None:
    """Синхронизирует узлы и рёбра воркфлоу с переданными списками.

    Выполняется в рамках открытой транзакции.
    Алгоритм:
      1. Получает текущие узлы из БД.
      2. Для каждого узла из nodes:
         - если node_id уже существует → обновляет поля (prompt_key, config, position_x, position_y)
         - иначе → создаёт новый узел.
      3. Удаляет узлы, которые есть в БД, но отсутствуют в nodes (каскадно удаляются связанные рёбра).
      4. Удаляет все оставшиеся рёбра для данного workflow (чтобы убрать те, что ссылались на неудалённые узлы, но не входят в edges).
      5. Вставляет новые рёбра из edges.

    Args:
        workflow_id: ID воркфлоу.
        nodes: Список словарей с ключами: node_id, prompt_key, config, position_x, position_y.
        edges: Список словарей с ключами: source_node, target_node, source_output, target_input.
        tx: Объект транзакции.

    Raises:
        Exception: при ошибке целостности (например, ребро ссылается на несуществующий узел) транзакция будет откачена.
    """
    # 1. Текущие узлы
    current_nodes = await get_workflow_nodes(workflow_id, tx=tx)
    node_map = {n['node_id']: n for n in current_nodes}  # node_id -> запись с полем id

    # 2. Обработка узлов из запроса
    for node_data in nodes:
        node_id = node_data['node_id']
        if node_id in node_map:
            # Обновляем существующий
            record_id = node_map[node_id]['id']
            await update_workflow_node(
                record_id,
                tx=tx,
                prompt_key=node_data['prompt_key'],
                config=node_data.get('config', {}),
                position_x=node_data['position_x'],
                position_y=node_data['position_y']
            )
            # Удаляем из node_map, чтобы потом не удалить ошибочно
            del node_map[node_id]
        else:
            # Создаём новый
            await create_workflow_node(
                workflow_id,
                node_id,
                prompt_key=node_data['prompt_key'],
                config=node_data.get('config', {}),
                position_x=node_data['position_x'],
                position_y=node_data['position_y'],
                tx=tx
            )

    # 3. Удаляем узлы, оставшиеся в node_map (отсутствуют в запросе)
    for node_record in node_map.values():
        await delete_workflow_node(node_record['id'], tx=tx)

    # 4. Удаляем все существующие рёбра (после удаления узлов часть могла удалиться каскадно,
    #    но удалим оставшиеся, чтобы гарантировать точное соответствие)
    current_edges = await get_workflow_edges(workflow_id, tx=tx)
    for edge in current_edges:
        await delete_workflow_edge(edge['id'], tx=tx)

    # 5. Вставляем новые рёбра
    for edge_data in edges:
        await create_workflow_edge(
            workflow_id,
            source_node=edge_data['source_node'],
            target_node=edge_data['target_node'],
            source_output=edge_data.get('source_output', 'output'),
            target_input=edge_data.get('target_input', 'input'),
            tx=tx
        )