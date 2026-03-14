import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import BOT_TOKEN, validate_config


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Telegram-бот MRAK-OS. Пока я просто принимаю сообщения."
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # На следующем шаге здесь можно будет вызывать backend API
    # для регистрации, создания Run и отправки сообщений в MANUAL/LLM.
    await update.message.reply_text("Ваше сообщение получено. Вскоре я научусь отвечать умнее 🙂")


async def main() -> None:
    validate_config()
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    await application.initialize()
    await application.start()
    # run_polling внутри, но в async-варианте — используем idle
    await application.updater.start_polling()
    await application.updater.idle()


if __name__ == "__main__":
    asyncio.run(main())

