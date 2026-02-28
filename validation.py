# validation.py
# Validation utilities for artifact generation

import logging
from typing import Any, List, Dict, Tuple

logger = logging.getLogger("validation")

class ValidationError(Exception):
    """Raised when artifact validation fails after retries."""
    pass

# Required fields for structured artifact types
REQUIRED_FIELDS = {
    "BusinessRequirementPackage": ["description", "priority", "stakeholder", "acceptance_criteria", "business_value"],
    "FunctionalRequirementPackage": ["description", "priority", "stakeholder", "acceptance_criteria", "business_value"],
    # Add more types as needed
}

def validate_json_output(content: Any, artifact_type: str) -> Tuple[bool, str]:
    """
    Проверяет, что content соответствует ожидаемой структуре для artifact_type.
    Возвращает (True, "OK") если валидно, иначе (False, сообщение об ошибке).
    """
    required = REQUIRED_FIELDS.get(artifact_type)
    if not required:
        return True, "OK"  # no validation rules for this type

    if not isinstance(content, list):
        return False, f"Expected list, got {type(content).__name__}"

    for i, item in enumerate(content):
        if not isinstance(item, dict):
            return False, f"Item {i} is not a dict"
        for field in required:
            if field not in item:
                return False, f"Item {i} missing required field '{field}'"
    return True, "OK"
