-- migrations/add_artifact_types.sql
-- Таблица для хранения метаданных о типах артефактов

CREATE TABLE IF NOT EXISTS artifact_types (
    type TEXT PRIMARY KEY,
    schema JSONB NOT NULL,
    allowed_parents TEXT[] NOT NULL DEFAULT '{}',
    requires_clarification BOOLEAN NOT NULL DEFAULT FALSE,
    icon TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Заполняем начальными данными на основе существующих правил
INSERT INTO artifact_types (type, schema, allowed_parents, requires_clarification) VALUES
    ('BusinessIdea', '{
        "type": "object",
        "properties": {
            "text": {"type": "string"}
        }
    }'::jsonb, '{}', TRUE),
    ('ProductCouncilAnalysis', '{
        "type": "object",
        "properties": {
            "content": {"type": "object"}
        }
    }'::jsonb, '{BusinessIdea}', TRUE),
    ('BusinessRequirementPackage', '{
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["HIGH","MEDIUM","LOW"]},
                "stakeholder": {"type": "string"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "business_value": {"type": "string"}
            },
            "required": ["description","priority","stakeholder","acceptance_criteria","business_value"]
        }
    }'::jsonb, '{ProductCouncilAnalysis}', FALSE),
    ('ReqEngineeringAnalysis', '{
        "type": "object",
        "properties": {
            "analysis": {"type": "object"}
        }
    }'::jsonb, '{BusinessRequirementPackage}', FALSE),
    ('FunctionalRequirementPackage', '{
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["HIGH","MEDIUM","LOW"]},
                "stakeholder": {"type": "string"},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                "business_value": {"type": "string"}
            },
            "required": ["description","priority","stakeholder","acceptance_criteria","business_value"]
        }
    }'::jsonb, '{ReqEngineeringAnalysis}', FALSE),
    ('ArchitectureAnalysis', '{
        "type": "object",
        "properties": {
            "analysis": {"type": "object"}
        }
    }'::jsonb, '{FunctionalRequirementPackage}', FALSE),
    ('AtomicTask', '{
        "type": "object",
        "properties": {
            "tasks": {"type": "array"}
        }
    }'::jsonb, '{ArchitectureAnalysis}', FALSE),
    ('CodeArtifact', '{
        "type": "object",
        "properties": {
            "code": {"type": "string"}
        }
    }'::jsonb, '{AtomicTask}', FALSE),
    ('TestPackage', '{
        "type": "object",
        "properties": {
            "tests": {"type": "array"}
        }
    }'::jsonb, '{CodeArtifact}', FALSE);