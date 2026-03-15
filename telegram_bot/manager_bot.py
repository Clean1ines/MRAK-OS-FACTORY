import asyncio
import logging
import os
import re
import sys

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
    """Ответ на команду /start."""
    await update.message.reply_text(
        "👋 Я бот для менеджеров MRAK-OS.\n\n"
        "Чтобы ответить клиенту, отправьте сообщение в формате:\n"
        "`EXEC:<идентификатор выполнения> ваш ответ`\n\n"
        "Ответ может занимать несколько строк.\n"
        "Пример:\n"
        "`EXEC:123e4567-e89b-12d3-a456-426614174000 Здравствуйте,\n"
        "чем могу помочь?`"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения от менеджера."""
    text = update.message.text
    # Ожидаем формат: EXEC:<exec_id> <текст ответа> (с поддержкой многострочности)
    match = re.match(r"EXEC:(\S+)\s+(.+)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        await update.message.reply_text(
            "❌ Неверный формат. Используйте:\n"
            "`EXEC:<идентификатор выполнения> ваш ответ`\n"
            "(можно в несколько строк)"
        )
        return

    exec_id = match.group(1)
    reply_text = match.group(2).strip()

    if not reply_text:
        await update.message.reply_text("❌ Пустой ответ. Пожалуйста, напишите сообщение.")
        return

    # Отправляем ответ через внутренний API
    url = f"{API_URL}/api/executions/{exec_id}/manager-reply"
    headers = {
        "X-Manager-Token": MANAGER_API_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {"message": reply_text}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                await update.message.reply_text("✅ Ответ успешно отправлен клиенту.")
            else:
                # Попробуем извлечь детали ошибки из JSON
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

def main():
    """Запуск бота."""
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Manager bot started, polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
