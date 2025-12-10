"""
Generate missing mapping files for existing FAISS indexes
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config.settings import get_settings
from db.models import Chunk, EmbeddingMetadata

settings = get_settings()


async def generate_mapping_for_project(project_id: int):
    """Generate chunk ID mapping file for a project"""
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all chunks for this project with embeddings, ordered by FAISS index ID
        stmt = (
            select(Chunk, EmbeddingMetadata.faiss_index_id)
            .join(EmbeddingMetadata, Chunk.id == EmbeddingMetadata.chunk_id)
            .join(Chunk.document)
            .where(Chunk.document.has(project_id=project_id))
            .order_by(EmbeddingMetadata.faiss_index_id)
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            print(f"  ❌ No chunks found for project {project_id}")
            return False
        
        # Build mapping array: faiss_index_id -> chunk_id
        chunk_ids = [row[0].id for row in rows]
        chunk_id_array = np.array(chunk_ids, dtype=np.int64)
        
        # Save mapping file
        mapping_path = Path("data/faiss_indexes") / f"project_{project_id}_mapping.npy"
        np.save(str(mapping_path), chunk_id_array)
        
        print(f"  ✅ Created mapping for project {project_id}: {len(chunk_ids)} chunks")
        return True
    
    await engine.dispose()


async def main():
    print("🔧 Generating missing FAISS mapping files...\n")
    
    # Find all FAISS index files
    faiss_dir = Path("data/faiss_indexes")
    if not faiss_dir.exists():
        print("❌ FAISS directory not found")
        return
    
    faiss_files = list(faiss_dir.glob("project_*.faiss"))
    
    if not faiss_files:
        print("ℹ️  No FAISS indexes found")
        return
    
    print(f"Found {len(faiss_files)} FAISS indexes\n")
    
    for faiss_file in faiss_files:
        # Extract project ID from filename
        project_id = int(faiss_file.stem.replace("project_", ""))
        
        # Check if mapping already exists
        mapping_file = faiss_dir / f"project_{project_id}_mapping.npy"
        
        if mapping_file.exists():
            print(f"Project {project_id}:")
            print(f"  ⏭️  Mapping already exists, skipping")
        else:
            print(f"Project {project_id}:")
            await generate_mapping_for_project(project_id)
        
        print()
    
    print("✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(main())
