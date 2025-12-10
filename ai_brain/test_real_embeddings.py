"""Test retrieval accuracy for 'Project name' query with real embeddings"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from rag.retriever import Retriever

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        retriever = Retriever()
        
        print("="*70)
        print("🧪 TESTING REAL EMBEDDINGS - 'Project name' Query")
        print("="*70)
        print()
        
        results = await retriever.retrieve(
            session=session,
            project_id=6,
            query="Project name",
            top_k=5
        )
        
        print(f"📥 Retrieved {len(results)} chunks:\n")
        
        for i, (chunk, score) in enumerate(results, 1):
            print(f"{i}. Chunk ID {chunk.id} | Score: {score:.4f}")
            
            # Check if chunk contains project name keywords
            chunk_lower = chunk.text.lower()
            has_godrej = 'godrej' in chunk_lower
            has_emerald = 'emerald' in chunk_lower
            has_waters = 'waters' in chunk_lower
            
            keywords = []
            if has_godrej and has_emerald and has_waters:
                keywords.append("✅ GODREJ EMERALD WATERS")
            elif has_godrej:
                keywords.append("⚠️ Godrej")
            
            if keywords:
                print(f"   Keywords: {', '.join(keywords)}")
            
            # Show text preview
            preview = chunk.text[:200].replace('\n', ' ')
            print(f"   Text: {preview}...")
            print()
        
        # Analysis
        print("="*70)
        print("📊 ANALYSIS:")
        print("="*70)
        
        relevant_count = sum(
            1 for chunk, _ in results 
            if 'godrej' in chunk.text.lower() and 'emerald' in chunk.text.lower()
        )
        
        print(f"\nRelevant chunks (contain 'Godrej Emerald'): {relevant_count}/{len(results)}")
        
        if relevant_count >= 3:
            print("✅ EXCELLENT: Most chunks are relevant to project name")
        elif relevant_count >= 1:
            print("⚠️ IMPROVED: Some relevant chunks, but could be better")
        else:
            print("❌ POOR: No relevant chunks found")
        
        print()
        print("Expected: Chunks mentioning 'GODREJ EMERALD WATERS'")
        print("Result: Chunks with actual project name information")
        print()
    
    await engine.dispose()

asyncio.run(main())
