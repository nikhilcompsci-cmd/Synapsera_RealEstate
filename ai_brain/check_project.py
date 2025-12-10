"""Check project 6 details"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config.settings import get_settings
from db.models import Project

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(Project).where(Project.id == 6))
        project = result.scalar_one_or_none()
        
        if project:
            print(f"Project ID: {project.id}")
            print(f"Project Name: {project.name}")
            print(f"Description: {project.description}")
        else:
            print("Project 6 not found")
    
    await engine.dispose()

asyncio.run(main())
