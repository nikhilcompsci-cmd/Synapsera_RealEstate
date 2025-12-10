"""
Test the chunk repository eager loading fix
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from db.repositories.chunk_repository import ChunkRepository

settings = get_settings()


async def test_chunk_eager_loading():
    """Test that chunk retrieval with eager loading works without greenlet errors"""
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True
    )
    
    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        chunk_repo = ChunkRepository(session)
        
        # Try to get chunks for any document (even if none exist, it shouldn't error)
        try:
            chunks = await chunk_repo.get_by_document(1)
            print(f"✅ Successfully retrieved {len(chunks)} chunks")
            
            # If chunks exist, try to access embedding_metadata
            if chunks:
                for chunk in chunks:
                    has_embedding = chunk.embedding_metadata is not None
                    print(f"✅ Chunk {chunk.id}: has_embedding={has_embedding} (no greenlet error!)")
            else:
                print("ℹ️  No chunks found for document_id=1 (this is OK)")
                
            print("\n✅ TEST PASSED: No greenlet errors!")
            return True
            
        except Exception as e:
            print(f"❌ TEST FAILED: {type(e).__name__}: {e}")
            return False
    
    await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(test_chunk_eager_loading())
    exit(0 if success else 1)
