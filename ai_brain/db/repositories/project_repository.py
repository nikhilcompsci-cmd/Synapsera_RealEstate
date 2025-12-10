from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Project
from typing import Sequence


class ProjectRepository:
    """Repository for Project database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, name: str, description: str | None = None) -> Project:
        """
        Create a new project.
        NOTE: Does NOT commit - transaction handled by caller.
        """
        project = Project(name=name, description=description)
        self.session.add(project)
        await self.session.flush()  # Flush to get the ID without committing
        await self.session.refresh(project)  # Refresh to get server defaults
        return project
    
    async def get_by_id(self, project_id: int) -> Project | None:
        """Get a project by ID."""
        result = await self.session.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> Sequence[Project]:
        """Get all projects ordered by creation date."""
        result = await self.session.execute(
            select(Project).order_by(Project.created_at.desc())
        )
        return result.scalars().all()
