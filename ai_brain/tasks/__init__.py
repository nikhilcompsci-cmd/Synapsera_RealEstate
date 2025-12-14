"""
Celery Tasks Package
====================

This package contains all Celery async tasks for the AI Brain application.

Tasks are organized by functionality:
- ingestion_tasks: Document ingestion and processing
- maintenance_tasks: Cleanup and system maintenance

Author: AI Brain Team
"""

from tasks.ingestion_tasks import ingest_document_async
from tasks.maintenance_tasks import cleanup_old_files, cleanup_expired_results

__all__ = [
    'ingest_document_async',
    'cleanup_old_files',
    'cleanup_expired_results',
]
