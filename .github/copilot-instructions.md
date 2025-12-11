# Copilot Global Instructions — Synapsera / AI Brain
**Use this file to guide GitHub Copilot behaviour for the entire repository.**  
Goal: produce industry-grade, secure, tested, production-ready code for FastAPI + Celery + Redis + RAG systems — *while* allowing Copilot to innovate and propose alternatives with clear justification.

---

## 0. How to use these rules
1. Treat **"MANDATORY"** rules as non-negotiable constraints for generated code.  
2. Treat **"PREFERRED"** rules as strong recommendations. Copilot SHOULD follow them but may propose alternatives.  
3. If proposing alternatives to a MANDATORY rule, Copilot must include an **explicit DESIGN NOTE** explaining why the alternative is safer/better and list trade-offs.  
4. If a human asks Copilot to "override rules", Copilot must output a short **RISK & MITIGATION** section and unit-test stubs for the change.

---

## 1. Mandatory (non-negotiable)
- **No secrets** in code. All keys/secrets must come from environment variables or a secret manager.  
- **Never** log PII (user full messages, emails, phone numbers, raw file contents). If logging is necessary, redact/hash.  
- **All long-running operations MUST be background tasks** (Celery, SQS, or approved queue). No blocking work in HTTP handlers.  
- **Redis MUST require AUTH + TLS in production**. Code must assert this when `ENV=production` and fail fast if insecure.  
- **File uploads**: validate magic bytes, MIME, max-size; store with UUID filenames in a temp dir; always delete temporary files after processing.  
- **Idempotency**: ingestion tasks must detect and skip duplicate documents (checksum or dedupe key).  
- **Task retry policy**: every Celery task must include sensible retry/backoff/jitter configuration or reference a shared retry helper.  
- **Sentry (or equivalent)** must be pluggable; only enabled in non-dev by env. Exceptions must be captured with context IDs.  
- **Tests required**: any generated feature must include at least unit tests for core logic and CI steps to run them.

---

## 2. Preferred (strong guidance)
- Use **async endpoints** (FastAPI) and Pydantic models for validation.  
- Use structured JSON logging (structlog or JSONFormatter) and include `correlation_id`/`task_id` in logs.  
- Use a clean module structure: `app/routes`, `app/tasks`, `app/services`, `app/utils`.  
- Batch embedding calls; prefer reuse of an `EmbeddingClient` wrapper with retry and rate-limit awareness.  
- Chunking should be semantic-first with fallback to fixed-size windows and overlap; store provenance metadata for each chunk.  
- Provide docstrings, type hints, simple examples in public functions.

---

## 3. Innovation & "Think Beyond" policy (explicit permission)
Copilot IS ALLOWED and ENCOURAGED to:
- Propose alternative architectures (e.g., SQS vs Redis vs Kafka, or RQ vs Celery) when it improves reliability, cost, or latency.  
- Suggest performance optimizations (quantization, ONNX, batching strategies, flashattention where relevant) with pragmatic trade-offs.  
- Propose richer ingestion alternatives (layout-aware extraction, table parsers, graph-RAG) and explain integration steps.  

When Copilot proposes any alternative it must output:
1. **DESIGN NOTE (short)** — what is the proposed change.  
2. **WHY (bullet points)** — concrete benefits vs current rules.  
3. **TRADE-OFFS (bullet points)** — cost, complexity, lock-in, operational burden.  
4. **SAFETY MITIGATION** — how to implement safely under current mandatory constraints (tests, feature flags, env gating).  
5. **MIGRATION PLAN (if applicable)** — stepwise plan to adopt the alternative with minimal risk.

---

## 4. Override flow (how humans instruct Copilot to deviate)
When a developer wants Copilot to intentionally deviate:
- Prefix the prompt with: `OVERRIDE_RULES: <short reason>`  
- Include required outputs: `RISK_ASSESSMENT`, `TESTS`, `ROLLBACK_PLAN`.  
- Example instruction to Copilot:  

```
OVERRIDE_RULES: Need to log full user message for debugging P0 incident

Request: Add temporary logging of full user input to troubleshoot issue #1234
```

