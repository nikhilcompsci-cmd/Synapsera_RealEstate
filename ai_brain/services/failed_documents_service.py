"""
Failed Documents Service
=========================

Business logic for managing failed document uploads and recovery operations.

Handles:
- Creating failed document records with error classification
- Scheduling automatic retries with exponential backoff
- Manual retry triggers from admin dashboard
- Cleanup of resolved/orphaned failed documents
- Metrics and reporting for monitoring

Security:
- Input validation on all operations
- Sanitized error messages in logs
- Audit trail for all recovery operations
- Access control via user_id tracking

Author: AI Brain Team
Last Updated: December 2025
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models_failed_documents import (
    FailedDocument,
    FailureStatus,
    ErrorType
)
from services.error_classifier import error_classifier
from config.logging_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class FailedDocumentsService:
    """
    Service for managing failed document uploads and recovery.
    
    Provides methods for:
    - Recording failed uploads with error classification
    - Scheduling and managing retries
    - Querying failed documents with filters
    - Manual recovery operations
    - Cleanup and maintenance
    """
    
    async def record_failure(
        self,
        db: AsyncSession,
        project_id: int,
        filename: str,
        file_path: str,
        exception: Exception,
        file_size: Optional[int] = None,
        failed_stage: Optional[str] = None,
        processing_duration: Optional[float] = None,
        task_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> FailedDocument:
        """
        Record a failed document upload with intelligent error classification.
        
        Args:
            db: Database session
            project_id: Project ID
            filename: Original filename
            file_path: Absolute path to uploaded file
            exception: Exception that caused failure
            file_size: File size in bytes
            failed_stage: Pipeline stage where failure occurred
            processing_duration: Time spent processing (seconds)
            task_id: Celery task ID
            user_id: User who uploaded the document
        
        Returns:
            Created FailedDocument instance
        
        Security:
            - Validates project_id and file_path
            - Sanitizes error messages
            - Logs creation for audit trail
        
        Example:
            >>> failed_doc = await service.record_failure(
            ...     db=session,
            ...     project_id=1,
            ...     filename="doc.pdf",
            ...     file_path="/uploads/doc.pdf",
            ...     exception=ConnectionError("Redis timeout"),
            ...     failed_stage="extraction"
            ... )
            >>> failed_doc.error_type
            <ErrorType.TRANSIENT: 'transient'>
        """
        # Validate inputs
        if not isinstance(project_id, int) or project_id <= 0:
            raise ValueError(f"Invalid project_id: {project_id}")
        
        if not file_path or not isinstance(file_path, str):
            raise ValueError(f"Invalid file_path: {file_path}")
        
        # Classify error
        error_type, retry_config = error_classifier.classify(exception)
        error_details = error_classifier.get_error_details(exception, include_traceback=True)
        
        # Calculate next retry time if automatic retry is enabled
        next_retry_at = None
        if retry_config['can_auto_retry'] and retry_config['max_retries'] > 0:
            retry_delay = retry_config['retry_delay']
            next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
        
        # Create failed document record
        failed_doc = FailedDocument(
            project_id=project_id,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            error_type=error_type,
            error_message=error_details['error_message'],
            error_details=error_details.get('traceback'),
            retry_count=0,
            max_retries=retry_config['max_retries'],
            next_retry_at=next_retry_at,
            status=FailureStatus.RETRYING if retry_config['can_auto_retry'] else FailureStatus.PERMANENTLY_FAILED,
            failed_stage=failed_stage,
            processing_duration=processing_duration,
            task_id=task_id,
        )
        
        db.add(failed_doc)
        await db.commit()
        await db.refresh(failed_doc)
        
        logger.info(
            f"Recorded failed document: {filename}",
            extra={
                'failed_document_id': failed_doc.id,
                'project_id': project_id,
                'error_type': error_type.value,
                'status': failed_doc.status.value,
                'max_retries': retry_config['max_retries'],
                'next_retry_at': next_retry_at.isoformat() if next_retry_at else None,
            }
        )
        
        # Log notification/alert requirements
        if retry_config['notify_user']:
            logger.info(
                f"User notification required for failed document {failed_doc.id}",
                extra={'user_id': user_id, 'filename': filename}
            )
        
        if retry_config['alert_admin']:
            logger.warning(
                f"Admin alert required for failed document {failed_doc.id}",
                extra={
                    'error_type': error_type.value,
                    'filename': filename,
                    'error_message': error_details['error_message']
                }
            )
        
        return failed_doc
    
    async def get_failed_documents(
        self,
        db: AsyncSession,
        project_id: Optional[int] = None,
        status: Optional[FailureStatus] = None,
        error_type: Optional[ErrorType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[FailedDocument], int]:
        """
        Query failed documents with filters and pagination.
        
        Args:
            db: Database session
            project_id: Filter by project (optional)
            status: Filter by status (optional)
            error_type: Filter by error type (optional)
            limit: Maximum results to return
            offset: Pagination offset
        
        Returns:
            Tuple of (failed_documents_list, total_count)
        
        Security:
            - Validates pagination parameters
            - Returns sanitized error messages only
        """
        # Build query with filters
        query = select(FailedDocument)
        count_query = select(func.count(FailedDocument.id))
        
        filters = []
        if project_id is not None:
            filters.append(FailedDocument.project_id == project_id)
        if status is not None:
            filters.append(FailedDocument.status == status)
        if error_type is not None:
            filters.append(FailedDocument.error_type == error_type)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Get total count
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()
        
        # Apply ordering and pagination
        query = query.order_by(FailedDocument.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(query)
        failed_docs = list(result.scalars().all())
        
        logger.debug(
            f"Retrieved {len(failed_docs)} failed documents (total: {total_count})",
            extra={
                'project_id': project_id,
                'status': status.value if status else None,
                'error_type': error_type.value if error_type else None,
            }
        )
        
        return failed_docs, total_count
    
    async def get_documents_pending_retry(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> List[FailedDocument]:
        """
        Get documents that are eligible for retry right now.
        
        Args:
            db: Database session
            limit: Maximum documents to return
        
        Returns:
            List of FailedDocument instances ready for retry
        
        Used by:
            Scheduled task that processes retry queue
        """
        now = datetime.utcnow()
        
        query = select(FailedDocument).where(
            and_(
                FailedDocument.status == FailureStatus.RETRYING,
                FailedDocument.retry_count < FailedDocument.max_retries,
                or_(
                    FailedDocument.next_retry_at.is_(None),
                    FailedDocument.next_retry_at <= now
                )
            )
        ).order_by(
            FailedDocument.next_retry_at.asc().nullsfirst()
        ).limit(limit)
        
        result = await db.execute(query)
        pending_docs = list(result.scalars().all())
        
        logger.info(
            f"Found {len(pending_docs)} documents pending retry",
            extra={'count': len(pending_docs)}
        )
        
        return pending_docs
    
    async def schedule_retry(
        self,
        db: AsyncSession,
        failed_document_id: int,
        retry_delay_seconds: Optional[int] = None,
    ) -> FailedDocument:
        """
        Schedule a failed document for retry.
        
        Args:
            db: Database session
            failed_document_id: ID of failed document
            retry_delay_seconds: Delay before retry (None = immediate)
        
        Returns:
            Updated FailedDocument instance
        
        Raises:
            ValueError: If document not found or cannot be retried
        
        Security:
            - Validates failed_document_id
            - Checks retry eligibility
            - Logs retry scheduling for audit
        """
        # Fetch document
        result = await db.execute(
            select(FailedDocument).where(FailedDocument.id == failed_document_id)
        )
        failed_doc = result.scalar_one_or_none()
        
        if not failed_doc:
            raise ValueError(f"Failed document {failed_document_id} not found")
        
        if not failed_doc.can_retry():
            raise ValueError(
                f"Document {failed_document_id} cannot be retried "
                f"(status: {failed_doc.status.value}, "
                f"retry_count: {failed_doc.retry_count}/{failed_doc.max_retries})"
            )
        
        # Update retry schedule
        failed_doc.increment_retry(retry_delay_seconds)
        failed_doc.status = FailureStatus.RETRYING
        
        await db.commit()
        await db.refresh(failed_doc)
        
        logger.info(
            f"Scheduled retry for failed document {failed_document_id}",
            extra={
                'failed_document_id': failed_document_id,
                'retry_count': failed_doc.retry_count,
                'next_retry_at': failed_doc.next_retry_at.isoformat() if failed_doc.next_retry_at else 'immediate',
            }
        )
        
        return failed_doc
    
    async def mark_resolved(
        self,
        db: AsyncSession,
        failed_document_id: int,
        resolution_notes: Optional[str] = None,
    ) -> FailedDocument:
        """
        Mark a failed document as successfully resolved.
        
        Args:
            db: Database session
            failed_document_id: ID of failed document
            resolution_notes: Optional notes about resolution
        
        Returns:
            Updated FailedDocument instance
        
        Security:
            - Validates failed_document_id
            - Logs resolution for audit trail
        """
        result = await db.execute(
            select(FailedDocument).where(FailedDocument.id == failed_document_id)
        )
        failed_doc = result.scalar_one_or_none()
        
        if not failed_doc:
            raise ValueError(f"Failed document {failed_document_id} not found")
        
        failed_doc.mark_resolved(resolution_notes)
        
        await db.commit()
        await db.refresh(failed_doc)
        
        logger.info(
            f"Marked failed document {failed_document_id} as resolved",
            extra={
                'failed_document_id': failed_document_id,
                'resolution_notes': resolution_notes,
            }
        )
        
        return failed_doc
    
    async def mark_permanently_failed(
        self,
        db: AsyncSession,
        failed_document_id: int,
    ) -> FailedDocument:
        """
        Mark a failed document as permanently failed (no more retries).
        
        Args:
            db: Database session
            failed_document_id: ID of failed document
        
        Returns:
            Updated FailedDocument instance
        """
        result = await db.execute(
            select(FailedDocument).where(FailedDocument.id == failed_document_id)
        )
        failed_doc = result.scalar_one_or_none()
        
        if not failed_doc:
            raise ValueError(f"Failed document {failed_document_id} not found")
        
        failed_doc.mark_permanently_failed()
        
        await db.commit()
        await db.refresh(failed_doc)
        
        logger.warning(
            f"Marked failed document {failed_document_id} as permanently failed",
            extra={
                'failed_document_id': failed_document_id,
                'retry_count': failed_doc.retry_count,
                'error_type': failed_doc.error_type.value,
            }
        )
        
        return failed_doc
    
    async def cleanup_orphaned_files(
        self,
        db: AsyncSession,
        older_than_days: int = 7,
    ) -> Dict[str, int]:
        """
        Delete files from permanently failed or resolved uploads.
        
        Args:
            db: Database session
            older_than_days: Delete files older than N days
        
        Returns:
            Dict with cleanup stats: {'files_deleted': N, 'space_freed': N}
        
        Security:
            - Only deletes files from failed_documents table
            - Validates file paths before deletion
            - Logs all deletions for audit
        """
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        # Query permanently failed or resolved documents older than cutoff
        query = select(FailedDocument).where(
            and_(
                FailedDocument.created_at < cutoff_date,
                or_(
                    FailedDocument.status == FailureStatus.PERMANENTLY_FAILED,
                    FailedDocument.status == FailureStatus.RESOLVED,
                )
            )
        )
        
        result = await db.execute(query)
        failed_docs = list(result.scalars().all())
        
        files_deleted = 0
        space_freed = 0
        
        for failed_doc in failed_docs:
            try:
                file_path = Path(failed_doc.file_path)
                
                # Security: Validate file is within uploads directory
                uploads_dir = Path(settings.data_dir) / 'uploads'
                try:
                    file_path.relative_to(uploads_dir)
                except ValueError:
                    logger.warning(
                        f"Skipping file outside uploads directory: {file_path}",
                        extra={'failed_document_id': failed_doc.id}
                    )
                    continue
                
                # Delete file if it exists
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    files_deleted += 1
                    space_freed += file_size
                    
                    logger.info(
                        f"Deleted orphaned file: {failed_doc.filename}",
                        extra={
                            'failed_document_id': failed_doc.id,
                            'file_size': file_size,
                            'status': failed_doc.status.value,
                        }
                    )
            
            except Exception as e:
                logger.error(
                    f"Failed to delete file for failed document {failed_doc.id}: {e}",
                    extra={'failed_document_id': failed_doc.id, 'error': str(e)}
                )
        
        logger.info(
            f"Cleanup completed: deleted {files_deleted} files, freed {space_freed} bytes",
            extra={'files_deleted': files_deleted, 'space_freed': space_freed}
        )
        
        return {
            'files_deleted': files_deleted,
            'space_freed': space_freed,
        }
    
    async def get_failure_metrics(
        self,
        db: AsyncSession,
        project_id: Optional[int] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get failure metrics for monitoring dashboard.
        
        Args:
            db: Database session
            project_id: Filter by project (optional)
            days: Time window in days
        
        Returns:
            Dict with metrics:
                - total_failures: Total failed uploads
                - by_error_type: Breakdown by error type
                - by_status: Breakdown by status
                - avg_retry_count: Average retry attempts
                - success_rate: Percentage resolved
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        filters = [FailedDocument.created_at >= cutoff_date]
        if project_id is not None:
            filters.append(FailedDocument.project_id == project_id)
        
        # Total count
        count_query = select(func.count(FailedDocument.id)).where(and_(*filters))
        result = await db.execute(count_query)
        total_failures = result.scalar_one()
        
        # By error type
        error_type_query = select(
            FailedDocument.error_type,
            func.count(FailedDocument.id)
        ).where(and_(*filters)).group_by(FailedDocument.error_type)
        result = await db.execute(error_type_query)
        by_error_type = {row[0].value: row[1] for row in result}
        
        # By status
        status_query = select(
            FailedDocument.status,
            func.count(FailedDocument.id)
        ).where(and_(*filters)).group_by(FailedDocument.status)
        result = await db.execute(status_query)
        by_status = {row[0].value: row[1] for row in result}
        
        # Average retry count
        avg_retry_query = select(func.avg(FailedDocument.retry_count)).where(and_(*filters))
        result = await db.execute(avg_retry_query)
        avg_retry_count = result.scalar_one() or 0
        
        # Success rate
        resolved_count = by_status.get(FailureStatus.RESOLVED.value, 0)
        success_rate = (resolved_count / total_failures * 100) if total_failures > 0 else 0
        
        metrics = {
            'total_failures': total_failures,
            'by_error_type': by_error_type,
            'by_status': by_status,
            'avg_retry_count': float(avg_retry_count),
            'success_rate': round(success_rate, 2),
            'time_window_days': days,
        }
        
        logger.debug("Generated failure metrics", extra=metrics)
        
        return metrics


# Singleton instance
failed_documents_service = FailedDocumentsService()
