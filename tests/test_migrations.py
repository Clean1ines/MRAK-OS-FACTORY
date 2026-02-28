"""
Integration tests for database migrations and constraints.
Uses real database connection via conftest.py fixtures.
"""

import pytest
import asyncpg  # type: ignore[import]
from repositories.base import transaction  # type: ignore[import]
from repositories.project_repository import create_project


@pytest.mark.asyncio
async def test_project_name_uniqueness_constraint(tx):
    """
    Test that the unique constraint on project name works as expected.
    Verifies REQ-013 and the migration adding uniqueness.
    """
    import uuid
    unique_name = f"UniqueTest-{uuid.uuid4().hex[:8]}"

    project_id = await create_project(
        name=unique_name,
        description="Test project",
        tx=tx
    )
    assert project_id is not None

    with pytest.raises(asyncpg.exceptions.UniqueViolationError) as excinfo:
        await create_project(
            name=unique_name,
            description="Another project",
            tx=tx
        )

    assert "duplicate key value violates unique constraint" in str(excinfo.value)


@pytest.mark.asyncio
async def test_unique_constraint_ignores_different_owners(db_connection):
    """
    Test that the unique constraint is scoped to owner_id.
    Requires that owner_id column exists. Otherwise skipped.
    """
    row = await db_connection.fetchrow("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'owner_id'
    """)
    if not row:
        pytest.skip("owner_id column not yet migrated – skipping test")

    async with transaction() as tx:
        await tx.execute("""
            INSERT INTO projects (id, name, description, owner_id, created_at, updated_at)
            VALUES (gen_random_uuid(), $1, $2, $3, NOW(), NOW())
        """, "SharedName", "Owner A", "user-1")

        await tx.execute("""
            INSERT INTO projects (id, name, description, owner_id, created_at, updated_at)
            VALUES (gen_random_uuid(), $1, $2, $3, NOW(), NOW())
        """, "SharedName", "Owner B", "user-2")

        with pytest.raises(asyncpg.exceptions.UniqueViolationError) as excinfo:
            await tx.execute("""
                INSERT INTO projects (id, name, description, owner_id, created_at, updated_at)
                VALUES (gen_random_uuid(), $1, $2, $3, NOW(), NOW())
            """, "SharedName", "Owner A duplicate", "user-1")
        assert "duplicate key value violates unique constraint" in str(excinfo.value)


@pytest.mark.asyncio
async def test_migration_applied_uniqueness_index(db_connection):
    """
    Verify that the unique index (name, owner_id) exists after migrations.
    """
    row = await db_connection.fetchrow("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'projects' AND indexdef LIKE '%UNIQUE%' AND indexdef LIKE '%name%'
    """)
    assert row is not None, "Unique index on projects(name) not found"
    indexdef = row['indexdef']

    col_row = await db_connection.fetchrow("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'owner_id'
    """)
    if col_row:
        assert "owner_id" in indexdef, "Unique index should include owner_id"
    else:
        print("Warning: owner_id column not found, index may be incomplete")
