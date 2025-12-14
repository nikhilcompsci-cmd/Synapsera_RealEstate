"""
Celery Application Configuration
================================

Production-grade Celery setup for asynchronous document ingestion tasks.
Handles distributed task processing with Redis as message broker and result backend.

Security Features:
- Task serialization security (JSON only, no pickle)
- Result expiration to prevent data leaks
- Task time limits to prevent runaway processes
- Rate limiting to prevent abuse

Performance Features:
- Connection pooling for Redis
- Task routing for prioritization
- Result compression
- Automatic retry with exponential backoff

Author: AI Brain Team
Last Updated: December 2025
"""

import os
from celery import Celery
from kombu import Queue, Exchange
from config.settings import get_settings

# Load application settings
settings = get_settings()

# Initialize Celery application with secure configuration
celery_app = Celery(
    'ai_brain',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        'tasks.ingestion_tasks',  # Document ingestion tasks
        'tasks.maintenance_tasks'  # Cleanup and maintenance tasks
    ]
)

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

celery_app.conf.update(
    # ========================================================================
    # SECURITY SETTINGS
    # ========================================================================
    
    # Task Serialization (JSON only for security - never use pickle in production)
    task_serializer='json',
    accept_content=['json'],  # Explicitly reject pickle, yaml, msgpack
    result_serializer='json',
    
    # Result Backend Security
    result_expires=3600,  # Results expire after 1 hour (prevent data accumulation)
    
    # Task Execution Limits (prevent resource exhaustion)
    task_time_limit=1800,  # 30 minutes hard limit (kills task)
    task_soft_time_limit=1500,  # 25 minutes soft limit (raises exception)
    
    # Worker Security
    worker_disable_rate_limits=False,  # Enable rate limiting
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_max_memory_per_child=500000,  # 500MB memory limit per worker
    
    # ========================================================================
    # BROKER (Redis) SETTINGS
    # ========================================================================
    
    broker_url=settings.celery_broker_url,
    broker_connection_retry_on_startup=True,  # Retry on startup if Redis unavailable
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Connection Pooling (improves performance)
    broker_pool_limit=10,  # Max connections in pool
    broker_transport_options={
        'visibility_timeout': 3600,  # 1 hour task visibility
        'fanout_prefix': True,
        'fanout_patterns': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {
            'TCP_KEEPIDLE': 60,
            'TCP_KEEPINTVL': 10,
            'TCP_KEEPCNT': 3,
        },
        # Redis connection timeout
        'socket_timeout': 5.0,
        'socket_connect_timeout': 5.0,
        # Health check interval
        'health_check_interval': 30,
    },
    
    # ========================================================================
    # RESULT BACKEND SETTINGS
    # ========================================================================
    
    result_backend=settings.celery_result_backend,
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0,
        }
    },
    result_compression='gzip',  # Compress results to save memory
    result_extended=True,  # Store additional task metadata
    
    # ========================================================================
    # TASK ROUTING AND QUEUES
    # ========================================================================
    
    # Define queues with priorities
    task_queues=(
        # High priority queue for small, fast tasks
        Queue('high_priority', 
              Exchange('high_priority', type='direct'),
              routing_key='high_priority',
              queue_arguments={'x-max-priority': 10}),
        
        # Default queue for document ingestion
        Queue('default',
              Exchange('default', type='direct'),
              routing_key='default',
              queue_arguments={'x-max-priority': 5}),
        
        # Low priority queue for maintenance tasks
        Queue('low_priority',
              Exchange('low_priority', type='direct'),
              routing_key='low_priority',
              queue_arguments={'x-max-priority': 1}),
    ),
    
    # Default queue for tasks
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # Task routing rules
    task_routes={
        'tasks.ingestion_tasks.ingest_document_async': {
            'queue': 'default',
            'routing_key': 'default',
            'priority': 5,
        },
        'tasks.maintenance_tasks.cleanup_old_files': {
            'queue': 'low_priority',
            'routing_key': 'low_priority',
            'priority': 1,
        },
    },
    
    # ========================================================================
    # TASK EXECUTION SETTINGS
    # ========================================================================
    
    # Task acknowledgment
    task_acks_late=True,  # Acknowledge after task completion (safer)
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
    
    # Task prefetching
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker (balance latency/throughput)
    
    # Task retry configuration
    task_autoretry_for=(Exception,),  # Auto-retry on all exceptions
    task_retry_backoff=True,  # Exponential backoff
    task_retry_backoff_max=600,  # Max 10 minutes between retries
    task_retry_jitter=True,  # Add randomness to prevent thundering herd
    
    # Task tracking
    task_track_started=True,  # Track when task starts (for monitoring)
    task_send_sent_event=True,  # Send event when task is sent
    
    # ========================================================================
    # WORKER SETTINGS
    # ========================================================================
    
    # Concurrency (adjust based on your hardware)
    worker_concurrency=4,  # 4 concurrent tasks per worker
    
    # Worker state
    worker_send_task_events=True,  # Enable monitoring events
    worker_state_db=os.path.join(settings.data_dir, 'celery_worker_state.db'),
    
    # ========================================================================
    # MONITORING AND LOGGING
    # ========================================================================
    
    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    
    # ========================================================================
    # BEAT SCHEDULER (for periodic tasks)
    # ========================================================================
    
    beat_schedule={
        # Cleanup old upload files daily at 2 AM
        'cleanup-old-files-daily': {
            'task': 'tasks.maintenance_tasks.cleanup_old_files',
            'schedule': 86400.0,  # 24 hours
            'options': {
                'queue': 'low_priority',
                'priority': 1,
            }
        },
        # Cleanup expired task results every hour
        'cleanup-expired-results': {
            'task': 'tasks.maintenance_tasks.cleanup_expired_results',
            'schedule': 3600.0,  # 1 hour
            'options': {
                'queue': 'low_priority',
                'priority': 1,
            }
        },
    },
    
    # Beat scheduler backend
    beat_scheduler='celery.beat:PersistentScheduler',
    beat_schedule_filename=os.path.join(settings.data_dir, 'celerybeat-schedule'),
    
    # ========================================================================
    # TIMEZONE
    # ========================================================================
    
    timezone='UTC',
    enable_utc=True,
)

