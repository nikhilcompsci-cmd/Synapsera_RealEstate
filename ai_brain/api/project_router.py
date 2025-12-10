from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db_session
from db.repositories.project_repository import ProjectRepository
from api.schemas import ProjectCreate, ProjectResponse
from typing import List

router = APIRouter(prefix="/project", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project"
)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_db_session)
) -> ProjectResponse:
    """
    Create a new real estate analysis project.
    
    - **name**: Project name (required)
    - **description**: Project description (optional)
    """
    try:
        repo = ProjectRepository(session)
        project = await repo.create(
            name=project_data.name,
            description=project_data.description
        )
        await session.commit()
        return ProjectResponse.model_validate(project)
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List all projects"
)
async def list_projects(
    session: AsyncSession = Depends(get_db_session)
) -> List[ProjectResponse]:
    """
    Retrieve all projects ordered by creation date (newest first).
    """
    try:
        repo = ProjectRepository(session)
        projects = await repo.get_all()
        return [ProjectResponse.model_validate(p) for p in projects]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}"
        )
