from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


# Project Schemas
class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, max_length=1000, description="Project description")


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Document Schemas
class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""
    status: str = Field(..., description="queued, success, duplicate, or error")
    document_id: int | None = Field(None, description="ID of created/existing document")
    message: str
    chunks_created: int
    embeddings_created: int
    page_count: int | None = None
    task_id: str | None = Field(None, description="Celery task ID for async processing")


class DocumentInfo(BaseModel):
    """Schema for document information."""
    id: int
    filename: str
    status: str
    page_count: int | None
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class IngestionStatusResponse(BaseModel):
    """Schema for ingestion status response."""
    total_documents: int
    pending: int
    processing: int
    completed: int
    failed: int
    documents: List[DocumentInfo]


class ChunkResponse(BaseModel):
    """Schema for chunk response."""
    id: int
    chunk_index: int
    text: str
    char_count: int
    start_page: int | None
    end_page: int | None
    has_embedding: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class EmbeddingCountResponse(BaseModel):
    """Schema for embedding count response."""
    project_id: int
    total_embeddings: int
    model_name: str | None = None
    vector_dimension: int | None = None


# Health Check Schema
class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: datetime


# Failed Documents Schemas
class FailedDocumentResponse(BaseModel):
    """Schema for failed document response."""
    id: int
    project_id: int
    user_id: int | None
    filename: str
    file_size: int | None
    error_type: str
    error_message: str  # Sanitized
    status: str
    retry_count: int
    max_retries: int
    failed_stage: str | None
    processing_duration: float | None
    task_id: str | None
    created_at: datetime
    last_retry_at: datetime | None
    next_retry_at: datetime | None
    resolved_at: datetime | None
    resolution_notes: str | None
    
    model_config = ConfigDict(from_attributes=True)


class FailedDocumentListResponse(BaseModel):
    """Schema for paginated failed documents list."""
    items: List[FailedDocumentResponse]
    total_count: int
    limit: int
    offset: int


class RetryFailedDocumentRequest(BaseModel):
    """Schema for manual retry request."""
    retry_delay_seconds: int | None = Field(
        None,
        ge=0,
        le=3600,
        description="Delay before retry in seconds (0-3600). None = immediate"
    )


class UpdateFailedDocumentRequest(BaseModel):
    """Schema for updating failed document status."""
    status: str = Field(..., description="New status: resolved, permanently_failed, or ignored")
    resolution_notes: str | None = Field(None, max_length=1000, description="Notes about resolution")


class FailureMetricsResponse(BaseModel):
    """Schema for failure metrics response."""
    total_failures: int
    by_error_type: dict[str, int]
    by_status: dict[str, int]
    avg_retry_count: float
    success_rate: float
    time_window_days: int


class SystemHealthResponse(BaseModel):
    """Schema for comprehensive system health check."""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    celery_workers: int
    redis_connected: bool
    database_connected: bool
    failed_tasks_24h: int
    success_rate_24h: float
    avg_processing_time_seconds: float | None
    timestamp: datetime
