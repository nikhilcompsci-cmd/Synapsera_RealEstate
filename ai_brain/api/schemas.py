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
