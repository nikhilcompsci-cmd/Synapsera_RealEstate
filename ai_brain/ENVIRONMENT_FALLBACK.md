# Environment-Based Celery/Redis Fallback

## Overview

The system implements **strict environment-based fallback logic** to ensure production reliability while maintaining development flexibility.

## Behavior by Environment

### 🔴 Production Environment (`environment=production`)

**STRICT MODE - NO FALLBACK**

#### Startup Behavior
```
❌ Application FAILS to start if Redis/Celery unavailable
💥 Raises RuntimeError: "Redis/Celery is required in production environment"
📝 Logs error: "PRODUCTION ERROR: Redis/Celery required but not available"
```

#### Runtime Behavior (if Redis goes down)
```
❌ Document upload returns HTTP 503 Service Unavailable
📝 Error: "Service unavailable: Task queue is not accessible"
🚫 NO fallback to synchronous processing
📧 Client instructed to contact support
```

#### Rationale
- Production systems MUST be reliable and predictable
- Synchronous processing would create inconsistent behavior
- Prevents silent performance degradation
- Forces proper infrastructure setup

---

### 🟢 Development Environment (`environment=development`)

**GRACEFUL FALLBACK MODE**

#### Startup Behavior
```
✅ Application starts normally even if Redis unavailable
⚠️  Warning displayed in console and logs
📝 Logs: "Redis not available: [connection error]"
🔄 Fallback mode enabled
```

#### Runtime Behavior (if Redis unavailable)
```
✅ Document upload succeeds using sync processing
⚠️  Warning logged: "DEV MODE: Using synchronous processing"
📝 Console message explains fallback
🐌 Slower processing (blocks during upload)
✅ Document still gets ingested successfully
```

#### Rationale
- Developers can work without Redis/Celery setup
- Testing functionality without infrastructure
- Clear warnings indicate suboptimal mode
- Encourages but doesn't require async setup

---

## Configuration

### Environment Variable
```bash
# .env file
ENVIRONMENT=development  # or "production" or "staging"
```

### Settings Class
```python
from config.settings import Settings

settings = Settings()

# Check environment
settings.is_production  # True if environment="production"
settings.is_development  # True if environment="development"
```

---

## Code Implementation

### 1. Startup Check (`main.py`)

```python
# Check Redis/Celery availability (STRICT in production)
try:
    import redis
    r = redis.from_url(settings.celery_broker_url)
    r.ping()
    logger.info("✅ Redis connection successful")
except Exception as e:
    if settings.is_production:
        # FAIL TO START - Redis required
        raise RuntimeError("Redis/Celery required in production")
    else:
        # WARN BUT CONTINUE - Fallback available
        logger.warning(f"⚠️ Redis not available: {e}")
```

### 2. Document Upload (`api/document_router.py`)

```python
try:
    # Try async processing
    task = ingest_document_async.delay(...)
    return {"status": "queued", "task_id": task.id}
    
except Exception as celery_error:
    if settings.is_production:
        # PRODUCTION: Fail fast
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: Task queue not accessible"
        )
    else:
        # DEVELOPMENT: Fallback to sync
        logger.warning("[DEV FALLBACK] Using sync processing")
        result = await ingestion_service.ingest_document(...)
        return {"status": "completed", "document_id": result.id}
```

---

## Testing

Run the environment test suite:
```bash
python test_environment_fallback.py
```

Expected output:
```
✅ PASS: Development Fallback
✅ PASS: Production No Fallback
✅ PASS: Current Environment
✅ PASS: Startup Behavior
```

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production` in environment variables
- [ ] Ensure Redis server is running and accessible
- [ ] Start Celery workers: `celery -A celery_app worker`
- [ ] Verify Redis connection: `redis-cli ping` returns `PONG`
- [ ] Test application startup (should succeed)
- [ ] Test document upload (should use async processing)
- [ ] Monitor Celery worker logs for task processing

⚠️ **WARNING**: Application will NOT start in production if Redis is unavailable!

---

## Development Setup

For local development:

1. **Option A: Full Setup (Recommended)**
   ```bash
   # Install Redis
   choco install redis-64 -y
   
   # Start Redis
   redis-server
   
   # Start Celery worker
   python start_celery_worker.py
   
   # Start API
   python run_server.py
   ```

2. **Option B: Without Redis (Fallback Mode)**
   ```bash
   # Just start API (sync fallback will be used)
   python run_server.py
   ```
   
   You'll see:
   ```
   ⚠️  DEV MODE WARNING: Redis/Celery not running
   Document ingestion will FALLBACK to SYNCHRONOUS processing
   This fallback is ONLY available in development mode.
   ```

---

## Monitoring

### Check Current Mode

```python
from config.settings import get_settings

settings = get_settings()
print(f"Environment: {settings.environment}")
print(f"Production: {settings.is_production}")
```

### Logs to Monitor

**Development with Redis unavailable:**
```
WARNING: Redis not available: Connection refused
WARNING: [DEV FALLBACK] Using synchronous processing
```

**Production with Redis unavailable:**
```
ERROR: PRODUCTION ERROR: Redis/Celery required but not available
FATAL: Application cannot start
```

---

## Summary

| Feature | Development | Production |
|---------|-------------|------------|
| **Startup without Redis** | ✅ Allowed (with warning) | ❌ Fails to start |
| **Fallback to sync** | ✅ Enabled | ❌ Disabled |
| **Error on upload** | ⚠️ Warning (continues) | ❌ HTTP 503 error |
| **Performance** | 🐌 Slower if fallback used | 🚀 Always async |
| **Reliability** | ⚠️ Flexible | ✅ Strict |

**Key Principle**: Production must be reliable and predictable. Development can be flexible and forgiving.
