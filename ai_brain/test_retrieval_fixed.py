"""
Test the RAG chat endpoint after fixing FAISS file issues
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from rag.retriever import Retriever

settings = get_settings()


async def test_retrieval():
    """Test the retrieval pipeline directly"""
    
    print("🧪 Testing RAG Retrieval Pipeline\n")
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        retriever = Retriever()
        
        # Test with project 6
        project_id = 6
        test_queries = [
            "What is the project name?",
            "Tell me about the property",
            "What are the amenities?"
        ]
        
        for query in test_queries:
            print(f"📝 Query: '{query}'")
            print(f"   Project ID: {project_id}")
            
            try:
                # Retrieve chunks
                results = await retriever.retrieve(
                    session=session,
                    project_id=project_id,
                    query=query,
                    top_k=3
                )
                
                if results:
                    print(f"   ✅ Found {len(results)} chunks")
                    for i, (chunk, score) in enumerate(results, 1):
                        text_preview = chunk.text[:100].replace('\n', ' ')
                        print(f"      {i}. Score: {score:.4f} | Chunk {chunk.id}: {text_preview}...")
                else:
                    print(f"   ⚠️  No chunks found (empty result)")
                
            except Exception as e:
                print(f"   ❌ Error: {type(e).__name__}: {e}")
            
            print()
    
    await engine.dispose()
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_retrieval())
