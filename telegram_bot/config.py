import os


BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")
API_TOKEN = os.getenv("API_TOKEN")  # токен для запросов к backend API

# Для внутренних вызовов из backend/worker к боту
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN")

# Для простого MVP можно уведомлять одного менеджера
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")


def validate_config() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    if not INTERNAL_TOKEN:
        raise RuntimeError("INTERNAL_TOKEN is not set")

