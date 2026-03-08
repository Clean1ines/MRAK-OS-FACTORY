"""
Integration tests for execution_queue_repository.
Uses real database, no mocks. Requires test database with migrations applied.
"""
import pytest
import pytest_asyncio
import uuid
import asyncio
from datetime import datetime, timedelta, timezone

from asyncpg import ForeignKeyViolationError

from repositories import execution_queue_repository as queue_repo
from repositories.base import get_connection, transaction


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Clean up relevant tables before each test."""
    conn = await get_connection()
    try:
        await conn.execute("TRUNCATE execution_queue, node_executions, runs, workflows, workflow_nodes, projects, artifacts CASCADE")
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def node_execution():
    """Create a complete set of related records and return a node_execution dict."""
    async with transaction() as tx:
        # 1. Create project
        project_id = str(uuid.uuid4())
        await tx.conn.execute("""
            INSERT INTO projects (id, name, description, created_at, updated_at)
            VALUES ($1, 'test-project', '', NOW(), NOW())
        """, project_id)

        # 2. Create workflow
        workflow_id = str(uuid.uuid4())
        await tx.conn.execute("""
            INSERT INTO workflows (id, project_id, name, created_at, updated_at)
            VALUES ($1, $2, 'test-workflow', NOW(), NOW())
        """, workflow_id, project_id)

        # 3. Create workflow node (to satisfy FK from node_executions)
        node_definition_id = str(uuid.uuid4())
        await tx.conn.execute("""
            INSERT INTO workflow_nodes (id, workflow_id, node_id, prompt_key, config, position_x, position_y, created_at, updated_at)
            VALUES ($1, $2, 'test-node', 'test-prompt', '{}', 0, 0, NOW(), NOW())
        """, node_definition_id, workflow_id)

        # 4. Create run
        run_id = str(uuid.uuid4())
        await tx.conn.execute("""
            INSERT INTO runs (id, project_id, workflow_id, status, created_at)
            VALUES ($1, $2, $3, 'OPEN', NOW())
        """, run_id, project_id, workflow_id)

        # 5. Create node_execution with all required fields
        exec_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        base_idempotency_key = idempotency_key
        now = datetime.now(timezone.utc)

        await tx.conn.execute("""
            INSERT INTO node_executions (
                id, run_id, node_definition_id, parent_execution_id,
                status, input_artifact_ids, output_artifact_id,
                idempotency_key, created_at, updated_at,
                validated_at, superseded_by_id,
                base_idempotency_key, attempt, max_attempts, retry_parent_id,
                project_id
            ) VALUES (
                $1, $2, $3, NULL,
                'PROCESSING', '[]', NULL,
                $4, $5, $5,
                NULL, NULL,
                $6, 1, 3, NULL,
                $7
            )
        """, exec_id, run_id, node_definition_id,
            idempotency_key, now,
            base_idempotency_key, project_id)

        # Return as dict (simulate repository _row_to_dict)
        return {
            "id": exec_id,
            "run_id": run_id,
            "node_definition_id": node_definition_id,
            "parent_execution_id": None,
            "status": "PROCESSING",
            "input_artifact_ids": [],
            "output_artifact_id": None,
            "idempotency_key": idempotency_key,
            "base_idempotency_key": base_idempotency_key,
            "attempt": 1,
            "max_attempts": 3,
            "retry_parent_id": None,
            "project_id": project_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "validated_at": None,
            "superseded_by_id": None,
        }


@pytest_asyncio.fixture
async def job_in_queue(node_execution):
    """Helper to insert a job directly into queue with given status."""
    async def _create(status="PENDING", locked_by=None, locked_at=None, created_at=None):
        job_id = str(uuid.uuid4())
        async with transaction() as tx:
            if created_at is None:
                created_at = datetime.now(timezone.utc)
            await tx.conn.execute("""
                INSERT INTO execution_queue (id, node_execution_id, status, locked_by, locked_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $6)
            """, job_id, node_execution['id'], status, locked_by, locked_at, created_at)
            return job_id
    return _create


# ----------------------------------------------------------------------
# Tests for enqueue
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enqueue_success(node_execution):
    """enqueue should insert a PENDING job and return its ID."""
    exec_id = node_execution['id']
    job_id = await queue_repo.enqueue(exec_id)
    assert job_id is not None
    assert uuid.UUID(job_id)

    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT * FROM execution_queue WHERE id = $1", job_id)
        assert row is not None
        assert row['status'] == 'PENDING'
        assert row['node_execution_id'] == uuid.UUID(exec_id)
        assert row['locked_by'] is None
        assert row['locked_at'] is None
        assert row['created_at'] is not None
        assert row['updated_at'] is not None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_enqueue_with_transaction(node_execution):
    """When called inside a transaction, the job should be visible within the transaction but not outside until commit."""
    exec_id = node_execution['id']
    async with transaction() as tx:
        job_id = await queue_repo.enqueue(exec_id, tx=tx)
        # Within transaction, job should be visible
        row = await tx.conn.fetchrow("SELECT * FROM execution_queue WHERE id = $1", job_id)
        assert row is not None
        # Outside transaction, it should not be visible yet (separate connection)
        conn2 = await get_connection()
        try:
            row2 = await conn2.fetchrow("SELECT * FROM execution_queue WHERE id = $1", job_id)
            assert row2 is None
        finally:
            await conn2.close()
    # After transaction commits, job becomes visible
    conn3 = await get_connection()
    try:
        row3 = await conn3.fetchrow("SELECT * FROM execution_queue WHERE id = $1", job_id)
        assert row3 is not None
    finally:
        await conn3.close()


@pytest.mark.asyncio
async def test_enqueue_foreign_key_violation():
    """enqueue with a non-existent node_execution_id should raise ForeignKeyViolationError."""
    fake_id = str(uuid.uuid4())
    with pytest.raises(ForeignKeyViolationError):
        await queue_repo.enqueue(fake_id)


# ----------------------------------------------------------------------
# Tests for claim_job
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_job_no_jobs():
    """claim_job should return None when no PENDING jobs exist."""
    result = await queue_repo.claim_job("worker1")
    assert result is None


@pytest.mark.asyncio
async def test_claim_job_single(job_in_queue):
    """claim_job should take one PENDING job, set status to PROCESSING and assign worker."""
    job_id = await job_in_queue(status="PENDING")
    worker = "worker-1"
    claimed = await queue_repo.claim_job(worker)
    assert claimed is not None
    assert claimed['id'] == job_id
    assert claimed['status'] == 'PROCESSING'
    assert claimed['locked_by'] == worker
    assert claimed['locked_at'] is not None
    # Verify in DB
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT * FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'PROCESSING'
        assert row['locked_by'] == worker
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_claim_job_respects_order(job_in_queue):
    """claim_job should return the oldest PENDING job (by created_at)."""
    now = datetime.now(timezone.utc)
    older_id = await job_in_queue(status="PENDING", created_at=now - timedelta(minutes=10))
    newer_id = await job_in_queue(status="PENDING", created_at=now)
    claimed = await queue_repo.claim_job("worker")
    assert claimed['id'] == older_id


@pytest.mark.asyncio
async def test_claim_job_skip_locked(job_in_queue):
    """
    Simulate two concurrent workers: one claims the only available job,
    the other should get None (or a different job if available).
    """
    job_id = await job_in_queue(status="PENDING")
    worker1 = "worker1"
    worker2 = "worker2"

    async def claim(worker):
        async with transaction() as tx:
            return await queue_repo.claim_job(worker, tx=tx)

    results = await asyncio.gather(claim(worker1), claim(worker2), return_exceptions=True)

    successes = [r for r in results if r is not None and not isinstance(r, Exception)]
    assert len(successes) == 1
    assert successes[0]['id'] == job_id
    none_results = [r for r in results if r is None]
    assert len(none_results) == 1


# ----------------------------------------------------------------------
# Tests for complete_job
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_job_success(job_in_queue):
    """complete_job with success=True should set status to DONE."""
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker")
    await queue_repo.complete_job(job_id, success=True)
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'DONE'
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_complete_job_failure(job_in_queue):
    """complete_job with success=False should set status to FAILED."""
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker")
    await queue_repo.complete_job(job_id, success=False)
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'FAILED'
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_complete_job_nonexistent():
    """complete_job with a job ID that doesn't exist should not raise an error."""
    await queue_repo.complete_job(str(uuid.uuid4()), success=True)


