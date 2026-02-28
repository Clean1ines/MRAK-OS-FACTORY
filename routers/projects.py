from fastapi import APIRouter, HTTPException, status
from typing import List
import db
from repositories.base import transaction
from repositories import project_repository as repo
from repositories.project_repository import DEFAULT_OWNER_ID
from schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/api", tags=["projects"])

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """
    Возвращает список всех проектов, отсортированных по дате создания (сначала новые).
    """
    projects = await repo.get_projects()  # owner_id не передаём – получаем все проекты
    return projects

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    Возвращает проект по его ID.
    """
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project_data: ProjectCreate):
    """
    Создаёт новый проект.

    Проверяет уникальность имени (не должно существовать проекта с таким же именем).
    """
    # Проверка уникальности имени для владельца по умолчанию
    if await repo.check_name_exists(project_data.name, owner_id=DEFAULT_OWNER_ID):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{project_data.name}' already exists"
        )

    async with transaction() as tx:
        project_id = await repo.create_project(
            name=project_data.name,
            description=project_data.description,
            owner_id=DEFAULT_OWNER_ID,
            tx=tx
        )
        new_project = await repo.get_project(project_id, tx=tx)

    if not new_project:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create project")
    return new_project

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_data: ProjectUpdate):
    """
    Полностью обновляет проект.

    Проверяет уникальность имени: новое имя не должно принадлежать другому проекту.
    Если проект с указанным ID не найден, возвращает 404.
    """
    existing = await repo.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Для проверки уникальности используем владельца текущего проекта (existing['owner_id']),
    # но в existing сейчас нет owner_id, потому что get_project не возвращает его.
    # Поэтому пока используем DEFAULT_OWNER_ID. В будущем нужно добавить owner_id в ответ.
    if await repo.check_name_exists(project_data.name, owner_id=DEFAULT_OWNER_ID, exclude_id=project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{project_data.name}' already exists"
        )

    async with transaction() as tx:
        updated = await repo.update_project(
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            owner_id=DEFAULT_OWNER_ID,  # временно
            tx=tx
        )
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        updated_project = await repo.get_project(project_id, tx=tx)

    return updated_project

@router.delete("/projects/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(project_id: str):
    """
    Удаляет проект и все связанные с ним артефакты (каскадно).
    """
    existing = await repo.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    async with transaction() as tx:
        await repo.delete_project(project_id, tx=tx)

    return {"status": "deleted", "id": project_id}
