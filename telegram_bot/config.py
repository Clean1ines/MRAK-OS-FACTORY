import os


BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN")  # токен для запросов к backend API

# Для внутренних вызовов из backend/worker к боту
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN")

# Публичный URL бота (для вебхука) – сначала пробуем RENDER_EXTERNAL_URL, потом WEBHOOK_URL
PUBLIC_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL")

# Для простого MVP можно уведомлять одного менеджера
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")


def validate_config() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    if not INTERNAL_TOKEN:
        raise RuntimeError("INTERNAL_TOKEN is not set")
    if not PUBLIC_URL:
        raise RuntimeError(
            "Neither RENDER_EXTERNAL_URL nor WEBHOOK_URL is set. "
            "Please set one of them to your public HTTPS URL."
        )
    if not PUBLIC_URL.startswith("https://"):
        raise RuntimeError(f"PUBLIC_URL must start with https://, got: {PUBLIC_URL}")