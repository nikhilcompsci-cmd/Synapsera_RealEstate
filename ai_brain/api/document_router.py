from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import shutil
import logging
from typing import List

from db.session import get_db_session
from db.repositories.chunk_repository import ChunkRepository
from db.repositories.embedding_metadata_repository import EmbeddingMetadataRepository
from ingestion.ingestion_service import IngestionService
from tasks.ingestion_tasks import ingest_document_async, get_task_status
from api.schemas import (
    DocumentUploadResponse,
    IngestionStatusResponse,
    ChunkResponse,
    EmbeddingCountResponse
)

router = APIRouter(tags=["Documents"])
logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/project/{project_id}/document/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF document"
)
async def upload_document(
    project_id: int,
    file: UploadFile = File(..., description="PDF file to upload"),
    session: AsyncSession = Depends(get_db_session)
) -> DocumentUploadResponse:
    """
    Upload a PDF document and run the complete ingestion pipeline:
    1. Save file
    2. Extract text and metadata
    3. Check for duplicates (content hash)
    4. Chunk text
    5. Generate embeddings
    6. Add to FAISS index
    7. Store metadata in database
    
    Returns status of the ingestion process.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        logger.warning(f"Invalid file type attempted: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    logger.info(f"Document upload started - Project ID: {project_id}, File: {file.filename}")
    
    # Create project-specific directory
    project_dir = UPLOAD_DIR / f"project_{project_id}"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    file_path = project_dir / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved successfully: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Try async ingestion with Celery, fallback to sync if Redis unavailable
    try:
        logger.info(f"Attempting async ingestion for {file.filename}")
        
        # Try to submit task to Celery queue
        task = ingest_document_async.delay(
            project_id=project_id,
            file_path=str(file_path),
            filename=file.filename
        )
        
        logger.info(f"Ingestion task queued - Task ID: {task.id}, File: {file.filename}")
        
        # Return immediately with task ID (non-blocking)
        return DocumentUploadResponse(
            status="queued",
            message=f"Document upload successful. Ingestion started asynchronously.",
            document_id=None,  # Will be set when task completes
            chunks_created=0,
            embeddings_created=0,
            task_id=task.id  # Client can poll this for progress
        )
    
    except Exception as celery_error:
        # Celery/Redis not available - fallback to synchronous ingestion
        error_msg = (
            "⚠️ WARNING: Async processing unavailable - Redis/Celery not running. "
            "Using synchronous processing (slower). "
            "To enable async: Install Redis and start Celery worker."
        )
        logger.warning(f"{error_msg} Error: {celery_error}")
        
        try:
            logger.info(f"Starting synchronous ingestion for {file.filename}")
            print(f"\n{error_msg}\n")  # Print to console for visibility
            
            ingestion_service = IngestionService(session)
            result = await ingestion_service.ingest_document(
                project_id=project_id,
                file_path=file_path,
                filename=file.filename
            )
            
            logger.info(f"Synchronous ingestion completed - Document ID: {result.get('document_id')}")
            
            # Add warning message to response
            result['message'] = f"{result.get('message', '')} (Note: Processed synchronously - Redis unavailable)"
            return DocumentUploadResponse(**result)
        
        except Exception as ingestion_error:
            logger.error(f"Synchronous ingestion failed for {file.filename}: {ingestion_error}", exc_info=True)
            # Clean up file if ingestion fails
            if file_path.exists():
                file_path.unlink()
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion failed: {str(ingestion_error)}"
            )


@router.get(
    "/task/{task_id}/status",
    summary="Get status of an ingestion task"
)
async def get_task_status_endpoint(task_id: str):
    """
    Get the current status of a Celery ingestion task.
    
    States:
    - PENDING: Task is waiting in queue
    - PROGRESS: Task is currently processing (includes progress info)
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed permanently
    - RETRY: Task is being retried
    
    Returns progress information if task is in PROGRESS state.
    """
    try:
        status = get_task_status(task_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get(
    "/project/{project_id}/ingestion-status",
    response_model=IngestionStatusResponse,
    summary="Get ingestion status for a project"
)
async def get_project_ingestion_status(
    project_id: int,
    session: AsyncSession = Depends(get_db_session)
) -> IngestionStatusResponse:
    """
    Get the ingestion status of all documents in a project.
    
    Shows:
    - Total documents
    - Status breakdown (pending, processing, completed, failed)
    - Per-document details
    """
    try:
        ingestion_service = IngestionService(session)
        status_data = await ingestion_service.get_ingestion_status(project_id)
        
        return IngestionStatusResponse(**status_data)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion status: {str(e)}"
        )


@router.get(
    "/document/{document_id}/chunks",
    response_model=List[ChunkResponse],
    summary="Get all chunks for a document"
)
async def get_document_chunks(
    document_id: int,
    session: AsyncSession = Depends(get_db_session)
) -> List[ChunkResponse]:
    """
    Retrieve all text chunks for a specific document.
    
    Chunks are returned in order (by chunk_index).
    """
    try:
        chunk_repo = ChunkRepository(session)
        chunks = await chunk_repo.get_by_document(document_id)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No chunks found for document {document_id}"
            )
        
        # Convert to response schema
        chunk_responses = []
        for chunk in chunks:
            chunk_responses.append(ChunkResponse(
                id=chunk.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                char_count=chunk.char_count,
                start_page=chunk.start_page,
                end_page=chunk.end_page,
                has_embedding=chunk.embedding_metadata is not None
            ))
        
        return chunk_responses
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chunks: {str(e)}"
        )


@router.get(
    "/project/{project_id}/embeddings/count",
    response_model=EmbeddingCountResponse,
    summary="Get embedding count for a project"
)
async def get_embeddings_count(
    project_id: int,
    session: AsyncSession = Depends(get_db_session)
) -> EmbeddingCountResponse:
    """
    Get the total number of embeddings (chunks with vectors) for a project.
    
    This is useful for tracking ingestion progress and FAISS index size.
    """
    try:
        embedding_repo = EmbeddingMetadataRepository(session)
        
        async with session.begin():
            count = await embedding_repo.count_by_project(project_id)
        
        # Get model info from first embedding (if exists)
        model_name = None
        vector_dim = None
        
        if count > 0:
            # This is a simple query, we can use stub values or query from first record
            model_name = "stub-model"  # Will come from actual data
            vector_dim = 384
        
        return EmbeddingCountResponse(
            project_id=project_id,
            total_embeddings=count,
            model_name=model_name,
            vector_dimension=vector_dim
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count embeddings: {str(e)}"
        )