**Copilot's required response format:**
```markdown
## OVERRIDE ACKNOWLEDGED

**RISK ASSESSMENT:**
- Violates: PII logging ban (MANDATORY rule)
- Exposure: User messages may contain sensitive data (emails, names, addresses)
- Blast radius: Logs accessible to all developers with server access
- Duration: Until override is removed

**IMPLEMENTATION:**
- Add feature flag: ENABLE_DEBUG_LOGGING=true (env var)
- Log redaction: Keep only first 50 chars + hash of full message
- Automatic expiry: Add 7-day TTL, require re-approval after
- Access control: Restrict log access to oncall engineer only

**TESTS:**
- Unit test: Verify redaction works correctly
- Integration test: Confirm logs are never written when flag=false
- Security test: Ensure no PII in logs in normal operation

**ROLLBACK PLAN:**
1. Set ENABLE_DEBUG_LOGGING=false
2. Delete all logs containing full messages (retention < 24h)
3. Rotate credentials if any leaked
4. Post-incident review within 48h
```

---

## 5. Code Review Standards

### Before Submitting Code
Every code change must pass these checks:

**Security Checklist:**
- [ ] No hardcoded secrets, API keys, or passwords
- [ ] All user input validated with Pydantic schemas
- [ ] No PII in logs (sanitized/redacted)
- [ ] Environment-based security enforcement (production strict mode)
- [ ] SQL injection protection (use parameterized queries/ORM)
- [ ] File upload validation (magic bytes, size limits)

**Quality Checklist:**
- [ ] Type hints on all function signatures
- [ ] Docstrings on public functions (Google style preferred)
- [ ] Error handling with proper exception types
- [ ] Logging with correlation IDs
- [ ] Unit tests with >80% coverage for new code
- [ ] Integration tests for API endpoints

**Performance Checklist:**
- [ ] Long operations (>2s) moved to background tasks
- [ ] Database queries use indexes (check EXPLAIN)
- [ ] No N+1 query patterns
- [ ] Pagination on list endpoints
- [ ] Caching strategy documented

---

## 6. Testing Standards

### Test Pyramid (ratios)
- **Unit Tests (70%):** Fast, isolated, no external dependencies
- **Integration Tests (20%):** Database, API, Celery tasks
- **E2E Tests (10%):** Full user workflows

### Required Test Coverage

**For every new feature:**
```python
# 1. Unit tests for business logic
def test_error_classification_transient():
    """Test that network timeout is classified as transient error."""
    classifier = ErrorClassifier()
    error_type = classifier.classify("Connection timeout after 30s")
    assert error_type == ErrorType.TRANSIENT

# 2. Integration test for API
@pytest.mark.asyncio
async def test_document_upload_endpoint(client, db_session):
    """Test document upload creates task and returns task_id."""
    response = await client.post("/api/v1/documents", files={"file": pdf_bytes})
    assert response.status_code == 202
    assert "task_id" in response.json()

# 3. Error case testing
@pytest.mark.asyncio
async def test_document_upload_invalid_file_type(client):
    """Test upload rejects non-PDF files."""
    response = await client.post("/api/v1/documents", files={"file": exe_bytes})
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
```

### Test Organization
```
tests/
├── unit/
│   ├── test_error_classifier.py
│   ├── test_chunking_service.py
│   └── test_embedding_client.py
├── integration/
│   ├── test_document_ingestion.py
│   ├── test_rag_pipeline.py
│   └── test_failed_documents_service.py
├── e2e/
│   └── test_document_qa_workflow.py
└── fixtures/
    ├── sample_documents/
    └── conftest.py
```

---

## 7. CI/CD Integration

### Pre-commit Hooks (Required)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: no-secrets
        name: Check for secrets
        entry: detect-secrets scan
        language: system
        
      - id: type-check
        name: MyPy type checking
        entry: mypy
        language: system
        types: [python]
        
      - id: format-check
        name: Black formatting
        entry: black --check
        language: system
        types: [python]
```

### CI Pipeline Stages
1. **Lint & Format:** Black, isort, flake8
2. **Type Check:** MyPy with strict mode
3. **Security Scan:** Bandit, detect-secrets
4. **Unit Tests:** Run with coverage report
5. **Integration Tests:** Docker compose with test DB
6. **Build:** Docker image build
7. **Smoke Tests:** Deploy to staging, run health checks

### Deployment Gates
- ✅ All tests passing (no skipped tests in CI)
- ✅ Code coverage ≥80% for changed files
- ✅ No high/critical security vulnerabilities
- ✅ Performance regression check (<10% slower)
- ✅ Database migrations reviewed and reversible

---

## 8. Performance Benchmarks

### Target Metrics (P95)
- **API Response Time:**
  - Document upload: <500ms (sync validation only)
  - Query endpoint: <2s (with vector search)
  - Document list: <300ms (paginated)

- **Background Task Duration:**
  - PDF text extraction: <30s per 100 pages
  - Embedding generation: <10s per 1000 chunks
  - Full document ingestion: <5min for 500-page document

- **System Throughput:**
  - Concurrent uploads: 100 uploads/min
  - Query handling: 1000 queries/min
  - Celery task processing: 500 tasks/min (3 workers)

### Performance Testing
```python
# Use locust or pytest-benchmark
@pytest.mark.benchmark
def test_embedding_generation_performance(benchmark):
    """Embedding generation should process 1000 chunks in <10s."""
    chunks = [f"Sample text chunk {i}" for i in range(1000)]
    result = benchmark(embedding_client.generate_embeddings, chunks)
    assert result.duration < 10.0