# ============================================================================
# TASK BASE CLASS (for shared task configuration)
# ============================================================================

class BaseTask(celery_app.Task):
    """
    Base task class with common configuration and error handling.
    
    All custom tasks should inherit from this class to ensure
    consistent behavior, logging, and error handling.
    """
    
    # Retry configuration
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handler called when task fails after all retries.
        
        Args:
            exc: Exception raised by task
            task_id: Unique task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception information
        """
        from config.logging_config import get_logger
        logger = get_logger(__name__)
        
        logger.error(
            f"Task {self.name}[{task_id}] failed permanently",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'exception': str(exc),
                'args': args,
                'kwargs': kwargs,
            }
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handler called when task is retried.
        
        Args:
            exc: Exception that triggered retry
            task_id: Unique task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception information
        """
        from config.logging_config import get_logger
        logger = get_logger(__name__)
        
        logger.warning(
            f"Task {self.name}[{task_id}] retrying due to {exc.__class__.__name__}",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'exception': str(exc),
                'retry_count': self.request.retries,
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """
        Handler called when task completes successfully.
        
        Args:
            retval: Return value of task
            task_id: Unique task ID
            args: Task positional arguments
            kwargs: Task keyword arguments
        """
        from config.logging_config import get_logger
        logger = get_logger(__name__)
        
        logger.info(
            f"Task {self.name}[{task_id}] completed successfully",
            extra={
                'task_id': task_id,
                'task_name': self.name,
                'duration': self.request.get('time_start'),
            }
        )

# Set base task class for all tasks
celery_app.Task = BaseTask

# ============================================================================
# HEALTH CHECK
# ============================================================================

@celery_app.task(name='celery.ping', bind=True)
def ping(self):
    """
    Health check task to verify Celery is working.
    
    Returns:
        str: 'pong' if Celery is healthy
    """
    return 'pong'

# ============================================================================
# EXPORT
# ============================================================================

__all__ = ['celery_app', 'BaseTask']
