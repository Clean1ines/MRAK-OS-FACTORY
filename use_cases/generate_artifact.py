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
            # Загружаем родительский артефакт, если он есть
            input_artifacts = []
            if req.parent_id:
                async with transaction() as tx:
                    parent = await db.get_artifact(req.parent_id, tx=tx)
                    if parent:
                        input_artifacts = [parent]

            # Универсальный вызов генерации
            new_id = await self.artifact_service.generate_artifact(
                artifact_type=req.artifact_type,
                input_artifacts=input_artifacts,
                user_input=req.feedback,
                model_id=req.model,
                project_id=req.project_id
            )

            # Возвращаем содержимое созданного артефакта
            async with transaction() as tx:
                artifact = await db.get_artifact(new_id, tx=tx)
            if artifact:
                return {"result": artifact['content']}
            else:
                return {"result": {"id": new_id}}

        except ValidationError as e:
            logger.warning(f"Validation error in generation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating artifact: {e}", exc_info=True)
            raise
