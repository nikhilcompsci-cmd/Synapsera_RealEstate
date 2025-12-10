"""
Quick start script for AI Brain application.
Run this after setting up the database to verify everything works.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from db.session import engine, AsyncSessionLocal
from db.models import Base, Project
from sqlalchemy import select


async def test_database_connection():
    """Test database connection and basic operations."""
    print("🔍 Testing database connection...")
    
    try:
        # Test connection
        async with engine.connect() as conn:
            await conn.execute(select(1))
            print("✅ Database connection successful!")
        
        # Test session and query
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Project))
            projects = result.scalars().all()
            print(f"✅ Found {len(projects)} projects in database")
            
            for project in projects:
                print(f"   - {project.name}")
        
        print("\n✨ All tests passed! Ready to start the application.")
        print("\n📝 Next steps:")
        print("   1. Start the API: uvicorn main:app --reload")
        print("   2. Visit: http://localhost:8000/docs")
        print("   3. Create a project using POST /api/v1/project")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure to:")
        print("   1. Start Docker: docker-compose up -d")
        print("   2. Run migrations: alembic upgrade head")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_database_connection())
