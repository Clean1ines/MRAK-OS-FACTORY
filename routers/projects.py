# routers/projects.py

from fastapi import APIRouter, HTTPException, status
from typing import List
import db
from repositories.base import transaction
from repositories import project_repository as repo
from schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/api", tags=["projects"])

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """
    Возвращает список всех проектов, отсортированных по дате создания (сначала новые).
    """
    projects = await repo.get_projects()
    return projects  # уже возвращает список словарей, подходящих под ProjectResponse

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
    # Проверка уникальности имени
    if await repo.check_name_exists(project_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{project_data.name}' already exists"
        )

    async with transaction() as tx:
        project_id = await repo.create_project(
            name=project_data.name,
            description=project_data.description,
            tx=tx
        )
        # После создания получаем полный объект проекта (чтобы вернуть created_at и пр.)
        # Можно сразу вернуть созданные данные, но проще сделать дополнительный select.
        # Используем тот же транзакционный контекст.
        new_project = await repo.get_project(project_id, tx=tx)

    if not new_project:
        # Крайне маловероятно, но на всякий случай
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create project")
    return new_project

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_data: ProjectUpdate):
    """
    Полностью обновляет проект.

    Проверяет уникальность имени: новое имя не должно принадлежать другому проекту.
    Если проект с указанным ID не найден, возвращает 404.
    """
    # Сначала убедимся, что проект существует
    existing = await repo.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Проверка уникальности имени (исключая текущий проект)
    if await repo.check_name_exists(project_data.name, exclude_id=project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{project_data.name}' already exists"
        )

    async with transaction() as tx:
        updated = await repo.update_project(
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            tx=tx
        )
        if not updated:
            # Может случиться, если проект был удалён между проверкой и обновлением
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        # Получаем обновлённые данные
        updated_project = await repo.get_project(project_id, tx=tx)

    return updated_project

@router.delete("/projects/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(project_id: str):
    """
    Удаляет проект и все связанные с ним артефакты (каскадно).
    """
    # Проверяем существование (опционально, можно и просто удалить)
    existing = await repo.get_project(project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    async with transaction() as tx:
        await repo.delete_project(project_id, tx=tx)

    return {"status": "deleted", "id": project_id}
