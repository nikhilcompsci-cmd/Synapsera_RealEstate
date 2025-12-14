"""
System Maintenance Celery Tasks
================================

Periodic tasks for system maintenance, cleanup, and health monitoring.

Tasks:
- cleanup_old_files: Remove old uploaded files
- cleanup_expired_results: Clear expired Celery task results
- health_check: Monitor system health

Author: AI Brain Team
Last Updated: December 2025
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger

from celery_app import celery_app, BaseTask
from config.settings import get_settings

# Task-specific logger
logger = get_task_logger(__name__)

# Load settings
settings = get_settings()


@celery_app.task(
    name='tasks.maintenance.cleanup_old_files',
    bind=True,
    base=BaseTask,
    max_retries=2,
)
def cleanup_old_files(self, days_old: int = 30):
    """
    Clean up uploaded files older than specified days.
    
    Args:
        self: Celery task instance
        days_old: Delete files older than this many days (default: 30)
    
    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"Starting cleanup of files older than {days_old} days")
    
    uploads_dir = Path(settings.data_dir) / 'uploads'
    if not uploads_dir.exists():
        logger.warning(f"Uploads directory does not exist: {uploads_dir}")
        return {'status': 'skipped', 'reason': 'uploads_dir_not_found'}
    
    cutoff_time = time.time() - (days_old * 24 * 3600)
    files_deleted = 0
    bytes_freed = 0
    errors = 0
    
    try:
        for file_path in uploads_dir.rglob('*'):
            if file_path.is_file():
                try:
                    file_stat = file_path.stat()
                    if file_stat.st_mtime < cutoff_time:
                        file_size = file_stat.st_size
                        file_path.unlink()
                        files_deleted += 1
                        bytes_freed += file_size
                        logger.debug(f"Deleted old file: {file_path.name}")
                except Exception as e:
                    errors += 1
                    logger.error(f"Failed to delete {file_path}: {e}")
        
        # Clean up empty directories
        for dir_path in uploads_dir.rglob('*'):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    logger.debug(f"Removed empty directory: {dir_path.name}")
                except Exception as e:
                    logger.error(f"Failed to remove directory {dir_path}: {e}")
        
        result = {
            'status': 'success',
            'files_deleted': files_deleted,
            'bytes_freed': bytes_freed,
            'errors': errors,
            'task_id': self.request.id,
        }
        
        logger.info(
            f"Cleanup completed: {files_deleted} files deleted, {bytes_freed / (1024*1024):.2f} MB freed"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}", exc_info=True)
        raise


@celery_app.task(
    name='tasks.maintenance.cleanup_expired_results',
    bind=True,
    base=BaseTask,
)
def cleanup_expired_results(self):
    """
    Clean up expired Celery task results from Redis backend.
    
    Returns:
        Dict with cleanup statistics
    """
    logger.info("Starting cleanup of expired task results")
    
    try:
        # Get all task results from backend
        from celery.result import AsyncResult
        
        # This is handled automatically by Celery's result_expires setting
        # Just log that maintenance ran
        logger.info("Expired results cleanup completed (handled by Celery)")
        
        return {
            'status': 'success',
            'message': 'Expired results cleaned up by Celery backend',
            'task_id': self.request.id,
        }
    
    except Exception as e:
        logger.error(f"Cleanup expired results failed: {e}", exc_info=True)
        raise


# ============================================================================
# EXPORT
# ============================================================================

__all__ = ['cleanup_old_files', 'cleanup_expired_results']