```

---

## 9. Logging & Monitoring

### Structured Logging Format
```python
import structlog

logger = structlog.get_logger()

# Every log must include:
logger.info(
    "document_ingestion_started",
    correlation_id=correlation_id,
    task_id=task_id,
    document_id=document_id,
    project_id=project_id,
    user_id=user_id,
    file_size=file_size,
    timestamp=datetime.utcnow().isoformat()
)
```

### Log Levels (Strict Rules)
- **DEBUG:** Development-only detailed traces (disabled in production)
- **INFO:** Normal operations (task started/completed, API calls)
- **WARNING:** Recoverable issues (retry triggered, fallback used)
- **ERROR:** Failed operations (task failed, API error)
- **CRITICAL:** System-level failures (database down, Redis unavailable)

### Alert Thresholds
- **WARNING:** No alert, logged only
- **ERROR:** Alert if >10/min (aggregate)
- **CRITICAL:** Immediate alert (PagerDuty/Sentry)

---

## 10. Database Best Practices

### Query Optimization
```python
# ❌ BAD: N+1 query
for document in documents:
    chunks = await session.execute(
        select(Chunk).where(Chunk.document_id == document.id)
    )

# ✅ GOOD: Eager loading
documents = await session.execute(
    select(Document).options(selectinload(Document.chunks))
)

# ✅ GOOD: Explicit join with limit
documents = await session.execute(
    select(Document)
    .join(Chunk)
    .where(Document.project_id == project_id)
    .limit(100)
)
```

### Index Strategy
```python
# Every foreign key needs an index
__table_args__ = (
    Index('idx_document_project_id', 'project_id'),
    Index('idx_chunk_document_id', 'document_id'),
    Index('idx_failed_doc_status_retry', 'status', 'next_retry_at'),  # Composite
)
```

### Migration Safety
```python
# ✅ Safe: Add column with default
op.add_column('documents', 
    sa.Column('processing_duration', sa.Integer(), nullable=True)
)

# ❌ Unsafe: Add NOT NULL column without default (locks table)
op.add_column('documents',
    sa.Column('required_field', sa.String(), nullable=False)
)

# ✅ Safe: Add column in two steps
# Migration 1: Add nullable column
op.add_column('documents',
    sa.Column('required_field', sa.String(), nullable=True)
)
# Migration 2: After backfill, make NOT NULL
op.alter_column('documents', 'required_field', nullable=False)
```

---

## 11. Error Handling Patterns

### Exception Hierarchy
```python
# Custom exceptions for domain logic
class AIBrainException(Exception):
    """Base exception for all AI Brain errors."""
    pass

class DocumentProcessingError(AIBrainException):
    """Document cannot be processed."""
    pass

class TransientError(AIBrainException):
    """Temporary error, safe to retry."""
    pass

class PermanentError(AIBrainException):
    """Cannot be fixed by retry."""
    pass
```

### Error Response Format (API)
```python
{
    "error": {
        "code": "DOCUMENT_PROCESSING_FAILED",
        "message": "Unable to extract text from PDF",
        "details": {
            "document_id": "uuid-here",
            "reason": "File appears to be corrupted"
        },
        "retry_after": 60,  # seconds, if retryable
        "correlation_id": "correlation-uuid"
    }
}
```

---

## 12. Security Incident Response

### If PII Leaked in Logs
1. **Immediate:** Rotate affected credentials
2. **Within 1h:** Identify scope (which logs, how many users)
3. **Within 4h:** Delete logs containing PII
4. **Within 24h:** Notify affected users (if required by GDPR)
5. **Within 48h:** Post-mortem with action items

### If Secrets Committed to Git
1. **Immediate:** Revoke compromised secret
2. **Within 30min:** Generate new secret, update deployment
3. **Within 2h:** Use BFG Repo-Cleaner to purge from history
4. **Within 24h:** Review git history for other secrets

---

## 13. Code Examples & Templates

### Adding a New API Endpoint
```python
# api/routes/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import MyFeatureRequest, MyFeatureResponse
from db.session import get_db
from services.my_feature_service import MyFeatureService
import structlog

