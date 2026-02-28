import pytest
from validation import validate_json_output, REQUIRED_FIELDS, ValidationError

def test_validate_json_output_success():
    """Проверяет, что правильный JSON проходит валидацию."""
    artifact_type = "BusinessRequirementPackage"
    content = [
        {
            "description": "Test requirement",
            "priority": "HIGH",
            "stakeholder": "User",
            "acceptance_criteria": ["criterion 1"],
            "business_value": "Test value"
        }
    ]
    valid, msg = validate_json_output(content, artifact_type)
    assert valid is True
    assert msg == "OK"

def test_validate_json_output_missing_field():
    """Проверяет, что отсутствие обязательного поля вызывает ошибку."""
    artifact_type = "BusinessRequirementPackage"
    content = [
        {
            "description": "Test requirement",
            "priority": "HIGH",
            # stakeholder отсутствует
            "acceptance_criteria": ["criterion 1"],
            "business_value": "Test value"
        }
    ]
    valid, msg = validate_json_output(content, artifact_type)
    assert valid is False
    assert "missing required field 'stakeholder'" in msg

def test_validate_json_output_not_a_list():
    """Проверяет, что если контент не список, валидация не проходит."""
    artifact_type = "BusinessRequirementPackage"
    content = {"description": "single item"}
    valid, msg = validate_json_output(content, artifact_type)
    assert valid is False
    assert "Expected list" in msg

def test_validate_json_output_unknown_type():
    """Для типов без правил валидация всегда успешна."""
    artifact_type = "UnknownType"
    content = {"any": "data"}
    valid, msg = validate_json_output(content, artifact_type)
    assert valid is True
    assert msg == "OK"

def test_validate_json_output_empty_list():
    """Пустой список считается валидным (нет элементов для проверки)."""
    artifact_type = "BusinessRequirementPackage"
    content = []
    valid, msg = validate_json_output(content, artifact_type)
    assert valid is True
    assert msg == "OK"

def test_validate_json_output_item_not_dict():
    """Если элемент списка не словарь, валидация не проходит."""
    artifact_type = "BusinessRequirementPackage"
    content = ["not a dict"]
    valid, msg = validate_json_output(content, artifact_type)
    assert valid is False
    assert "Item 0 is not a dict" in msg

# Можно также добавить тест для проверки, что REQUIRED_FIELDS содержит ожидаемые ключи
def test_required_fields_defined():
    assert "BusinessRequirementPackage" in REQUIRED_FIELDS
    assert "FunctionalRequirementPackage" in REQUIRED_FIELDS
