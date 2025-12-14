"""
Sentry Integration for Error Tracking and Monitoring
===================================================

Provides centralized error tracking, performance monitoring,
and admin alerts through Sentry.io

Features:
- Automatic error capture and reporting
- Performance transaction tracking
- User context tracking
- Custom tags for filtering (environment, error_type, etc.)
- Admin email/Slack notifications (configured in Sentry dashboard)
- Release tracking and error trends

Setup:
1. Create account at https://sentry.io
2. Create new project (Python/FastAPI)
3. Copy DSN to .env: SENTRY_DSN=https://...
4. Set SENTRY_ENABLED=true in .env

Author: AI Brain Team
Date: December 2025
"""

import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def init_sentry(
    dsn: str,
    environment: str = "development",
    traces_sample_rate: float = 1.0,
    enabled: bool = True,
    release: Optional[str] = None
) -> bool:
    """
    Initialize Sentry SDK for error tracking and monitoring.
    
    Args:
        dsn: Sentry Data Source Name (get from Sentry project settings)
        environment: Environment name (development, staging, production)
        traces_sample_rate: Percentage of transactions to capture (0.0 to 1.0)
        enabled: Whether to enable Sentry
        release: Release version (defaults to app version)
    
    Returns:
        bool: True if Sentry initialized successfully, False otherwise
    
    Example:
        >>> init_sentry(
        ...     dsn="https://abc123@o123.ingest.sentry.io/456",
        ...     environment="production",
        ...     traces_sample_rate=0.1  # 10% of transactions
        ... )
    """
    if not enabled:
        logger.info("Sentry is disabled (SENTRY_ENABLED=false)")
        return False
    
    if not dsn:
        logger.warning("Sentry DSN not configured - error tracking disabled")
        logger.info("To enable Sentry:")
        logger.info("  1. Sign up at https://sentry.io")
        logger.info("  2. Create a new Python project")
        logger.info("  3. Copy DSN to .env: SENTRY_DSN=https://...")
        logger.info("  4. Set SENTRY_ENABLED=true")
        return False
    
    try:
        # Configure logging integration
        # This sends ERROR and CRITICAL logs to Sentry
        logging_integration = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors and above as events
        )
        
        # Initialize Sentry
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="url"),  # FastAPI request tracking
                CeleryIntegration(),                          # Celery task tracking
                SqlalchemyIntegration(),                      # Database query tracking
                logging_integration,                          # Automatic log capture
            ],
            
            # Performance monitoring
            enable_tracing=True,
            
            # Error filtering - send everything in production, less in dev
            before_send=lambda event, hint: filter_event(event, hint, environment),
            
            # Attach stack locals for better debugging
            attach_stacktrace=True,
            
            # Send default PII (personally identifiable information)
            send_default_pii=False,  # Set to True if you want user IPs, etc.
        )
        
        logger.info(f"✅ Sentry initialized successfully")
        logger.info(f"   Environment: {environment}")
        logger.info(f"   Traces sample rate: {traces_sample_rate * 100}%")
        logger.info(f"   Release: {release or 'not set'}")
        
        # Test Sentry connection
        sentry_sdk.capture_message(
            f"Sentry initialized for {environment}",
            level="info"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def filter_event(event: Dict[str, Any], hint: Dict[str, Any], environment: str) -> Optional[Dict[str, Any]]:
    """
    Filter events before sending to Sentry.
    
    Use this to:
    - Filter out noise in development
    - Redact sensitive information
    - Add custom tags
    
    Args:
        event: Sentry event dictionary
        hint: Event hint with exception info
        environment: Current environment
    
    Returns:
        Modified event dict, or None to drop the event
    """
    # In development, only send errors and critical
    if environment == "development":
        level = event.get('level')
        if level in ['debug', 'info', 'warning']:
            return None  # Drop non-error events in dev
    
    # Add custom tags for better filtering in Sentry dashboard
    event.setdefault('tags', {})
    
    # Tag errors from specific modules
    if 'exception' in event:
        exc_type = event['exception']['values'][0]['type'] if event['exception'].get('values') else 'Unknown'
        event['tags']['error_type'] = exc_type
    
    return event


def capture_exception_with_context(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    level: str = "error"
) -> None:
    """
    Capture an exception with additional context and tags.
    
    This sends the error to Sentry with custom metadata for better debugging.
    
    Args:
        exception: The exception to capture
        context: Additional context (user_id, project_id, etc.)
        tags: Custom tags for filtering (error_type, stage, etc.)
        level: Error level (info, warning, error, fatal)
    
    Example:
        >>> try:
        ...     process_document(file_path)
        ... except Exception as e:
        ...     capture_exception_with_context(
        ...         exception=e,
        ...         context={
        ...             'filename': 'document.pdf',
        ...             'project_id': 123,
        ...             'user_id': 456
        ...         },
        ...         tags={
        ...             'error_type': 'transient',
        ...             'stage': 'pdf_extraction'
        ...         }
        ...     )
    """
    # Set context
    if context:
        sentry_sdk.set_context("additional_info", context)
    
    # Set tags
    if tags:
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)
    
    # Capture exception
    sentry_sdk.capture_exception(exception, level=level)
    
    logger.error(
        f"Exception captured by Sentry: {exception}",
        extra={'context': context, 'tags': tags}
    )


