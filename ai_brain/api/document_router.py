from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import shutil
from typing import List

from db.session import get_db_session
from db.repositories.chunk_repository import ChunkRepository
from db.repositories.embedding_metadata_repository import EmbeddingMetadataRepository
from ingestion.ingestion_service import IngestionService
from api.schemas import (
    DocumentUploadResponse,
    IngestionStatusResponse,
    ChunkResponse,
    EmbeddingCountResponse
)

router = APIRouter(tags=["Documents"])

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Create project-specific directory
    project_dir = UPLOAD_DIR / f"project_{project_id}"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file
    file_path = project_dir / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Run ingestion pipeline
    try:
        ingestion_service = IngestionService(session)
        result = await ingestion_service.ingest_document(
            project_id=project_id,
            file_path=file_path,
            filename=file.filename
        )
        
        return DocumentUploadResponse(**result)
    
    except Exception as e:
        # Clean up file if ingestion fails
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.get(
    "/project/{project_id}/ingestion-status",
    response_model=IngestionStatusResponse,
    summary="Get ingestion status for a project"
)
async def get_ingestion_status(
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
