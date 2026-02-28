# CHANGED: Added version argument to db.save_artifact
import logging
import uuid
from schemas import SavePackageRequest
from repositories.base import transaction
import db
from utils.hash import compute_content_hash

logger = logging.getLogger(__name__)

class SaveArtifactPackageUseCase:
    async def execute(self, req: SavePackageRequest):
        try:
            new_hash = compute_content_hash(req.content)
            async with transaction() as tx:
                last_pkg = await db.get_last_version_by_parent_and_type(
                    req.parent_id, req.artifact_type, tx=tx
                )
                if last_pkg and last_pkg.get('content_hash') == new_hash:
                    return {"id": last_pkg['id'], "duplicate": True}

                if last_pkg:
                    try:
                        last_version = int(last_pkg['version'])
                    except (ValueError, TypeError):
                        last_version = 0
                    version = str(last_version + 1)
                else:
                    version = "1"

                content_to_save = req.content
                if req.artifact_type in ["BusinessRequirementPackage", "FunctionalRequirementPackage"] and isinstance(content_to_save, list):
                    for r in content_to_save:
                        if 'id' not in r:
                            r['id'] = str(uuid.uuid4())

                artifact_id = await db.save_artifact(
                    artifact_type=req.artifact_type,
                    content=content_to_save,
                    owner="user",
                    status="DRAFT",
                    project_id=req.project_id,
                    parent_id=req.parent_id,
                    content_hash=new_hash,
                    version=version,  # ADDED
                    tx=tx
                )
            return {"id": artifact_id}
        except Exception as e:
            logger.error(f"Error saving package: {e}")
            raise
