"""
Chat Router - RAG-powered Q&A endpoint
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import time
import logging
from typing import List

from db.session import get_db_session
from db.models import Project
from api.chat_schemas import ChatRequest, ChatResponse, SourceChunk
from rag.retriever import Retriever
from rag.llm_engine import LLMEngine


router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

# Initialize RAG components (singleton instances)
retriever = Retriever()
llm_engine = LLMEngine()


@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_query(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db_session)
) -> ChatResponse:
    """
    RAG-powered chat endpoint.
    
    Process:
    1. Validate project exists
    2. Embed user query
    3. Retrieve relevant chunks from FAISS + database
    4. Generate answer using LLM
    5. Return structured response with sources
    
    Args:
        request: Chat request with project_id and message
        session: Database session (injected)
        
    Returns:
        ChatResponse with answer, sources, and metadata
        
    Raises:
        HTTPException 404: Project not found
        HTTPException 400: No documents indexed for project
    """
    # Start latency measurement
    start_time = time.time()
    
    logger.info(f"Chat query received - Project ID: {request.project_id}, Query: '{request.message[:100]}...'")
    
    # Step 1: Verify project exists
    stmt = select(Project).where(Project.id == request.project_id)
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        logger.warning(f"Project not found: {request.project_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {request.project_id} not found"
        )
    
    logger.debug(f"Project found: {project.name} (ID: {project.id})")
    
    # Step 2 & 3: Retrieve relevant chunks
    # This handles: embed query -> search FAISS -> fetch chunks from DB
    logger.debug(f"Retrieving chunks for query: '{request.message[:50]}...'")
    retrieved_chunks = await retriever.retrieve(
        session=session,
        project_id=request.project_id,
        query=request.message,
        top_k=10  # Increased from 5 for better accuracy with current chunking
    )
    
    if not retrieved_chunks:
        logger.warning(f"No chunks found for project {request.project_id}")
        # No chunks found - project might not have indexed documents
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No indexed documents found for project {request.project_id}. Please upload and process documents first."
        )
    
    logger.info(f"Retrieved {len(retrieved_chunks)} chunks with scores: {[f'{score:.3f}' for _, score in retrieved_chunks[:3]]}")
    
    # Step 4: Extract chunk texts for LLM
    chunk_texts = [chunk.text for chunk, _ in retrieved_chunks]
    
    # Step 5: Generate answer using LLM
    answer = llm_engine.generate_answer(
        question=request.message,
        chunks=chunk_texts
    )
    
    # Step 6: Detect language
    language = llm_engine.detect_language(request.message)
    
    # Step 7: Build source chunks for response
    sources: List[SourceChunk] = [
        SourceChunk(
            chunk_id=chunk.id,
            score=score,
            text=chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text
        )
        for chunk, score in retrieved_chunks
    ]
    
    # Calculate latency
    end_time = time.time()
    latency_ms = int((end_time - start_time) * 1000)
    
    # Step 8: Return response
    return ChatResponse(
        answer=answer,
        language=language,
        sources=sources,
        latency_ms=latency_ms
    )
