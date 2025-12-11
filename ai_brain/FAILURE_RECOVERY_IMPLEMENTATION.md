# Failed Document Recovery System - Implementation Guide

## ✅ Completed Components

### 1. Database Models (COMPLETE)
**File:** `db/models_failed_documents.py`

**FailedDocument Model:**
- Comprehensive error tracking with classification
- Automatic retry scheduling with exponential backoff
- Status management (retrying, permanently_failed, resolved, ignored)
- Helper methods: `can_retry()`, `should_retry_now()`, `mark_permanently_failed()`, `mark_resolved()`
- Audit trail with timestamps
- Multiple indexes for performance

**ProcessingCheckpoint Model:**
- Stores intermediate results for resume capability
- Auto-expires after 7 days
- JSON checkpoint data storage

**Enums:**
- `ErrorType`: transient, permanent, user_fixable, system_issue, rate_limit, timeout, unknown
- `FailureStatus`: retrying, permanently_failed, resolved, ignored

**Relationships:**
- Added `failed_documents` relationship to `Project` model in `db/models.py`

---

### 2. Database Migration (COMPLETE)
**File:** `alembic/versions/003_create_failed_documents_and_checkpoints_tables.py`

**Creates:**
- `failed_documents` table with 10+ indexes for query performance
- `processing_checkpoints` table with unique document identifier
- `error_type_enum` and `failure_status_enum` PostgreSQL enums
- Foreign key constraints with CASCADE delete
- Composite indexes for common queries

**To Apply:**
```bash
alembic upgrade head
```

---

### 3. Error Classification Service (COMPLETE)
**File:** `services/error_classifier.py`

**ErrorClassifier Class:**
- Pattern-based error classification using regex
- 60+ error patterns categorized by type
- Smart retry configuration per error type
- Sensitive data sanitization (paths, IPs, passwords, API keys)
- Detailed error information extraction

**Retry Configurations by Error Type:**
| Error Type     | Max Retries | Initial Delay | Exponential Backoff | Notify User | Alert Admin |
|---------------|-------------|---------------|---------------------|-------------|-------------|
| Rate Limit    | 10          | 300s (5min)   | Yes                 | No          | Yes         |
| Timeout       | 2           | 120s (2min)   | No                  | No          | No          |
| System Issue  | 3           | 300s (5min)   | Yes                 | Yes         | Yes         |
| User Fixable  | 0           | 0s            | No                  | Yes         | No          |
| Permanent     | 0           | 0s            | No                  | Yes         | No          |
| Transient     | 5           | 60s (1min)    | Yes                 | No          | No          |
| Unknown       | 3           | 60s (1min)    | Yes                 | No          | No          |

**Usage:**
```python
from services.error_classifier import error_classifier

error_type, retry_config = error_classifier.classify(exception)
sanitized_msg = error_classifier.sanitize_error_message(str(exception))
```

---

### 4. Failed Documents Service (COMPLETE)
**File:** `services/failed_documents_service.py`

**FailedDocumentsService Class:**

**Methods:**
1. `record_failure()` - Record failed upload with automatic error classification
2. `get_failed_documents()` - Query with filters (project_id, status, error_type) and pagination
3. `get_documents_pending_retry()` - Get documents eligible for retry now
4. `schedule_retry()` - Schedule manual retry with custom delay
5. `mark_resolved()` - Mark document as successfully recovered
6. `mark_permanently_failed()` - Mark as permanently failed (no more retries)
7. `cleanup_orphaned_files()` - Delete files from failed/resolved uploads
8. `get_failure_metrics()` - Get metrics for monitoring dashboard

**Security Features:**
- Input validation on all parameters
- File path sanitization
- Audit logging for all operations
- Access control via user_id tracking

**Usage:**
```python
from services.failed_documents_service import failed_documents_service

# Record failure
failed_doc = await failed_documents_service.record_failure(
    db=session,
    project_id=1,
    filename="doc.pdf",
    file_path="/uploads/doc.pdf",
    exception=ConnectionError("Redis timeout"),
    failed_stage="extraction",
    task_id="abc-123",
    user_id=5
)

# Get failed documents
failed_docs, total = await failed_documents_service.get_failed_documents(
    db=session,
    project_id=1,
    status=FailureStatus.RETRYING,
    limit=50,
    offset=0
)

# Get metrics
metrics = await failed_documents_service.get_failure_metrics(
    db=session,
    project_id=1,
    days=7
)
```

---

## 🚧 Remaining Implementation

### 5. Enhanced Ingestion Task (IN PROGRESS)
**File:** `tasks/ingestion_tasks.py`

**Required Changes:**
1. Wrap main processing in try-except
2. On exception:
   - Classify error using `error_classifier.classify()`
   - Record to `failed_documents` using `failed_documents_service.record_failure()`
   - Check if should retry based on classification
   - Re-raise for Celery retry if transient error
3. On success:
   - Mark any existing failed_document as resolved
   - Clean up checkpoints

