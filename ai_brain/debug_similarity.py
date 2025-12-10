"""Debug: Check which chunks should rank highest for 'Project name'"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config.settings import get_settings
from db.models import Chunk, Document
from services.embedding_service import EmbeddingService
import numpy as np

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    emb_service = EmbeddingService()
    
    async with async_session() as session:
        # Get all chunks for project 6
        stmt = (
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.project_id == 6)
            .order_by(Chunk.id)
        )
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        print(f"Computing similarities for {len(chunks)} chunks...\n")
        
        # Embed query
        query_vec = emb_service.embed_text("Project name")
        
        # Compute similarity for each chunk
        similarities = []
        for chunk in chunks:
            chunk_vec = emb_service.embed_text(chunk.text)
            similarity = float(query_vec @ chunk_vec)  # Dot product
            similarities.append((chunk.id, similarity, chunk.text))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        print("TOP 10 CHUNKS BY SEMANTIC SIMILARITY:")
        print("="*80)
        print()
        
        for i, (chunk_id, sim, text) in enumerate(similarities[:10], 1):
            # Check if contains project name
            has_name = any(kw in text.lower() for kw in ['godrej', 'emerald', 'waters'])
            marker = "✅" if has_name else "  "
            
            print(f"{i}. {marker} Chunk {chunk_id} | Similarity: {sim:.4f}")
            preview = text[:150].replace('\n', ' ')
            print(f"   {preview}...")
            print()
        
        # Count relevant in top 5
        relevant_in_top5 = sum(1 for _, _, text in similarities[:5] 
                               if any(kw in text.lower() for kw in ['godrej', 'emerald', 'waters']))
        
        print("="*80)
        print(f"\n✅ Relevant chunks in top 5: {relevant_in_top5}/5\n")
        
        if relevant_in_top5 >= 3:
            print("🎉 Excellent! Real embeddings working correctly.")
        elif relevant_in_top5 >= 1:
            print("⚠️ Good, but could be better. May need higher top_k.")
        else:
            print("❌ Issue: No relevant chunks in top 5")
    
    await engine.dispose()

asyncio.run(main())
