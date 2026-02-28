# CHANGED: Use artifact_service instead of orchestrator
import logging
from schemas import GenerateArtifactRequest
from artifact_service import ArtifactService
from repositories.base import transaction
import db
from validation import ValidationError

logger = logging.getLogger(__name__)

class GenerateArtifactUseCase:
    def __init__(self, artifact_service: ArtifactService):
        self.artifact_service = artifact_service

    async def execute(self, req: GenerateArtifactRequest):
        try:
            if req.artifact_type == "BusinessRequirementPackage":
                result = await self.artifact_service.generate_business_requirements(
                    analysis_id=req.parent_id,
                    user_feedback=req.feedback,
                    model_id=req.model,
                    project_id=req.project_id,
                    existing_requirements=req.existing_content
                )
            elif req.artifact_type == "ReqEngineeringAnalysis":
                result = await self.artifact_service.generate_req_engineering_analysis(
                    parent_id=req.parent_id,
                    user_feedback=req.feedback,
                    model_id=req.model,
                    project_id=req.project_id,
                    existing_analysis=req.existing_content
                )
            elif req.artifact_type == "FunctionalRequirementPackage":
                result = await self.artifact_service.generate_functional_requirements(
                    analysis_id=req.parent_id,
                    user_feedback=req.feedback,
                    model_id=req.model,
                    project_id=req.project_id,
                    existing_requirements=req.existing_content
                )
            else:
                parent = None
                if req.parent_id:
                    async with transaction() as tx:
                        parent = await db.get_artifact(req.parent_id, tx=tx)
                new_id = await self.artifact_service.generate_artifact(
                    artifact_type=req.artifact_type,
                    user_input=req.feedback,
                    parent_artifact=parent,
                    model_id=req.model,
                    project_id=req.project_id
                )
                async with transaction() as tx:
                    artifact = await db.get_artifact(new_id, tx=tx)
                if artifact:
                    return {"result": artifact['content']}
                else:
                    return {"result": {"id": new_id}}

            return {"result": result}
        except ValidationError as e:
            logger.warning(f"Validation error in generation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating artifact: {e}", exc_info=True)
            raise