**Pseudo-code:**
```python
async def ingest_document_async(...):
    try:
        # Existing ingestion logic
        result = await ingestion_service.ingest_document(...)
        
        # Mark as resolved if previously failed
        await mark_any_failed_document_resolved(...)
        
        return result
    
    except Exception as e:
        # Classify error
        error_type, retry_config = error_classifier.classify(e)
        
        # Record failure
        async with AsyncSessionLocal() as db:
            failed_doc = await failed_documents_service.record_failure(
                db=db,
                project_id=project_id,
                filename=filename,
                file_path=file_path,
                exception=e,
                failed_stage=current_stage,
                task_id=self.request.id
            )
        
        # Retry if allowed
        if retry_config['can_auto_retry']:
            raise self.retry(exc=e, countdown=retry_config['retry_delay'])
        else:
            raise
```

---

### 6. Failed Documents API Endpoints (TODO)
**File:** `api/failed_documents_router.py` (NEW)

**Required Endpoints:**

```python
# GET /api/v1/documents/failed
# Query failed documents with filters
async def get_failed_documents(
    project_id: Optional[int] = None,
    status: Optional[FailureStatus] = None,
    error_type: Optional[ErrorType] = None,
    limit: int = 100,
    offset: int = 0
)

# GET /api/v1/documents/failed/{failed_document_id}
# Get single failed document details
async def get_failed_document(failed_document_id: int)

# POST /api/v1/documents/failed/{failed_document_id}/retry
# Manually trigger retry
async def retry_failed_document(
    failed_document_id: int,
    retry_delay_seconds: Optional[int] = None
)

# PATCH /api/v1/documents/failed/{failed_document_id}
# Update status (resolve, ignore, mark_permanently_failed)
async def update_failed_document(
    failed_document_id: int,
    status: FailureStatus,
    resolution_notes: Optional[str] = None
)

# DELETE /api/v1/documents/failed/{failed_document_id}
# Delete failed document record and file
async def delete_failed_document(failed_document_id: int)

# GET /api/v1/documents/failed/metrics
# Get failure metrics for dashboard
async def get_failure_metrics(
    project_id: Optional[int] = None,
    days: int = 7
)
```

---

### 7. API Schemas (TODO)
**File:** `api/schemas.py`

**Required Schemas:**

```python
class FailedDocumentResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_size: Optional[int]
    error_type: str
    error_message: str  # Sanitized
    status: str
    retry_count: int
    max_retries: int
    failed_stage: Optional[str]
    created_at: datetime
    last_retry_at: Optional[datetime]
    next_retry_at: Optional[datetime]

class FailedDocumentListResponse(BaseModel):
    items: List[FailedDocumentResponse]
    total_count: int
    limit: int
    offset: int

class RetryFailedDocumentRequest(BaseModel):
    retry_delay_seconds: Optional[int] = None

class UpdateFailedDocumentRequest(BaseModel):
    status: FailureStatus
    resolution_notes: Optional[str] = None

class FailureMetricsResponse(BaseModel):
    total_failures: int
    by_error_type: Dict[str, int]
    by_status: Dict[str, int]
    avg_retry_count: float
    success_rate: float
    time_window_days: int
```

---

### 8. Automated Retry Processor Task (TODO)
**File:** `tasks/retry_processor_tasks.py` (NEW)

**Purpose:**
Scheduled Celery Beat task that processes the retry queue automatically.

```python
@celery_app.task(name='tasks.retry.process_retry_queue')
def process_retry_queue():
    """
    Process documents pending retry.
    
    Scheduled to run every 5 minutes via Celery Beat.
    Fetches documents eligible for retry and re-submits to ingestion queue.
    """
    async with AsyncSessionLocal() as db:
        # Get documents pending retry
        pending = await failed_documents_service.get_documents_pending_retry(
            db=db,
            limit=50
        )
        
        for failed_doc in pending:
            # Submit to ingestion queue
            ingest_document_async.apply_async(
                args=[
                    failed_doc.project_id,
                    failed_doc.file_path,
                    failed_doc.filename
                ],
                kwargs={'user_id': failed_doc.user_id},
                queue='default'
            )
```

**Celery Beat Schedule:**
```python
# In celery_app.py beat_schedule
'process-retry-queue': {
    'task': 'tasks.retry.process_retry_queue',
    'schedule': 300.0,  # Every 5 minutes
}
```

---

### 9. Cleanup Tasks (TODO)
**File:** `tasks/maintenance_tasks.py`

**Add Methods:**

```python
@celery_app.task(name='tasks.maintenance.cleanup_orphaned_failed_files')
async def cleanup_orphaned_failed_files():
    """
    Delete files from permanently failed or resolved uploads older than 7 days.
    
    Scheduled to run daily via Celery Beat.
    """
    async with AsyncSessionLocal() as db:
        result = await failed_documents_service.cleanup_orphaned_files(
            db=db,
            older_than_days=7
        )
    
    logger.info(
        f"Cleaned up {result['files_deleted']} orphaned files, "
        f"freed {result['space_freed']} bytes"
    )

@celery_app.task(name='tasks.maintenance.cleanup_expired_checkpoints')
async def cleanup_expired_checkpoints():
    """
    Delete expired processing checkpoints.
    
    Scheduled to run daily via Celery Beat.
    """
    # Implementation here
```