def capture_message_with_context(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Capture a message (non-exception event) in Sentry.
    
    Use this for important events that aren't errors:
    - Admin alerts
    - Critical state changes
    - Performance issues
    
    Args:
        message: The message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context
        tags: Custom tags
    
    Example:
        >>> capture_message_with_context(
        ...     message="Rate limit exceeded for API",
        ...     level="warning",
        ...     context={'api': 'OpenAI', 'project_id': 123},
        ...     tags={'alert_type': 'rate_limit'}
        ... )
    """
    # Set context
    if context:
        sentry_sdk.set_context("additional_info", context)
    
    # Set tags
    if tags:
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)
    
    # Capture message
    sentry_sdk.capture_message(message, level=level)
    
    logger.info(
        f"Message captured by Sentry: {message}",
        extra={'level': level, 'context': context, 'tags': tags}
    )


def set_user_context(user_id: int, email: Optional[str] = None, username: Optional[str] = None) -> None:
    """
    Set user context for error tracking.
    
    This helps track which users are experiencing errors.
    
    Args:
        user_id: User ID
        email: User email (optional)
        username: Username (optional)
    
    Example:
        >>> set_user_context(user_id=123, email="user@example.com")
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username
    })


def clear_user_context() -> None:
    """Clear user context (e.g., after logout)."""
    sentry_sdk.set_user(None)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a breadcrumb for error context.
    
    Breadcrumbs are events leading up to an error, helping debug the issue.
    
    Args:
        message: Breadcrumb message
        category: Category (navigation, http, database, etc.)
        level: Level (debug, info, warning, error)
        data: Additional data
    
    Example:
        >>> add_breadcrumb(
        ...     message="User uploaded document",
        ...     category="upload",
        ...     data={'filename': 'contract.pdf', 'size': 1024000}
        ... )
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


# Convenience functions for common use cases

def alert_admin(
    message: str,
    error_type: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Send an admin alert to Sentry.
    
    These appear as warnings/errors in Sentry and can trigger
    email/Slack notifications (configured in Sentry dashboard).
    
    Args:
        message: Alert message
        error_type: Type of error (system_issue, rate_limit, etc.)
        context: Additional context
    
    Example:
        >>> alert_admin(
        ...     message="Redis connection lost",
        ...     error_type="system_issue",
        ...     context={'service': 'redis', 'attempts': 3}
        ... )
    """
    capture_message_with_context(
        message=f"⚠️ ADMIN ALERT: {message}",
        level="error",
        context=context,
        tags={
            'alert_type': 'admin',
            'error_type': error_type
        }
    )


def track_failed_document(
    filename: str,
    error_type: str,
    error_message: str,
    project_id: int,
    user_id: Optional[int] = None
) -> None:
    """
    Track a failed document ingestion in Sentry.
    
    Args:
        filename: Document filename
        error_type: Error classification
        error_message: Error message
        project_id: Project ID
        user_id: User ID (optional)
    
    Example:
        >>> track_failed_document(
        ...     filename="contract.pdf",
        ...     error_type="transient",
        ...     error_message="Redis timeout",
        ...     project_id=123,
        ...     user_id=456
        ... )
    """
    capture_message_with_context(
        message=f"Document ingestion failed: {filename}",
        level="warning",
        context={
            'filename': filename,
            'error_message': error_message,
            'project_id': project_id,
            'user_id': user_id
        },
        tags={
            'event_type': 'failed_document',
            'error_type': error_type
        }
    )
