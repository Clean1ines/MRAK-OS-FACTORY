import os

from fastapi import APIRouter, HTTPException, status, Header, Depends

from schemas import TelegramRegisterRequest, ManagerReplyRequest
from repositories import (
    telegram_clients_repository,
    node_execution_repository,
    run_repository,
)
from repositories.base import transaction
from session_service import SessionService
import httpx


router = APIRouter(prefix="/api", tags=["telegram"])


def get_manager_api_token() -> str:
    token = os.getenv("MANAGER_API_TOKEN")
    if not token:
        raise RuntimeError("MANAGER_API_TOKEN is not set")
    return token


def get_bot_token() -> str:
    token = os.getenv("MANAGER_API_TOKEN")
    if not token:
        raise RuntimeError("MANAGER_API_TOKEN is not set")
    return token


@router.post("/telegram/register")
async def register_telegram_client(
    payload: TelegramRegisterRequest,
    x_bot_token: str = Header(..., alias="X-Bot-Token"),
):
    """
    Регистрирует Telegram-клиента в системе.

    Для MVP: просто сохраняем chat_id, project_id и email / crm_contact_id в таблицу telegram_clients.
    Интеграция с CRM-адаптером будет добавлена позже.
    """
    expected_token = get_bot_token()
    if x_bot_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bot token")

    # Пока CRM-адаптеры не реализованы полностью, используем email как crm_contact_id.
    crm_contact_id = payload.email

    await telegram_clients_repository.upsert_client(
        chat_id=payload.chat_id,
        project_id=payload.project_id,
        crm_contact_id=crm_contact_id,
    )

    return {"status": "ok", "crm_contact_id": crm_contact_id}


@router.post("/executions/{exec_id}/manager-reply")
async def manager_reply(
    exec_id: str,
    body: ManagerReplyRequest,
    x_manager_token: str = Header(..., alias="X-Manager-Token"),
    session_service: SessionService = Depends(),
):
    """
    Эндпоинт для ответа менеджера.

    - Проверяет X-Manager-Token (MANAGER_API_TOKEN).
    - Проверяет, что выполнение существует и находится в статусе MANUAL.
    - Добавляет сообщение в clarification-сессию как ответ ассистента.
    - Находит chat_id клиента по last_run_id в telegram_clients.
    - Отправляет сообщение клиенту через второго бота (MANAGER_BOT_TOKEN) напрямую.
    """
    expected_token = get_manager_api_token()
    if x_manager_token != expected_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid manager token")

    execution = await node_execution_repository.get_node_execution(exec_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    if execution.get("status") != "MANUAL":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Execution must be in MANUAL status, got {execution.get('status')}",
        )

    session_id = execution.get("clarification_session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Execution has no clarification session")

    # Сохраняем ответ менеджера как сообщение ассистента
    await session_service.add_message_to_session(session_id, "assistant", body.message)

    # Ищем клиента по run_id
    run_id = execution.get("run_id")
    if not run_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Execution has no run_id")

    client = await telegram_clients_repository.get_client_by_last_run(run_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram client not found for this run")

    chat_id = client.get("chat_id")
    if chat_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram client has no chat_id")

    # ----- ИЗМЕНЕНО: используем второго бота напрямую вместо внутреннего сервера -----
    manager_bot_token = os.getenv("MANAGER_BOT_TOKEN")
    if not manager_bot_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MANAGER_BOT_TOKEN is not configured",
        )

    url = f"https://api.telegram.org/bot{manager_bot_token}/sendMessage"
    params = {
        "chat_id": int(chat_id),
        "text": body.message,
    }

    async with httpx.AsyncClient(timeout=10.0) as client_http:
        resp = await client_http.post(url, json=params)
        if resp.status_code >= 400:
            # Пробуем получить текст ошибки от Telegram
            error_detail = "Unknown error"
            try:
                error_data = resp.json()
                error_detail = error_data.get("description", str(resp.status_code))
            except Exception:
                error_detail = f"HTTP {resp.status_code}"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to send Telegram message: {error_detail}",
            )

    return {"status": "ok"}
