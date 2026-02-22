-- migrations/add_workflow_tables.sql
-- Создание таблиц для хранения конфигурируемых пайплайнов (workflows)
-- Добавлено: 2026-02-22

-- ==================== Таблица workflows ====================
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ==================== Таблица workflow_nodes ====================
CREATE TABLE IF NOT EXISTS workflow_nodes (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,  -- локальный идентификатор узла в рамках workflow
    prompt_key TEXT NOT NULL,  -- ключ из mode_map (например, "02_IDEA_CLARIFIER")
    config JSONB NOT NULL DEFAULT '{}',
    position_x FLOAT NOT NULL,
    position_y FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(workflow_id, node_id)
);

-- ==================== Таблица workflow_edges ====================
CREATE TABLE IF NOT EXISTS workflow_edges (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    source_node TEXT NOT NULL,
    target_node TEXT NOT NULL,
    source_output TEXT NOT NULL DEFAULT 'output',
    target_input TEXT NOT NULL DEFAULT 'input',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- внешние ключи на workflow_nodes через составной ключ (workflow_id, node_id)
    FOREIGN KEY (workflow_id, source_node) REFERENCES workflow_nodes(workflow_id, node_id) ON DELETE CASCADE,
    FOREIGN KEY (workflow_id, target_node) REFERENCES workflow_nodes(workflow_id, node_id) ON DELETE CASCADE
);

-- ==================== Индексы ====================
CREATE INDEX IF NOT EXISTS idx_workflow_nodes_workflow ON workflow_nodes(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_edges_workflow ON workflow_edges(workflow_id);
-- Уникальность (workflow_id, node_id) уже обеспечена UNIQUE-ограничением выше, индекс создаётся автоматически.