# ----------------------------------------------------------------------
# Tests for reset_stuck_jobs
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reset_stuck_jobs(job_in_queue):
    """reset_stuck_jobs should reset jobs that have been PROCESSING longer than timeout."""
    stuck_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker", locked_at=stuck_time)
    count = await queue_repo.reset_stuck_jobs(timeout_minutes=10)
    assert count == 1
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT status, locked_by, locked_at FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'PENDING'
        assert row['locked_by'] is None
        assert row['locked_at'] is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_reset_stuck_jobs_no_stuck(job_in_queue):
    """reset_stuck_jobs should not affect jobs that are not stuck (recent locked_at)."""
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker", locked_at=recent_time)
    count = await queue_repo.reset_stuck_jobs(timeout_minutes=10)
    assert count == 0
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'PROCESSING'
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_reset_stuck_jobs_multiple(job_in_queue):
    """reset_stuck_jobs should reset all stuck jobs and return the correct count."""
    now = datetime.now(timezone.utc)
    stuck1 = await job_in_queue(status="PROCESSING", locked_by="w1", locked_at=now - timedelta(minutes=15))
    stuck2 = await job_in_queue(status="PROCESSING", locked_by="w2", locked_at=now - timedelta(minutes=20))
    fresh = await job_in_queue(status="PROCESSING", locked_by="w3", locked_at=now - timedelta(minutes=5))
    count = await queue_repo.reset_stuck_jobs(timeout_minutes=10)
    assert count == 2
    conn = await get_connection()
    try:
        row1 = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", stuck1)
        assert row1['status'] == 'PENDING'
        row2 = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", stuck2)
        assert row2['status'] == 'PENDING'
        row3 = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", fresh)
        assert row3['status'] == 'PROCESSING'
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_reset_stuck_jobs_zero_timeout(job_in_queue):
    """reset_stuck_jobs with timeout=0 should reset all PROCESSING jobs with locked_at in the past."""
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker", locked_at=past)
    count = await queue_repo.reset_stuck_jobs(timeout_minutes=0)
    assert count == 1
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'PENDING'
    finally:
        await conn.close()


# ----------------------------------------------------------------------
# Combined flows
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_job_after_reset(job_in_queue):
    """A job that was stuck and then reset should be claimable again."""
    stuck_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker", locked_at=stuck_time)
    await queue_repo.reset_stuck_jobs(timeout_minutes=10)
    claimed = await queue_repo.claim_job("new_worker")
    assert claimed is not None
    assert claimed['id'] == job_id
    assert claimed['status'] == 'PROCESSING'
    assert claimed['locked_by'] == 'new_worker'


@pytest.mark.asyncio
async def test_complete_job_after_reset(job_in_queue):
    """A job that was reset and then claimed can be completed normally."""
    stuck_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    job_id = await job_in_queue(status="PROCESSING", locked_by="worker", locked_at=stuck_time)
    await queue_repo.reset_stuck_jobs(timeout_minutes=10)
    await queue_repo.claim_job("new_worker")
    await queue_repo.complete_job(job_id, success=True)
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT status FROM execution_queue WHERE id = $1", job_id)
        assert row['status'] == 'DONE'
    finally:
        await conn.close()