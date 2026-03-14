import asyncio
import logging
import uuid
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .config import BOT_TOKEN, API_URL, INTERNAL_TOKEN, validate_config
from .api_client import BackendAPIClient

logger = logging.getLogger(__name__)

_api_client = None
_application = None
_initialized = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Telegram-бот MRAK-OS. Отправь мне любое сообщение, и я обработаю его через твой workflow."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global _api_client

    # Запускаем фоновую задачу для периодической отправки "печатает"
    async def send_typing():
        while True:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            await asyncio.sleep(5)

    typing_task = asyncio.create_task(send_typing())

    text = update.message.text
    project_id = "ddbee36b-1c76-4bcd-94a7-162cb854f661"
    workflow_id = "0040c020-bcc1-4452-9466-e60b3466b692"
    start_node_id = "0fd2e911-537f-4a73-8cd9-286e594dfee8"

    try:
        run_id = await _api_client.create_run(project_id, workflow_id)
        logger.info(f"Run created: {run_id}")

        idempotency_key = str(uuid.uuid4())
        execution_id = await _api_client.execute_node(run_id, start_node_id, idempotency_key)
        logger.info(f"Execution created: {execution_id}")

        response = await _api_client.send_message(execution_id, text)
        logger.info(f"Got response: {response}")

        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        await update.message.reply_text(response)

    except Exception as e:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        logger.exception("Error processing message")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")

def get_application() -> Application:
    global _application, _api_client
    if _application is None:
        validate_config()
        _api_client = BackendAPIClient(API_URL, INTERNAL_TOKEN)
        _application = Application.builder().token(BOT_TOKEN).build()
        _application.add_handler(CommandHandler("start", start))
        _application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    return _application

async def init_application():
    global _initialized
    if not _initialized:
        app = get_application()
        await app.initialize()
        await app.start()
        _initialized = True
        logger.info("Telegram Application initialized and started")

async def handle_webhook(data: dict) -> None:
    if not _initialized:
        raise RuntimeError("Application not initialized. Call init_application() first.")
    app = get_application()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)