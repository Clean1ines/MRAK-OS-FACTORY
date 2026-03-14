from aiohttp import web

from .config import INTERNAL_TOKEN, validate_config, BOT_TOKEN

from telegram import Bot


def create_app() -> web.Application:
    """
    Создаёт aiohttp-приложение с внутренним эндпоинтом /send-message,
    защищённым токеном INTERNAL_TOKEN.
    """
    validate_config()
    app = web.Application()
    app["bot"] = Bot(token=BOT_TOKEN)
    app.router.add_post("/send-message", handle_send_message)
    return app


async def handle_send_message(request: web.Request) -> web.Response:
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {INTERNAL_TOKEN}"
    if auth_header != expected:
        return web.json_response({"detail": "Unauthorized"}, status=401)

    data = await request.json()
    chat_id = data.get("chat_id")
    message = data.get("message")
    if chat_id is None or message is None:
        return web.json_response({"detail": "chat_id and message are required"}, status=400)

    bot: Bot = request.app["bot"]
    await bot.send_message(chat_id=chat_id, text=message)
    return web.json_response({"status": "ok"})


def main():
    """
    Точка входа для запуска внутреннего HTTP-сервера.

    Пример запуска:
        python -m telegram_bot.server
    """
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()

