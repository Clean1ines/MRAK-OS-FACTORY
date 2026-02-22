-- migrations/add_default_workflow.sql
-- Добавляет дефолтный workflow "Software Development" для простого режима

-- Вставляем workflow, если его ещё нет (проверяем по имени)
INSERT INTO workflows (id, name, description, is_default, created_at, updated_at)
SELECT '11111111-1111-1111-1111-111111111111'::uuid, 'Software Development', 'Default workflow for simple mode', TRUE, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM workflows WHERE name = 'Software Development');

-- Удаляем старые узлы и рёбра для этого workflow (если пересоздаём)
DELETE FROM workflow_edges WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid;
DELETE FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid;

-- Вставляем узлы (каждый узел соответствует типу артефакта)
INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y)
VALUES
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'BusinessIdea', '02_IDEA_CLARIFIER', '{}', 100, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'ProductCouncilAnalysis', '03_PRODUCT_COUNCIL', '{}', 300, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'BusinessRequirementPackage', '04_BUSINESS_REQ_GEN', '{}', 500, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'ReqEngineeringAnalysis', '05_REQ_ENG_COUNCIL', '{}', 700, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'FunctionalRequirementPackage', '06_SYSTEM_REQ_GEN', '{}', 900, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'ArchitectureAnalysis', '08_ARCHITECTURE_COUNCIL', '{}', 1100, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'AtomicTask', '09_CODE_TASK_GEN', '{}', 1300, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'CodeArtifact', '10_CODE_GEN', '{}', 1500, 100),
    (gen_random_uuid(), '11111111-1111-1111-1111-111111111111'::uuid, 'TestPackage', '11_TEST_GEN', '{}', 1700, 100);

-- Получаем ID узлов (используем подзапросы по node_id)
-- Создаём рёбра, связывающие узлы в линейную цепочку
INSERT INTO workflow_edges (id, workflow_id, source_node, target_node, source_output, target_input)
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'BusinessIdea') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'ProductCouncilAnalysis') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'ProductCouncilAnalysis') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'BusinessRequirementPackage') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'BusinessRequirementPackage') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'ReqEngineeringAnalysis') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'ReqEngineeringAnalysis') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'FunctionalRequirementPackage') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'FunctionalRequirementPackage') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'ArchitectureAnalysis') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'ArchitectureAnalysis') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'AtomicTask') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'AtomicTask') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'CodeArtifact') target
UNION ALL
SELECT
    gen_random_uuid(),
    '11111111-1111-1111-1111-111111111111'::uuid,
    source.node_id,
    target.node_id,
    'output',
    'input'
FROM
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'CodeArtifact') source,
    (SELECT node_id FROM workflow_nodes WHERE workflow_id = '11111111-1111-1111-1111-111111111111'::uuid AND node_id = 'TestPackage') target;
