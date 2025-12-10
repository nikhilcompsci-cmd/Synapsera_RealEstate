"""
Compare retrieval BEFORE and AFTER real embeddings fix
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from rag.retriever import Retriever
from rag.llm_engine import LLMEngine

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("="*80)
    print(" "*20 + "🎯 RAG RETRIEVAL FIX VERIFICATION")
    print("="*80)
    print()
    
    async with async_session() as session:
        retriever = Retriever()
        llm_engine = LLMEngine()
        
        # Test query
        query = "What is the project name?"
        project_id = 6
        
        print(f"Query: '{query}'")
        print(f"Project ID: {project_id}")
        print()
        print("-"*80)
        
        # Retrieve chunks
        results = await retriever.retrieve(
            session=session,
            project_id=project_id,
            query=query,
            top_k=5
        )
        
        print()
        print("📥 RETRIEVED CHUNKS:")
        print()
        
        chunk_texts = []
        relevant_count = 0
        
        for i, (chunk, score) in enumerate(results, 1):
            chunk_texts.append(chunk.text)
            
            # Check relevance
            has_name = any(kw in chunk.text.lower() for kw in ['godrej', 'emerald', 'waters'])
            if has_name:
                relevant_count += 1
                status = "✅ RELEVANT"
            else:
                status = "❌ IRRELEVANT"
            
            print(f"{i}. Chunk {chunk.id} | Score: {score:.4f} | {status}")
            preview = chunk.text[:120].replace('\n', ' ')
            print(f"   {preview}...")
            print()
        
        print("-"*80)
        print()
        
        # Generate answer
        answer = llm_engine.generate_answer(query, chunk_texts)
        
        print("🤖 GENERATED ANSWER:")
        print()
        print(answer)
        print()
        
        print("="*80)
        print("📊 EVALUATION:")
        print("="*80)
        print()
        
        print(f"✅ Relevant chunks retrieved: {relevant_count}/5")
        print(f"✅ Chunks contain 'GODREJ EMERALD WATERS': {relevant_count >= 3}")
        print(f"✅ Top chunk is relevant: {relevant_count > 0 and results[0][0].text.lower().find('godrej') >= 0}")
        print()
        
        if relevant_count >= 3:
            print("🎉 SUCCESS! Real embeddings are working correctly!")
            print()
            print("Before fix:")
            print("  - Random chunks (payment plans, dimensions)")
            print("  - 0-1 relevant chunks")
            print("  - Generic answer about 'document characters'")
            print()
            print("After fix:")
            print("  - Project name chunks (GODREJ EMERALD WATERS)")
            print("  - 3-5 relevant chunks")
            print("  - Answer contains actual project information")
        else:
            print("⚠️ Needs improvement. Expected 3+ relevant chunks.")
        
        print()
    
    await engine.dispose()

asyncio.run(main())
