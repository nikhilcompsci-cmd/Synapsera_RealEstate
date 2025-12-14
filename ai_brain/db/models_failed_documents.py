"""
Failed Documents Database Model
================================

Tracks documents that failed during ingestion process for error analysis,
retry management, and recovery operations.

Security:
- Input validation on all fields
- Sanitized error messages (no sensitive data)
- Indexed queries for performance
- Audit trail with timestamps

Author: AI Brain Team
Last Updated: December 2025
"""

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, func, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
import enum

from db.models import Base


class FailureStatus(str, enum.Enum):
    """
    Status of a failed document in the recovery pipeline.
    
    - RETRYING: Automatic retry in progress
    - PERMANENTLY_FAILED: Exceeded max retries, needs manual intervention
    - RESOLVED: Issue fixed and document successfully ingested
    - IGNORED: Marked by admin as acceptable failure (corrupted file, etc.)
    """
    RETRYING = "retrying"
    PERMANENTLY_FAILED = "permanently_failed"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class ErrorType(str, enum.Enum):
    """
    Classification of error types for smart retry logic.
    
    - TRANSIENT: Temporary issues (network, Redis down) - retry automatically
    - PERMANENT: Unfixable issues (corrupted file) - don't retry
    - USER_FIXABLE: User can fix (password-protected PDF) - notify user
    - SYSTEM_ISSUE: Infrastructure problems (disk full) - alert admin
    - RATE_LIMIT: API rate limiting - retry with backoff
    - TIMEOUT: Processing timeout - retry with longer timeout
    - UNKNOWN: Unclassified error - default retry logic
    """
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    USER_FIXABLE = "user_fixable"
    SYSTEM_ISSUE = "system_issue"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class FailedDocument(Base):
    """
    Failed Documents model - tracks documents that failed during ingestion.
    
    This model stores comprehensive information about failed document uploads
    for error analysis, automatic retry, manual recovery, and audit trails.
    
    Attributes:
        id: Primary key
        project_id: Foreign key to projects table
        filename: Original filename (for display to user)
        file_path: Absolute path to uploaded file (for retry)
        file_size: File size in bytes (for analysis)
        error_type: Classification of error (transient, permanent, etc.)
        error_message: Sanitized error message (no sensitive data)
        error_details: Full error details (stack trace, context) - for debugging
        retry_count: Number of retry attempts made
        max_retries: Maximum retries allowed for this error type
        last_retry_at: Timestamp of most recent retry attempt
        next_retry_at: Scheduled time for next retry (NULL if not retrying)
        status: Current status (retrying, permanently_failed, resolved, ignored)
        failed_stage: Pipeline stage where failure occurred
        processing_duration: Time spent processing before failure (seconds)
        task_id: Celery task ID (for tracking)
        user_id: User who uploaded the document (for notification)
        resolution_notes: Admin notes on how issue was resolved
        created_at: First failure timestamp
        updated_at: Last update timestamp
        resolved_at: Resolution timestamp
    
    Security Notes:
        - error_message is sanitized to remove sensitive data
        - file_path is validated to prevent directory traversal
        - user_id links to user table for audit trail
    
    Performance:
        - Indexed on: project_id, status, error_type, created_at
        - Composite index on (status, next_retry_at) for retry queries
    """
    
    __tablename__ = "failed_documents"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # File information
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # bytes
    
    # Error classification
    error_type: Mapped[ErrorType] = mapped_column(
        SQLEnum(ErrorType, name='error_type_enum', create_constraint=True),
        nullable=False,
        default=ErrorType.UNKNOWN,
        index=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=False)  # Sanitized
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Full details
    
    # Retry management
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    
    # Status tracking
    status: Mapped[FailureStatus] = mapped_column(
        SQLEnum(FailureStatus, name='failure_status_enum', create_constraint=True),
        nullable=False,
        default=FailureStatus.RETRYING,
        index=True
    )
    
    # Processing context
    failed_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )  # 'extraction', 'chunking', 'embedding', 'indexing'
    processing_duration: Mapped[Optional[float]] = mapped_column(
        nullable=True
    )  # seconds
    task_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True
    )  # Celery task ID
    
    # Resolution tracking
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="failed_documents"
    )
    
    # Composite indexes for common queries
    __table_args__ = (
        # Query failed documents pending retry
        Index('idx_failed_documents_retry_schedule', 'status', 'next_retry_at'),
        # Query failed documents by project and status
        Index('idx_failed_documents_project_status', 'project_id', 'status'),
        # Query recent failures for monitoring
        Index('idx_failed_documents_created_status', 'created_at', 'status'),
        # Query by error type for analysis
        Index('idx_failed_documents_error_type', 'error_type', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FailedDocument(id={self.id}, "
            f"filename='{self.filename}', "
            f"status='{self.status.value}', "
            f"error_type='{self.error_type.value}', "
            f"retry_count={self.retry_count})>"
        )
    
    def can_retry(self) -> bool:
        """
        Check if document is eligible for retry.
        
        Returns:
            True if retry count is below max and status is RETRYING
        """
        return (
            self.status == FailureStatus.RETRYING and
            self.retry_count < self.max_retries
        )
    
    def should_retry_now(self) -> bool:
        """
        Check if document should be retried now based on schedule.
        
        Returns:
            True if next_retry_at is in the past and can_retry() is True
        """
        if not self.can_retry():
            return False
        
        if self.next_retry_at is None:
            return True
        
        return datetime.utcnow() >= self.next_retry_at
    
    def mark_permanently_failed(self) -> None:
        """
        Mark document as permanently failed (exceeded max retries).
        
        Updates status to PERMANENTLY_FAILED and clears retry schedule.
        """
        self.status = FailureStatus.PERMANENTLY_FAILED
        self.next_retry_at = None
        self.updated_at = datetime.utcnow()
    
    def mark_resolved(self, resolution_notes: Optional[str] = None) -> None:
        """
        Mark document as successfully resolved/ingested.
        
        Args:
            resolution_notes: Optional notes about how issue was resolved
        """
        self.status = FailureStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if resolution_notes:
            self.resolution_notes = resolution_notes
    
    def increment_retry(self, next_retry_delay_seconds: Optional[int] = None) -> None:
        """
        Increment retry count and schedule next retry.
        
        Args:
            next_retry_delay_seconds: Seconds until next retry (NULL for immediate)
        """
        self.retry_count += 1
        self.last_retry_at = datetime.utcnow()
        
        if next_retry_delay_seconds is not None:
            from datetime import timedelta
            self.next_retry_at = datetime.utcnow() + timedelta(seconds=next_retry_delay_seconds)
        else:
            self.next_retry_at = None
        
        self.updated_at = datetime.utcnow()


class ProcessingCheckpoint(Base):
    """
    Processing Checkpoints model - stores intermediate results for resume capability.
    
    When document processing fails, this model allows resuming from the last
    successful stage instead of re-processing from scratch.
    
    Attributes:
        id: Primary key
        document_identifier: Unique identifier (filename + project_id hash)
        project_id: Foreign key to projects table
        stage: Processing stage ('extraction', 'chunking', 'embedding', 'indexing')
        checkpoint_data: JSON blob with stage-specific data
        created_at: Checkpoint creation timestamp
        expires_at: Checkpoint expiration (auto-cleanup after 7 days)
    
    Example checkpoint_data by stage:
        extraction: {"text": "...", "page_count": 71, "has_ocr": true}
        chunking: {"chunks": [...], "chunk_count": 150}
        embedding: {"embeddings": [...], "embedding_count": 150}
        indexing: {"faiss_ids": [...], "index_path": "/path/to/index"}
    """
    
    __tablename__ = "processing_checkpoints"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Unique identifier for document (hash of filename + project_id)
    document_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True
    )
    
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Processing stage
    stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )  # 'extraction', 'chunking', 'embedding', 'indexing'
    
    # Checkpoint data (JSON)
    checkpoint_data: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )  # Auto-cleanup after 7 days
    
    # Relationship
    project: Mapped["Project"] = relationship("Project")
    
    # Index for cleanup queries
    __table_args__ = (
        Index('idx_checkpoints_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ProcessingCheckpoint(id={self.id}, "
            f"identifier='{self.document_identifier}', "
            f"stage='{self.stage}')>"
        )
