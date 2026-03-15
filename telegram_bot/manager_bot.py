import asyncio
import logging
import os
import sys

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from services.redis_client import get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("MANAGER_BOT_TOKEN", "").strip()
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
MANAGER_API_TOKEN = os.getenv("MANAGER_API_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError("MANAGER_BOT_TOKEN is not set or empty")
if not MANAGER_API_TOKEN:
    raise RuntimeError("MANAGER_API_TOKEN is not set or empty")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Я бот для менеджеров MRAK-OS.\n\n"
        "Вы будете получать уведомления о новых обращениях клиентов. "
        "Под каждым уведомлением есть кнопка ✏️ Ответить. "
        "Нажмите её, затем введите ваш ответ – он будет отправлен клиенту."
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие на inline-кнопку."""
    query = update.callback_query
    await query.answer()  # убираем "часики"

    data = query.data
    if data.startswith("reply:"):
        exec_id = data.split(":", 1)[1]
        chat_id = query.message.chat_id

        # Сохраняем состояние ожидания ответа от этого менеджера
        redis = await get_redis_client()
        key = f"awaiting_reply:{chat_id}"
        await redis.setex(key, 600, exec_id)  # 10 минут на ответ

        await query.message.reply_text(
            "✍️ Введите ваш ответ на это обращение (можно несколько строк).\n"
            "Отправьте сообщение сейчас, и оно будет доставлено клиенту."
        )
    else:
        await query.message.reply_text("Неизвестная команда.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения – возможно, это ответ на уведомление."""
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    text = update.message.text.strip()

    redis = await get_redis_client()
    key = f"awaiting_reply:{chat_id}"
    exec_id = await redis.get(key)

    if exec_id:
        # Это ответ на ожидающее уведомление
        await redis.delete(key)  # сразу удаляем, чтобы нельзя было ответить дважды

        # Отправляем ответ через API
        url = f"{API_URL}/api/executions/{exec_id}/manager-reply"
        headers = {
            "X-Manager-Token": MANAGER_API_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {"message": text}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    await update.message.reply_text("✅ Ответ успешно отправлен клиенту.")
                else:
                    detail = "неизвестная ошибка"
                    try:
                        data = resp.json()
                        detail = data.get("detail", str(resp.status_code))
                    except Exception:
                        detail = f"HTTP {resp.status_code}"
                    await update.message.reply_text(f"❌ Ошибка при отправке: {detail}")
        except Exception as e:
            logger.exception("Failed to send manager reply")
            await update.message.reply_text(f"❌ Техническая ошибка: {str(e)}")
    else:
        # Нет ожидающего ответа – отправляем подсказку
        await update.message.reply_text(
            "Чтобы ответить клиенту, нажмите кнопку ✏️ Ответить под соответствующим уведомлением."
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Принудительный сброс
    async def setup():
        await app.bot.delete_webhook(drop_pending_updates=True)
        # Получаем все обновления с offset = -1, чтобы очистить очередь
        await app.bot.get_updates(offset=-1)
        logger.info("Webhook cleared and updates reset, starting polling...")

    import asyncio
    asyncio.get_event_loop().run_until_complete(setup())

    logger.info("Manager bot started, polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()