import re
import json
import logging

logger = logging.getLogger(__name__)

def extract_client_response(full_response: str) -> str:
    """Извлекает текст после [CLIENT_RESPONSE]."""
    pattern = r'\[CLIENT_RESPONSE\]\s*(.*?)(?=\[|\Z)'
    match = re.search(pattern, full_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    logger.warning("No [CLIENT_RESPONSE] marker found, returning full response")
    return full_response.strip()

def extract_system_data(full_response: str) -> dict:
    """
    Извлекает JSON из блока [SYSTEM_DATA].
    Ищет текст между [SYSTEM_DATA] и следующим маркером [ или концом строки.
    Удаляет возможные обрамления ```json и ```.
    """
    pattern = r'\[SYSTEM_DATA\]\s*(.*?)(?=\[|\Z)'
    match = re.search(pattern, full_response, re.DOTALL | re.IGNORECASE)
    if not match:
        logger.warning("No [SYSTEM_DATA] marker found")
        return {}
    
    json_str = match.group(1).strip()
    # Убираем возможные обрамляющие ```json или ```
    json_str = re.sub(r'^```(?:json)?\s*|```$', '', json_str, flags=re.IGNORECASE).strip()
    json_str = re.sub(r'^```|```$', '', json_str).strip()
    
    try:
        data = json.loads(json_str)
        # Приводим artifact_id к строке, если пришло числом
        if "artifact_id" in data and not isinstance(data["artifact_id"], str):
            data["artifact_id"] = str(data["artifact_id"])
        return data
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from SYSTEM_DATA: {json_str[:200]}")
        return {}