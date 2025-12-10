"""Analyze retrieval quality for 'Project name' query"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config.settings import get_settings
from db.models import Chunk, Document, Project
from rag.retriever import Retriever
from services.embedding_service import EmbeddingService

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get project info
        proj_result = await session.execute(select(Project).where(Project.id == 6))
        project = proj_result.scalar_one_or_none()
        print(f"📁 Project: {project.name}")
        print(f"   Description: {project.description}\n")
        
        # Get all chunks for project 6
        stmt = (
            select(Chunk, Document.filename)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.project_id == 6)
            .order_by(Chunk.id)
        )
        result = await session.execute(stmt)
        all_chunks = result.all()
        
        print(f"📊 Total chunks in project: {len(all_chunks)}\n")
        
        # Search for chunks containing "project name" or similar
        print("🔍 Chunks containing project name keywords:")
        keywords = ['godrej', 'emerald', 'waters', 'project name', 'property name']
        
        for chunk, filename in all_chunks:
            chunk_lower = chunk.text.lower()
            matches = [kw for kw in keywords if kw in chunk_lower]
            if matches:
                print(f"\n  Chunk ID {chunk.id} (from {filename}):")
                print(f"  Keywords found: {matches}")
                preview = chunk.text[:200].replace('\n', ' ')
                print(f"  Text: {preview}...")
        
        print("\n" + "="*70)
        print("🧪 Testing Retriever with 'Project name' query")
        print("="*70 + "\n")
        
        # Test retrieval with stub embeddings
        retriever = Retriever()
        results = await retriever.retrieve(
            session=session,
            project_id=6,
            query="Project name",
            top_k=5
        )
        
        print(f"📥 Retrieved {len(results)} chunks:\n")
        for i, (chunk, score) in enumerate(results, 1):
            print(f"{i}. Chunk ID {chunk.id} | Score: {score:.4f}")
            preview = chunk.text[:150].replace('\n', ' ')
            print(f"   {preview}...\n")
        
        print("="*70)
        print("🔬 ANALYSIS:")
        print("="*70)
        print()
        print("ISSUE: Stub embeddings are RANDOM and don't capture semantic meaning")
        print()
        print("Current behavior:")
        print("  ✗ Query 'Project name' gets random embedding")
        print("  ✗ Document chunks have random embeddings (from ingestion)")
        print("  ✗ FAISS returns random chunks based on random similarity")
        print("  ✗ Result: Irrelevant chunks about dimensions, payment plans, etc.")
        print()
        print("Expected behavior (with real embeddings):")
        print("  ✓ Query 'Project name' → embedding captures 'name/title' concept")
        print("  ✓ Chunks with 'Godrej Emerald Waters' → high similarity")
        print("  ✓ FAISS returns chunks mentioning the actual project name")
        print("  ✓ Result: 'The project is called Godrej Emerald Waters'")
        print()
        print("="*70)
        print("💡 SOLUTION:")
        print("="*70)
        print()
        print("Replace stub embeddings with REAL sentence-transformers:")
        print()
        print("In retriever.py:")
        print("  - Remove stub embed_query()")
        print("  - Use: self.embedding_service.embed_text(query)")
        print()
        print("Benefits:")
        print("  ✓ Semantic similarity matching")
        print("  ✓ 'Project name' query finds chunks with actual names")
        print("  ✓ 'amenities' query finds amenity lists")
        print("  ✓ Accurate, context-aware retrieval")
        print()
        
        # Test with real embeddings
        print("="*70)
        print("🧪 TESTING WITH REAL EMBEDDINGS:")
        print("="*70 + "\n")
        
        emb_service = EmbeddingService()
        
        # Embed the query
        query_vector = emb_service.embed_text("Project name")
        print(f"✓ Query embedded with real model: {emb_service.model_name}")
        print(f"  Vector dimension: {query_vector.shape[0]}\n")
        
        # Compare with a few chunks manually
        print("Manual similarity check (real embeddings):\n")
        
        test_chunks = [
            "GODREJ EMERALD WATERS - A luxury residential project",
            "Payment plan details and milestones",
            "The project name is Godrej Emerald Waters"
        ]
        
        for text in test_chunks:
            chunk_vector = emb_service.embed_text(text)
            similarity = float(query_vector @ chunk_vector)  # Dot product
            print(f"  Similarity: {similarity:.4f} | {text}")
        
    await engine.dispose()

asyncio.run(main())
