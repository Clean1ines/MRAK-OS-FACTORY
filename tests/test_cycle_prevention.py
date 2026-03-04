"""
Integration tests for cycle prevention trigger on node_executions.parent_execution_id.
Uses real database and transactions; no mocks.
"""
import pytest
import uuid
import asyncpg

pytestmark = pytest.mark.asyncio

async def test_no_cycle_on_legal_update(tx):
    """
    Given two executions without parent,
    updating the second to be child of the first should succeed.
    """
    # Setup: create project, workflow, node, run, and two executions
    # Using direct SQL with tx.conn
    project_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO projects (id, name) VALUES ($1, $2)",
        project_id, "test_cycle_project"
    )
    workflow_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflows (id, name, project_id) VALUES ($1, $2, $3)",
        workflow_id, "test_cycle_workflow", project_id
    )
    node_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_id, workflow_id, "test_node", "test", '{}', 0, 0
    )
    run_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO runs (id, project_id, workflow_id) VALUES ($1, $2, $3)",
        run_id, project_id, workflow_id
    )
    exec1_id = str(uuid.uuid4())
    exec2_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, idempotency_key) VALUES ($1, $2, $3, $4)",
        exec1_id, run_id, node_id, "key1"
    )
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, idempotency_key) VALUES ($1, $2, $3, $4)",
        exec2_id, run_id, node_id, "key2"
    )

    # Legal update: set exec2's parent to exec1
    await tx.conn.execute(
        "UPDATE node_executions SET parent_execution_id = $1 WHERE id = $2",
        exec1_id, exec2_id
    )

    # Verify that parent was set
    row = await tx.conn.fetchrow("SELECT parent_execution_id FROM node_executions WHERE id = $1", exec2_id)
    assert row["parent_execution_id"] == uuid.UUID(exec1_id)

async def test_cycle_on_update_raises(tx):
    """
    Attempting to create a cycle (set exec1's parent to exec2 after exec2 is child of exec1)
    should raise an exception.
    """
    project_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO projects (id, name) VALUES ($1, $2)",
        project_id, "test_cycle_project2"
    )
    workflow_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflows (id, name, project_id) VALUES ($1, $2, $3)",
        workflow_id, "test_cycle_workflow2", project_id
    )
    node_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_id, workflow_id, "test_node", "test", '{}', 0, 0
    )
    run_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO runs (id, project_id, workflow_id) VALUES ($1, $2, $3)",
        run_id, project_id, workflow_id
    )
    exec1_id = str(uuid.uuid4())
    exec2_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, idempotency_key) VALUES ($1, $2, $3, $4)",
        exec1_id, run_id, node_id, "key3"
    )
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, idempotency_key) VALUES ($1, $2, $3, $4)",
        exec2_id, run_id, node_id, "key4"
    )

    # First, make exec2 child of exec1
    await tx.conn.execute(
        "UPDATE node_executions SET parent_execution_id = $1 WHERE id = $2",
        exec1_id, exec2_id
    )

    # Now attempt to set exec1's parent to exec2 (should create a cycle)
    with pytest.raises(asyncpg.exceptions.PostgresError, match="Cycle detected"):
        await tx.conn.execute(
            "UPDATE node_executions SET parent_execution_id = $1 WHERE id = $2",
            exec2_id, exec1_id
        )

async def test_self_parent_raises(tx):
    """
    Setting an execution's parent to itself should be rejected.
    """
    project_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO projects (id, name) VALUES ($1, $2)",
        project_id, "test_cycle_project3"
    )
    workflow_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflows (id, name, project_id) VALUES ($1, $2, $3)",
        workflow_id, "test_cycle_workflow3", project_id
    )
    node_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_id, workflow_id, "test_node", "test", '{}', 0, 0
    )
    run_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO runs (id, project_id, workflow_id) VALUES ($1, $2, $3)",
        run_id, project_id, workflow_id
    )
    exec_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, idempotency_key) VALUES ($1, $2, $3, $4)",
        exec_id, run_id, node_id, "key5"
    )

    with pytest.raises(asyncpg.exceptions.PostgresError, match="execution cannot be its own parent"):
        await tx.conn.execute(
            "UPDATE node_executions SET parent_execution_id = $1 WHERE id = $2",
            exec_id, exec_id
        )

async def test_insert_with_parent_no_cycle(tx):
    """
    Inserting a new execution with a valid parent should succeed.
    """
    project_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO projects (id, name) VALUES ($1, $2)",
        project_id, "test_cycle_project4"
    )
    workflow_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflows (id, name, project_id) VALUES ($1, $2, $3)",
        workflow_id, "test_cycle_workflow4", project_id
    )
    node_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_id, workflow_id, "test_node", "test", '{}', 0, 0
    )
    run_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO runs (id, project_id, workflow_id) VALUES ($1, $2, $3)",
        run_id, project_id, workflow_id
    )
    # Create a parent execution
    parent_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, idempotency_key) VALUES ($1, $2, $3, $4)",
        parent_id, run_id, node_id, "parent_key"
    )
    # Insert child with that parent
    child_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO node_executions (id, run_id, node_definition_id, parent_execution_id, idempotency_key) VALUES ($1, $2, $3, $4, $5)",
        child_id, run_id, node_id, parent_id, "child_key"
    )
    # Verify
    row = await tx.conn.fetchrow("SELECT parent_execution_id FROM node_executions WHERE id = $1", child_id)
    assert row["parent_execution_id"] == uuid.UUID(parent_id)

async def test_insert_self_parent_raises(tx):
    """
    Inserting a new execution with parent set to its own id should be rejected.
    """
    project_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO projects (id, name) VALUES ($1, $2)",
        project_id, "test_cycle_project5"
    )
    workflow_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflows (id, name, project_id) VALUES ($1, $2, $3)",
        workflow_id, "test_cycle_workflow5", project_id
    )
    node_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        node_id, workflow_id, "test_node", "test", '{}', 0, 0
    )
    run_id = str(uuid.uuid4())
    await tx.conn.execute(
        "INSERT INTO runs (id, project_id, workflow_id) VALUES ($1, $2, $3)",
        run_id, project_id, workflow_id
    )
    exec_id = str(uuid.uuid4())
    with pytest.raises(asyncpg.exceptions.PostgresError, match="execution cannot be its own parent"):
        await tx.conn.execute(
            "INSERT INTO node_executions (id, run_id, node_definition_id, parent_execution_id, idempotency_key) VALUES ($1, $2, $3, $4, $5)",
            exec_id, run_id, node_id, exec_id, "self_key"
        )
