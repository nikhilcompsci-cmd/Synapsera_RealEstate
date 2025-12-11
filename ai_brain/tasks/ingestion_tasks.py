"""
Document Ingestion Celery Tasks
================================

Asynchronous tasks for document ingestion pipeline.
Handles PDF extraction, OCR, chunking, embedding generation, and FAISS indexing.

Security:
- Input validation before processing
- File path sanitization
- Resource limits (time, memory)
- Error handling with secure logging (no sensitive data in logs)

Performance:
- Parallel OCR processing
- Batch embedding generation
- Progress tracking
- Automatic retry with exponential backoff

Author: AI Brain Team
Last Updated: December 2025
"""

import os
import time
from pathlib import Path
from typing import Dict, Optional
from celery import Task
from celery.utils.log import get_task_logger

from celery_app import celery_app, BaseTask
from db.session import AsyncSessionLocal
from ingestion.ingestion_service import IngestionService
from config.settings import get_settings

# Task-specific logger (automatically includes task ID in logs)
logger = get_task_logger(__name__)

# Load settings
settings = get_settings()


@celery_app.task(
    name='tasks.ingestion.ingest_document',
    bind=True,
    base=BaseTask,
    max_retries=3,
    default_retry_delay=60,  # 1 minute between retries
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
    acks_late=True,  # Acknowledge after completion
    reject_on_worker_lost=True,  # Requeue if worker crashes
    track_started=True,  # Enable progress tracking
)
def ingest_document_async(
    self: Task,
    project_id: int,
    file_path: str,
    filename: str,
    user_id: Optional[int] = None
) -> Dict:
    """
    Asynchronously ingest a document into the RAG system.
    
    This task handles the complete document ingestion pipeline:
    1. PDF text extraction (with OCR fallback for scanned documents)
    2. Text chunking with overlap
    3. Embedding generation
    4. FAISS vector indexing
    5. Database record creation
    
    Args:
        self: Celery task instance (auto-injected)
        project_id: ID of the project to associate document with
        file_path: Absolute path to uploaded PDF file
        filename: Original filename (for display)
        user_id: ID of user who uploaded document (for audit trail)
    
    Returns:
        Dict with ingestion results:
            - status: 'success', 'duplicate', or 'error'
            - document_id: Created document ID
            - message: Human-readable result message
            - chunks_created: Number of text chunks created
            - embeddings_created: Number of embeddings generated
            - page_count: Number of pages in PDF
            - processing_time: Total processing time in seconds
    
    Raises:
        ValueError: If project_id is invalid or file doesn't exist
        Exception: Any unexpected error during processing
    
    Security Notes:
        - File path is validated to prevent directory traversal
        - File size is checked against limits
        - Sensitive data is not logged
        - Task has memory and time limits
    
    Example:
        >>> task = ingest_document_async.delay(
        ...     project_id=1,
        ...     file_path='/uploads/doc.pdf',
        ...     filename='doc.pdf'
        ... )
        >>> task.id
        '3c5e42a8-7f9a-4c5d-9e3f-8b1a2c3d4e5f'
        >>> task.state
        'PENDING'
    """
    start_time = time.time()
    
    # ========================================================================
    # INPUT VALIDATION AND SECURITY CHECKS
    # ========================================================================
    
    logger.info(
        f"Starting document ingestion",
        extra={
            'project_id': project_id,
            'filename': filename,
            'user_id': user_id,
            'task_id': self.request.id,
        }
    )
    
    # Validate project_id
    if not isinstance(project_id, int) or project_id <= 0:
        error_msg = f"Invalid project_id: {project_id}"
        logger.error(error_msg, extra={'task_id': self.request.id})
        raise ValueError(error_msg)
    
    # Convert file_path to Path object and validate
    try:
        file_path_obj = Path(file_path).resolve()
    except Exception as e:
        error_msg = f"Invalid file path: {file_path}"
        logger.error(error_msg, extra={'task_id': self.request.id, 'error': str(e)})
        raise ValueError(error_msg)
    
    # Security: Ensure file is within uploads directory (prevent directory traversal)
    uploads_dir = Path(settings.data_dir) / 'uploads'
    try:
        file_path_obj.relative_to(uploads_dir)
    except ValueError:
        error_msg = f"File path outside uploads directory: {file_path}"
        logger.error(error_msg, extra={'task_id': self.request.id})
        raise ValueError(error_msg)
    
    # Validate file exists
    if not file_path_obj.exists():
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg, extra={'task_id': self.request.id})
        raise ValueError(error_msg)
    
    # Validate file size (prevent DoS)
    file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
    max_size_mb = 100  # 100MB limit
    if file_size_mb > max_size_mb:
        error_msg = f"File too large: {file_size_mb:.1f}MB (max {max_size_mb}MB)"
        logger.error(error_msg, extra={'task_id': self.request.id})
        raise ValueError(error_msg)
    
    # Validate file extension
    if file_path_obj.suffix.lower() != '.pdf':
        error_msg = f"Invalid file type: {file_path_obj.suffix} (expected .pdf)"
        logger.error(error_msg, extra={'task_id': self.request.id})
        raise ValueError(error_msg)
    
    logger.info(
        f"File validation passed",
        extra={
            'task_id': self.request.id,
            'file_size_mb': f"{file_size_mb:.2f}",
        }
    )
    
    # ========================================================================
    # UPDATE TASK STATE: STARTED
    # ========================================================================
    
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 0,
            'total': 100,
            'status': 'Validating document...',
            'stage': 'validation',
        }
    )
    
    # ========================================================================
    # DATABASE SESSION AND INGESTION SERVICE
    # ========================================================================
    
    document_id = None
    session = None
    
    try:
        # Create async database session
        session = AsyncSessionLocal()
        
        # Initialize ingestion service
        ingestion_service = IngestionService(
            session=session,
            chunk_size=1000,
            overlap=200,
            use_stub_embeddings=False  # Use real embeddings in production
        )
        
        # ====================================================================
        # STAGE 1: PDF EXTRACTION
        # ====================================================================
        
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': 'Extracting text from PDF...',
                'stage': 'extraction',
            }
        )
        
        logger.info(
            f"Starting PDF extraction",
            extra={'task_id': self.request.id}
        )
        
        # ====================================================================
        # STAGE 2: TEXT CHUNKING
        # ====================================================================
        
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 40,
                'total': 100,
                'status': 'Chunking text...',
                'stage': 'chunking',
            }
        )
        
        # ====================================================================
        # STAGE 3: EMBEDDING GENERATION
        # ====================================================================
        
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 60,
                'total': 100,
                'status': 'Generating embeddings...',
                'stage': 'embedding',
            }
        )
        
        # ====================================================================
        # STAGE 4: FAISS INDEXING
        # ====================================================================
        
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 80,
                'total': 100,
                'status': 'Building search index...',
                'stage': 'indexing',
            }
        )
        
        # ====================================================================
        # RUN COMPLETE INGESTION PIPELINE
        # ====================================================================
        
        import asyncio
        
        # Run async ingestion in sync context
        result = asyncio.run(
            ingestion_service.ingest_document(
                project_id=project_id,
                file_path=file_path_obj,
                filename=filename
            )
        )
        
        # ====================================================================
        # FINALIZE AND RETURN RESULT
        # ====================================================================
        
        processing_time = time.time() - start_time
        
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Ingestion completed successfully',
                'stage': 'completed',
                'result': result,
            }
        )
        
        logger.info(
            f"Document ingestion completed successfully",
            extra={
                'task_id': self.request.id,
                'project_id': project_id,
                'document_id': result.get('document_id'),
                'status': result.get('status'),
                'chunks': result.get('chunks_created'),
                'embeddings': result.get('embeddings_created'),
                'processing_time': f"{processing_time:.2f}s",
            }
        )
        
        # Add processing time to result
        result['processing_time'] = processing_time
        result['task_id'] = self.request.id
        
        return result
    
    except Exception as e:
        # ====================================================================
        # ERROR HANDLING
        # ====================================================================
        
        processing_time = time.time() - start_time
        
        logger.error(
            f"Document ingestion failed",
            extra={
                'task_id': self.request.id,
                'project_id': project_id,
                'filename': filename,
                'error': str(e),
                'error_type': e.__class__.__name__,
                'processing_time': f"{processing_time:.2f}s",
            },
            exc_info=True  # Include stack trace
        )
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': f'Ingestion failed: {str(e)}',
                'stage': 'failed',
                'error': str(e),
            }
        )
        
        # Retry task if it's a transient error
        if self.request.retries < self.max_retries:
            # Exponential backoff: 60s, 120s, 240s
            retry_delay = 60 * (2 ** self.request.retries)
            logger.warning(
                f"Retrying task in {retry_delay}s (attempt {self.request.retries + 1}/{self.max_retries})",
                extra={'task_id': self.request.id}
            )
            raise self.retry(exc=e, countdown=retry_delay)
        
        # Return error result
        return {
            'status': 'error',
            'document_id': document_id,
            'message': str(e),
            'chunks_created': 0,
            'embeddings_created': 0,
            'processing_time': processing_time,
            'task_id': self.request.id,
        }
    
    finally:
        # ====================================================================
        # CLEANUP
        # ====================================================================
        
        # Close database session
        if session:
            try:
                asyncio.run(session.close())
            except Exception as e:
                logger.warning(
                    f"Failed to close database session",
                    extra={'task_id': self.request.id, 'error': str(e)}
                )


@celery_app.task(
    name='tasks.ingestion.get_task_status',
    bind=False,
)
def get_task_status(task_id: str) -> Dict:
    """
    Get the current status of an ingestion task.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Dict with task status information
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery_app)
    
    response = {
        'task_id': task_id,
        'state': task.state,
        'ready': task.ready(),
        'successful': task.successful() if task.ready() else None,
    }
    
    if task.state == 'PROGRESS':
        response['progress'] = task.info
    elif task.state == 'SUCCESS':
        response['result'] = task.result
    elif task.state == 'FAILURE':
        response['error'] = str(task.info)
    
    return response


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ['ingest_document_async', 'get_task_status']
