"""
Репозиторий для работы с таблицей runs.
"""
from typing import Optional, Dict, Any, List
from .base import get_connection

async def create_run(
    project_id: str,
    workflow_id: str,
    created_by: Optional[str] = None,
    tx=None
) -> str:
    """Создаёт новый Run в статусе OPEN. Возвращает ID созданной записи."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        run_id = await conn.fetchval("""
            INSERT INTO runs (project_id, workflow_id, created_by)
            VALUES ($1, $2, $3)
            RETURNING id
        """, project_id, workflow_id, created_by)
        return str(run_id)  # UUID -> str
    finally:
        if close_conn:
            await conn.close()

async def get_run(run_id: str, tx=None) -> Optional[Dict[str, Any]]:
    """Возвращает запись Run по ID или None. Все UUID преобразуются в строки."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        row = await conn.fetchrow("SELECT * FROM runs WHERE id = $1", run_id)
        if row:
            run = dict(row)
            # Преобразуем UUID поля в строки
            run['id'] = str(run['id'])
            run['project_id'] = str(run['project_id'])
            run['workflow_id'] = str(run['workflow_id'])
            run['created_at'] = run['created_at'].isoformat() if run['created_at'] else None
            run['frozen_at'] = run['frozen_at'].isoformat() if run['frozen_at'] else None
            run['archived_at'] = run['archived_at'].isoformat() if run['archived_at'] else None
            return run
        return None
    finally:
        if close_conn:
            await conn.close()

async def update_run_status(
    run_id: str,
    new_status: str,
    expected_status: Optional[str] = None,
    tx=None
) -> bool:
    """
    Обновляет статус Run. Возвращает True, если обновление выполнено, иначе False.
    Если указан expected_status, обновление происходит только при совпадении текущего статуса.
    При статусах FROZEN или ARCHIVED автоматически заполняет соответствующие временные метки.
    """
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        # Формируем запрос с условием на ожидаемый статус
        query = "UPDATE runs SET status = $1"
        params = [new_status]
        if expected_status:
            query += " WHERE id = $2 AND status = $3"
            params.extend([run_id, expected_status])
        else:
            query += " WHERE id = $2"
            params.append(run_id)

        result = await conn.execute(query, *params)
        if result == "UPDATE 0":
            return False

        # Заполняем временные метки в зависимости от нового статуса
        if new_status == "FROZEN":
            await conn.execute("UPDATE runs SET frozen_at = NOW() WHERE id = $1", run_id)
        elif new_status == "ARCHIVED":
            await conn.execute("UPDATE runs SET archived_at = NOW() WHERE id = $1", run_id)
        # Для других статусов (например, OPEN) метки не трогаем

        return True
    finally:
        if close_conn:
            await conn.close()

async def list_runs(project_id: Optional[str] = None, tx=None) -> List[Dict[str, Any]]:
    """Возвращает список Run. Если указан project_id, фильтрует по нему. Сортировка по created_at убыванию."""
    if tx:
        conn = tx.conn
        close_conn = False
    else:
        conn = await get_connection()
        close_conn = True
    try:
        if project_id:
            rows = await conn.fetch("""
                SELECT * FROM runs
                WHERE project_id = $1
                ORDER BY created_at DESC
            """, project_id)
        else:
            rows = await conn.fetch("""
                SELECT * FROM runs
                ORDER BY created_at DESC
            """)
        runs = []
        for row in rows:
            run = dict(row)
            run['id'] = str(run['id'])
            run['project_id'] = str(run['project_id'])
            run['workflow_id'] = str(run['workflow_id'])
            run['created_at'] = run['created_at'].isoformat() if run['created_at'] else None
            run['frozen_at'] = run['frozen_at'].isoformat() if run['frozen_at'] else None
            run['archived_at'] = run['archived_at'].isoformat() if run['archived_at'] else None
            runs.append(run)
        return runs
    finally:
        if close_conn:
            await conn.close()