import asyncio
import logging
import sys
import uuid
from aiohttp import web
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

from .config import BOT_TOKEN, API_URL, API_TOKEN, INTERNAL_TOKEN, PUBLIC_URL, validate_config
from .api_client import BackendAPIClient

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Глобальные объекты
api_client = None
application = None
INSTANCE_ID = uuid.uuid4().hex[:4]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Telegram-бот MRAK-OS. Отправь мне любое сообщение, и я обработаю его через твой workflow."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global api_client
    text = update.message.text
    project_id = "ddbee36b-1c76-4bcd-94a7-162cb854f661"
    workflow_id = "0040c020-bcc1-4452-9466-e60b3466b692"
    start_node_id = "0fd2e911-537f-4a73-8cd9-286e594dfee8"

    try:
        run_id = await api_client.create_run(project_id, workflow_id)
        logger.info(f"Run created: {run_id}")

        idempotency_key = str(uuid.uuid4())
        execution_id = await api_client.execute_node(run_id, start_node_id, idempotency_key)
        logger.info(f"Execution created: {execution_id}")

        response = await api_client.send_message(execution_id, text)
        logger.info(f"Got response: {response}")

        await update.message.reply_text(response)

    except Exception as e:
        logger.exception("Error processing message")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

async def send_message_handler(request: web.Request) -> web.Response:
    """Внутренний эндпоинт для отправки сообщений (от воркера)."""
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {INTERNAL_TOKEN}"
    if auth_header != expected:
        return web.json_response({"detail": "Unauthorized"}, status=401)

    data = await request.json()
    chat_id = data.get("chat_id")
    message = data.get("message")
    if chat_id is None or message is None:
        return web.json_response({"detail": "chat_id and message are required"}, status=400)

    await application.bot.send_message(chat_id=chat_id, text=message)
    return web.json_response({"status": "ok"})

async def cleanup(app: web.Application):
    """Закрывает приложение при остановке."""
    await application.shutdown()
    await api_client.close()
    logger.info("Application shutdown complete")

def create_app() -> web.Application:
    global api_client, application
    validate_config()
    api_client = BackendAPIClient(API_URL, API_TOKEN)

    # Создаём Telegram Application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    app = web.Application()
    app.router.add_post("/send-message", send_message_handler)
    app.on_shutdown.append(cleanup)
    return app

def main():
    logger.info(f"Instance {INSTANCE_ID}: Starting telegram-server")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8081)

if __name__ == "__main__":
    main()