import pytest
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from use_cases.save_artifact_package import SaveArtifactPackageUseCase
from schemas import SavePackageRequest

@pytest.fixture
def mock_db():
    with patch("use_cases.save_artifact_package.db") as mock:
        mock.get_last_version_by_parent_and_type = AsyncMock()
        mock.save_artifact = AsyncMock()
        yield mock

@pytest.fixture
def mock_transaction():
    with patch("use_cases.save_artifact_package.transaction") as mock_tx:
        mock_tx.return_value.__aenter__.return_value = None
        yield mock_tx

@pytest.mark.asyncio
async def test_save_new_package(mock_db, mock_transaction):
    mock_db.get_last_version_by_parent_and_type.return_value = None
    mock_db.save_artifact.return_value = "new-id"

    req = SavePackageRequest(
        project_id="proj-id",
        parent_id="parent-id",
        artifact_type="BusinessRequirementPackage",
        content=[{"description": "test"}]
    )
    use_case = SaveArtifactPackageUseCase()
    result = await use_case.execute(req)

    assert result == {"id": "new-id"}
    mock_db.save_artifact.assert_called_once()
    args, kwargs = mock_db.save_artifact.call_args
    assert kwargs["artifact_type"] == "BusinessRequirementPackage"
    assert kwargs["project_id"] == "proj-id"
    assert kwargs["parent_id"] == "parent-id"
    assert "content_hash" in kwargs
    assert kwargs["version"] == "1"

@pytest.mark.asyncio
async def test_save_duplicate_package(mock_db, mock_transaction):
    mock_db.get_last_version_by_parent_and_type.return_value = {
        "id": "existing-id",
        "content_hash": "somehash"
    }
    with patch("use_cases.save_artifact_package.compute_content_hash", return_value="somehash"):
        req = SavePackageRequest(
            project_id="proj-id",
            parent_id="parent-id",
            artifact_type="BusinessRequirementPackage",
            content=[{"description": "test"}]
        )
        use_case = SaveArtifactPackageUseCase()
        result = await use_case.execute(req)

    assert result == {"id": "existing-id", "duplicate": True}
    mock_db.save_artifact.assert_not_called()

@pytest.mark.asyncio
async def test_save_with_increment_version(mock_db, mock_transaction):
    mock_db.get_last_version_by_parent_and_type.return_value = {
        "id": "old-id",
        "version": "5",
        "content_hash": "oldhash"
    }
    with patch("use_cases.save_artifact_package.compute_content_hash", return_value="newhash"):
        mock_db.save_artifact.return_value = "new-id"

        req = SavePackageRequest(
            project_id="proj-id",
            parent_id="parent-id",
            artifact_type="BusinessRequirementPackage",
            content=[{"description": "updated"}]
        )
        use_case = SaveArtifactPackageUseCase()
        result = await use_case.execute(req)

    assert result == {"id": "new-id"}
    mock_db.save_artifact.assert_called_once()
    args, kwargs = mock_db.save_artifact.call_args
    assert kwargs["version"] == "6"  # int(5)+1

@pytest.mark.asyncio
async def test_save_with_bad_version(mock_db, mock_transaction):
    mock_db.get_last_version_by_parent_and_type.return_value = {
        "id": "old-id",
        "version": "abc",  # не число
        "content_hash": "oldhash"
    }
    with patch("use_cases.save_artifact_package.compute_content_hash", return_value="newhash"):
        mock_db.save_artifact.return_value = "new-id"

        req = SavePackageRequest(
            project_id="proj-id",
            parent_id="parent-id",
            artifact_type="BusinessRequirementPackage",
            content=[{"description": "updated"}]
        )
        use_case = SaveArtifactPackageUseCase()
        result = await use_case.execute(req)

    assert result == {"id": "new-id"}
    args, kwargs = mock_db.save_artifact.call_args
    assert kwargs["version"] == "1"  # fallback to 1

@pytest.mark.asyncio
async def test_save_artifact_type_adds_ids(mock_db, mock_transaction):
    mock_db.get_last_version_by_parent_and_type.return_value = None
    mock_db.save_artifact.return_value = "new-id"

    content = [
        {"description": "req1", "id": "existing-id"},  # уже есть id
        {"description": "req2"}  # без id
    ]
    req = SavePackageRequest(
        project_id="proj-id",
        parent_id="parent-id",
        artifact_type="BusinessRequirementPackage",
        content=content
    )
    use_case = SaveArtifactPackageUseCase()
    result = await use_case.execute(req)

    assert result == {"id": "new-id"}
    saved_content = mock_db.save_artifact.call_args[1]["content"]
    assert len(saved_content) == 2
    assert saved_content[0]["id"] == "existing-id"
    assert "id" in saved_content[1]
    assert saved_content[1]["id"] is not None