router = APIRouter(prefix="/api/v1/my-feature", tags=["my-feature"])
logger = structlog.get_logger()

@router.post("", response_model=MyFeatureResponse, status_code=201)
async def create_my_feature(
    request: MyFeatureRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Create new feature.
    
    Args:
        request: Feature creation parameters
        db: Database session
        user_id: Authenticated user ID
        
    Returns:
        Created feature details
        
    Raises:
        HTTPException: 400 if validation fails, 500 if creation fails
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        "create_my_feature_started",
        correlation_id=correlation_id,
        user_id=user_id
    )
    
    try:
        service = MyFeatureService(db)
        result = await service.create(request, user_id)
        
        logger.info(
            "create_my_feature_completed",
            correlation_id=correlation_id,
            feature_id=result.id
        )
        return result
        
    except ValidationError as e:
        logger.warning(
            "create_my_feature_validation_failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "create_my_feature_failed",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True
        )
        # Alert admin for system errors
        if settings.sentry_enabled:
            capture_exception_with_context(e, {"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Adding a New Celery Task
```python
# tasks/my_task.py
from celery_app import celery_app
from config.sentry_config import capture_exception_with_context
import structlog

logger = structlog.get_logger()

@celery_app.task(
    bind=True,
    name="my_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_jitter=True
)
def my_background_task(self, task_data: dict):
    """
    Background task with proper error handling.
    
    Args:
        task_data: Dictionary with task parameters
        
    Returns:
        Dictionary with task results
    """
    task_id = self.request.id
    logger.info("my_task_started", task_id=task_id, data=task_data)
    
    try:
        # Task logic here
        result = process_data(task_data)
        
        logger.info("my_task_completed", task_id=task_id, result=result)
        return result
        
    except TransientError as e:
        logger.warning(
            "my_task_transient_error",
            task_id=task_id,
            error=str(e),
            retry_count=self.request.retries
        )
        # Auto-retry handled by decorator
        raise
        
    except PermanentError as e:
        logger.error("my_task_permanent_error", task_id=task_id, error=str(e))
        # Don't retry permanent errors
        return {"status": "failed", "error": str(e)}
        
    except Exception as e:
        logger.error("my_task_unexpected_error", task_id=task_id, error=str(e), exc_info=True)
        capture_exception_with_context(e, {"task_id": task_id, "data": task_data})
        raise
```

---

## 14. Documentation Requirements

### Every Feature Must Include
1. **README section:** Purpose, usage, examples
2. **API documentation:** OpenAPI/Swagger auto-generated
3. **Architecture Decision Record (ADR):** For significant design choices
4. **Runbook:** Deployment steps, rollback procedure
5. **Troubleshooting guide:** Common issues and solutions

### ADR Template
```markdown
# ADR-001: Use FAISS for Vector Search

## Status
Accepted

## Context
Need fast similarity search over 1M+ document chunks with sub-second latency.

## Decision
Use FAISS (Facebook AI Similarity Search) with IVF index.

## Consequences
**Positive:**
- 10x faster than PostgreSQL pgvector
- Handles millions of vectors efficiently
- Battle-tested at scale

**Negative:**
- In-memory (requires RAM planning)
- Rebuild index on updates
- No built-in persistence (need backup strategy)

## Alternatives Considered
- pgvector: Too slow at scale
- Pinecone: Vendor lock-in, cost concerns
- Elasticsearch: Overkill, higher resource usage
```

---

## 15. Summary & Quick Reference

### Golden Rules
1. ✅ **Security first:** No secrets, sanitize PII, fail secure in production
2. ✅ **Async everything:** HTTP handlers fast, background tasks for heavy work
3. ✅ **Test always:** Unit tests required, integration tests for critical paths
4. ✅ **Monitor proactively:** Structured logging, Sentry alerts, metrics
5. ✅ **Document thoroughly:** Code comments, docstrings, ADRs, runbooks

### Before Every Commit
```bash
black .                          # Format code
mypy .                           # Type check
pytest tests/                    # Run tests
detect-secrets scan              # Check for secrets
```

### Getting Help
- 📚 **Documentation:** See `ai_brain/docs/` or `PROJECT_SUMMARY.md`
- 🔍 **Examples:** Search codebase for similar patterns
- 💬 **Team:** Ask in #ai-brain Slack channel
- 🤖 **Copilot:** Use `OVERRIDE_RULES` prefix for special cases

---

**Last Updated:** December 11, 2025  
**Version:** 1.0  
**Maintained By:** AI Brain Team
