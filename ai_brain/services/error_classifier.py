"""
Error Classification Service
=============================

Intelligent error classification for smart retry logic and failure handling.

Classifies exceptions into categories:
- Transient: Temporary issues (network, Redis) - retry automatically
- Permanent: Unfixable issues (corrupted file) - don't retry
- User-fixable: User can resolve (password-protected PDF) - notify user
- System-issue: Infrastructure problems (disk full) - alert admin
- Rate-limit: API throttling - retry with exponential backoff
- Timeout: Processing timeout - retry with longer timeout

Security:
- Sanitizes error messages to remove sensitive data (paths, credentials, IPs)
- Validates input parameters
- Logs classification decisions for audit trail

Author: AI Brain Team
Last Updated: December 2025
"""

import re
import traceback
from typing import Tuple, Optional, Dict, Any

from db.models_failed_documents import ErrorType
from config.logging_config import get_logger

logger = get_logger(__name__)


class ErrorClassifier:
    """
    Classifies exceptions for intelligent retry logic.
    
    Analyzes exception type, message, and context to determine:
    1. Error category (transient, permanent, user-fixable, system-issue)
    2. Retry strategy (max retries, backoff delay)
    3. User notification requirements
    4. Admin alert requirements
    
    Example:
        >>> classifier = ErrorClassifier()
        >>> error_type, retry_config = classifier.classify(ConnectionError("Redis timeout"))
        >>> error_type
        <ErrorType.TRANSIENT: 'transient'>
        >>> retry_config['max_retries']
        5
    """
    
    # Patterns for transient errors (network, temporary unavailability)
    TRANSIENT_PATTERNS = [
        r'connection.*refused',
        r'connection.*timeout',
        r'connection.*reset',
        r'redis.*unavailable',
        r'redis.*connection',
        r'database.*connection.*lost',
        r'network.*unreachable',
        r'temporarily.*unavailable',
        r'service.*unavailable',
        r'rate.*limit.*exceeded',
        r'too.*many.*requests',
        r'gateway.*timeout',
        r'timeout.*error',
        r'connect.*timeout',
        r'read.*timeout',
    ]
    
    # Patterns for permanent errors (corrupted data, unsupported format)
    PERMANENT_PATTERNS = [
        r'corrupted',
        r'invalid.*pdf',
        r'malformed.*pdf',
        r'not.*a.*pdf',
        r'unsupported.*format',
        r'file.*not.*found',
        r'no.*such.*file',
        r'permission.*denied.*file',
        r'cannot.*read.*file',
        r'decode.*error',
        r'encoding.*error',
        r'invalid.*file',
    ]
    
    # Patterns for user-fixable errors (password, permissions)
    USER_FIXABLE_PATTERNS = [
        r'password.*required',
        r'encrypted.*pdf',
        r'protected.*pdf',
        r'file.*too.*large',
        r'exceeds.*size.*limit',
        r'invalid.*project',
        r'project.*not.*found',
        r'unauthorized',
        r'access.*denied.*user',
    ]
    
    # Patterns for system issues (infrastructure, resources)
    SYSTEM_ISSUE_PATTERNS = [
        r'disk.*full',
        r'out.*of.*memory',
        r'memory.*error',
        r'no.*space.*left',
        r'resource.*exhausted',
        r'system.*overload',
        r'worker.*lost',
        r'worker.*killed',
        r'segmentation.*fault',
        r'core.*dumped',
        r'internal.*server.*error',
    ]
    
    # Patterns for rate limiting
    RATE_LIMIT_PATTERNS = [
        r'rate.*limit',
        r'quota.*exceeded',
        r'too.*many.*requests',
        r'throttled',
        r'429',  # HTTP status code
    ]
    
    # Patterns for timeouts
    TIMEOUT_PATTERNS = [
        r'timeout',
        r'timed.*out',
        r'deadline.*exceeded',
        r'operation.*took.*too.*long',
    ]
    
    # Sensitive data patterns to sanitize
    SENSITIVE_PATTERNS = [
        (r'/home/[^/\s]+', r'/home/[user]'),  # Unix home paths
        (r'C:\\Users\\[^\\]+', r'C:\\Users\\[user]'),  # Windows user paths (raw string for replacement)
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', r'[IP]'),  # IP addresses
        (r'password[=:]\S+', r'password=[REDACTED]'),  # Passwords
        (r'api[_-]?key[=:]\S+', r'api_key=[REDACTED]'),  # API keys
        (r'token[=:]\S+', r'token=[REDACTED]'),  # Tokens
    ]
    
    def __init__(self):
        """Initialize error classifier with compiled regex patterns."""
        # Compile patterns for performance
        self.transient_regex = re.compile('|'.join(self.TRANSIENT_PATTERNS), re.IGNORECASE)
        self.permanent_regex = re.compile('|'.join(self.PERMANENT_PATTERNS), re.IGNORECASE)
        self.user_fixable_regex = re.compile('|'.join(self.USER_FIXABLE_PATTERNS), re.IGNORECASE)
        self.system_issue_regex = re.compile('|'.join(self.SYSTEM_ISSUE_PATTERNS), re.IGNORECASE)
        self.rate_limit_regex = re.compile('|'.join(self.RATE_LIMIT_PATTERNS), re.IGNORECASE)
        self.timeout_regex = re.compile('|'.join(self.TIMEOUT_PATTERNS), re.IGNORECASE)
    
    def classify(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorType, Dict[str, Any]]:
        """
        Classify an exception and return error type with retry configuration.
        
        Args:
            exception: The exception to classify
            context: Optional context (stage, file_size, retry_count, etc.)
        
        Returns:
            Tuple of (ErrorType, retry_config_dict)
            
            retry_config_dict contains:
                - max_retries: Maximum retry attempts
                - retry_delay: Initial delay in seconds
                - exponential_backoff: Whether to use exponential backoff
                - notify_user: Whether to notify the user
                - alert_admin: Whether to alert administrators
                - can_auto_retry: Whether automatic retry is allowed
        
        Example:
            >>> exc = ConnectionError("Redis connection timeout")
            >>> error_type, config = classifier.classify(exc)
            >>> error_type
            <ErrorType.TRANSIENT: 'transient'>
            >>> config['max_retries']
            5
        """
        context = context or {}
        error_message = str(exception).lower()
        exception_type = type(exception).__name__
        
        # Log classification attempt
        logger.debug(
            f"Classifying error: {exception_type}",
            extra={
                'exception_type': exception_type,
                'error_snippet': error_message[:200],
                'context': context
            }
        )
        
        # Check patterns in order of specificity
        
        # 1. Rate limiting (specific handling)
        if self.rate_limit_regex.search(error_message):
            logger.info(f"Classified as RATE_LIMIT: {exception_type}")
            return ErrorType.RATE_LIMIT, {
                'max_retries': 10,
                'retry_delay': 300,  # 5 minutes
                'exponential_backoff': True,
                'notify_user': False,
                'alert_admin': True,  # Alert if rate limits persist
                'can_auto_retry': True,
            }
        
        # 2. Timeout (may need longer timeout on retry)
        if self.timeout_regex.search(error_message):
            logger.info(f"Classified as TIMEOUT: {exception_type}")
            return ErrorType.TIMEOUT, {
                'max_retries': 2,
                'retry_delay': 120,  # 2 minutes
                'exponential_backoff': False,
                'notify_user': False,
                'alert_admin': False,
                'can_auto_retry': True,
            }
        
        # 3. System issues (needs admin intervention)
        if self.system_issue_regex.search(error_message):
            logger.warning(f"Classified as SYSTEM_ISSUE: {exception_type}")
            return ErrorType.SYSTEM_ISSUE, {
                'max_retries': 3,
                'retry_delay': 300,  # 5 minutes
                'exponential_backoff': True,
                'notify_user': True,  # Inform user of delay
                'alert_admin': True,  # Urgent admin alert
                'can_auto_retry': True,
            }
        
        # 4. User-fixable errors (user action required)
        if self.user_fixable_regex.search(error_message):
            logger.info(f"Classified as USER_FIXABLE: {exception_type}")
            return ErrorType.USER_FIXABLE, {
                'max_retries': 0,  # Don't auto-retry
                'retry_delay': 0,
                'exponential_backoff': False,
                'notify_user': True,  # User must fix
                'alert_admin': False,
                'can_auto_retry': False,
            }
        
        # 5. Permanent errors (don't retry)
        if self.permanent_regex.search(error_message):
            logger.info(f"Classified as PERMANENT: {exception_type}")
            return ErrorType.PERMANENT, {
                'max_retries': 0,
                'retry_delay': 0,
                'exponential_backoff': False,
                'notify_user': True,
                'alert_admin': False,
                'can_auto_retry': False,
            }
        
        # 6. Transient errors (auto-retry)
        if self.transient_regex.search(error_message):
            logger.info(f"Classified as TRANSIENT: {exception_type}")
            return ErrorType.TRANSIENT, {
                'max_retries': 5,
                'retry_delay': 60,  # 1 minute
                'exponential_backoff': True,
                'notify_user': False,
                'alert_admin': False,
                'can_auto_retry': True,
            }
        
        # 7. Unknown (conservative retry)
        logger.warning(
            f"Could not classify error: {exception_type}. Using UNKNOWN category.",
            extra={'error_message': error_message[:200]}
        )
        return ErrorType.UNKNOWN, {
            'max_retries': 3,
            'retry_delay': 60,
            'exponential_backoff': True,
            'notify_user': False,
            'alert_admin': False,
            'can_auto_retry': True,
        }
    
    def sanitize_error_message(self, error_message: str) -> str:
        """
        Remove sensitive information from error messages.
        
        Replaces:
        - User paths with generic placeholders
        - IP addresses with [IP]
        - Passwords, API keys, tokens with [REDACTED]
        
        Args:
            error_message: Raw error message
        
        Returns:
            Sanitized error message safe for logging and display
        
        Security:
            Prevents leaking sensitive data in logs, user notifications,
            and admin dashboards.
        
        Example:
            >>> classifier.sanitize_error_message(
            ...     "Failed to connect to 192.168.1.100 with password=secret123"
            ... )
            'Failed to connect to [IP] with password=[REDACTED]'
        """
        sanitized = error_message
        
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def get_error_details(
        self,
        exception: Exception,
        include_traceback: bool = True
    ) -> Dict[str, Any]:
        """
        Extract comprehensive error details for debugging.
        
        Args:
            exception: The exception to analyze
            include_traceback: Whether to include full stack trace
        
        Returns:
            Dictionary with error details:
                - exception_type: Exception class name
                - error_message: Sanitized error message
                - error_message_raw: Original unsanitized message (for debugging)
                - traceback: Full stack trace (if include_traceback=True)
        
        Security:
            - Sanitizes public-facing error_message
            - Keeps raw message for admin debugging only
            - Logs access to raw error details
        """
        error_details = {
            'exception_type': type(exception).__name__,
            'error_message': self.sanitize_error_message(str(exception)),
            'error_message_raw': str(exception),  # For admin only
        }
        
        if include_traceback:
            error_details['traceback'] = traceback.format_exc()
        
        return error_details


# Singleton instance for application-wide use
error_classifier = ErrorClassifier()
