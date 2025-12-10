"""
Pydantic schemas for Chat API
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import List


class ChatRequest(BaseModel):
    """Request model for chat query"""
    project_id: int = Field(..., description="Project ID to search within")
    message: str = Field(..., min_length=1, description="User's question or message")


class SourceChunk(BaseModel):
    """Retrieved source chunk with relevance score"""
    chunk_id: int = Field(..., description="Database ID of the chunk")
    score: float = Field(..., description="Relevance score (higher is better)")
    text: str = Field(..., description="Chunk text content")
    
    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    """Response model for chat query"""
    answer: str = Field(..., description="AI-generated answer")
    language: str = Field(default="en", description="Detected language of the response")
    sources: List[SourceChunk] = Field(default_factory=list, description="Retrieved source chunks")
    latency_ms: int = Field(..., description="Total processing time in milliseconds")