**Celery Beat Schedule:**
```python
'cleanup-orphaned-files': {
    'task': 'tasks.maintenance.cleanup_orphaned_failed_files',
    'schedule': 86400.0,  # Daily
}
```

---

### 10. Health Check Endpoint (TODO)
**File:** `api/health_router.py` (NEW)

```python
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    System health check with failure metrics.
    
    Returns:
        - Celery worker status
        - Redis connection status
        - Database connection status
        - Recent failure rate
        - Average processing time
    """
    # Check Celery workers
    inspect = celery_app.control.inspect()
    active_workers = len(inspect.active() or {})
    
    # Check Redis
    redis_connected = check_redis_connection()
    
    # Get failure metrics
    metrics = await failed_documents_service.get_failure_metrics(
        db=db,
        days=1  # Last 24 hours
    )
    
    return {
        "status": "healthy" if redis_connected and active_workers > 0 else "degraded",
        "celery_workers": active_workers,
        "redis_connected": redis_connected,
        "failed_tasks_24h": metrics['total_failures'],
        "success_rate": metrics['success_rate'],
        "timestamp": datetime.utcnow()
    }
```

---

## 📊 Testing Plan

### Unit Tests
```python
# tests/test_error_classifier.py
def test_classify_transient_error():
    exc = ConnectionError("Redis connection timeout")
    error_type, config = error_classifier.classify(exc)
    assert error_type == ErrorType.TRANSIENT
    assert config['max_retries'] == 5

# tests/test_failed_documents_service.py
async def test_record_failure():
    failed_doc = await failed_documents_service.record_failure(...)
    assert failed_doc.error_type == ErrorType.TRANSIENT
    assert failed_doc.status == FailureStatus.RETRYING
```

### Integration Tests
```python
# tests/test_failure_recovery.py
async def test_failed_document_recovery_flow():
    # 1. Upload document that will fail
    # 2. Verify failed_document created
    # 3. Trigger manual retry
    # 4. Verify document resolved
```

---

## 🚀 Deployment Steps

### 1. Run Database Migration
```bash
cd ai_brain
alembic upgrade head
```

### 2. Restart Celery Workers
```bash
# Stop existing workers
celery -A celery_app control shutdown

# Start workers with new code
celery -A celery_app worker --loglevel=info --pool=solo
```

### 3. Start Celery Beat (for scheduled tasks)
```bash
celery -A celery_app beat --loglevel=info
```

### 4. Restart API Server
```bash
python run_server.py
```

---

## 📈 Monitoring

### Key Metrics to Track
1. **Failure Rate**: `failed_documents` count / total uploads
2. **Retry Success Rate**: resolved / total_failures
3. **Average Retry Count**: avg(retry_count)
4. **Error Type Distribution**: Count by error_type
5. **Processing Time**: avg(processing_duration)

### Dashboard Queries
```sql
-- Failure rate last 24 hours
SELECT 
    COUNT(*) as total_failures,
    COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
    COUNT(*) FILTER (WHERE status = 'permanently_failed') as permanent_failures
FROM failed_documents
WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Top error types
SELECT error_type, COUNT(*) as count
FROM failed_documents
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY error_type
ORDER BY count DESC;
```

---

## 🔐 Security Considerations

### Implemented
✅ Input validation on all service methods
✅ Sanitized error messages (no sensitive data)
✅ File path validation (prevent directory traversal)
✅ Audit logging for all operations
✅ Foreign key constraints with CASCADE
✅ Enum constraints on error_type and status

### Best Practices
- Never log raw error messages to user-facing logs
- Always use `error_classifier.sanitize_error_message()`
- Validate project_id ownership before operations
- Rate limit retry attempts per user/project
- Alert admins on system_issue and rate_limit errors

---

## 📝 Next Steps

1. **Enhance ingestion task** with failure recording
2. **Create API endpoints** for failed documents management
3. **Add API schemas** for request/response validation
4. **Implement retry processor** scheduled task
5. **Add cleanup tasks** for orphaned files and checkpoints
6. **Create health check** endpoint with metrics
7. **Write tests** for all components
8. **Update frontend** to display failed documents
9. **Setup monitoring** dashboard with metrics
10. **Configure alerts** for high failure rates

---

## 📚 Related Files

- `db/models_failed_documents.py` - Database models ✅
- `alembic/versions/003_*.py` - Migration ✅
- `services/error_classifier.py` - Error classification ✅
- `services/failed_documents_service.py` - Business logic ✅
- `tasks/ingestion_tasks.py` - Ingestion with failure handling 🚧
- `api/failed_documents_router.py` - API endpoints ⏳
- `api/schemas.py` - Request/response schemas ⏳
- `tasks/retry_processor_tasks.py` - Automated retry ⏳
- `tasks/maintenance_tasks.py` - Cleanup tasks ⏳
- `api/health_router.py` - Health check ⏳

**Legend:** ✅ Complete | 🚧 In Progress | ⏳ Not Started
