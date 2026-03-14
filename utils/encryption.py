import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


_MASTER_KEY_ENV = "CRM_MASTER_KEY"
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """
    Возвращает инициализированный экземпляр Fernet на основе мастер-ключа из окружения.

    Ключ должен быть в формате base64-строки, совместимой с Fernet.
    """
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.getenv(_MASTER_KEY_ENV)
    if not key:
        raise RuntimeError(f"{_MASTER_KEY_ENV} is not set in environment")

    try:
        _fernet = Fernet(key)
    except Exception as exc:
        # Явная ошибка, чтобы быстро заметить некорректный ключ при старте
        raise RuntimeError(f"Invalid {_MASTER_KEY_ENV} value for Fernet") from exc

    return _fernet


def encrypt(data: str) -> str:
    """
    Шифрует строку с помощью Fernet и возвращает base64-строку.
    """
    if data is None:
        raise ValueError("Cannot encrypt None")

    f = _get_fernet()
    token = f.encrypt(data.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(token: str) -> str:
    """
    Расшифровывает base64-строку, зашифрованную encrypt().

    При неверном ключе или повреждённых данных выбрасывает RuntimeError.
    """
    if token is None:
        raise ValueError("Cannot decrypt None")

    f = _get_fernet()
    try:
        data = f.decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise RuntimeError("Failed to decrypt CRM data: invalid token or key") from exc

    return data.decode("utf-8")

