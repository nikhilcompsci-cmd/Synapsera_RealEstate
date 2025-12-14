# Celery Setup Guide for AI Brain

## 📋 Overview

This guide covers the setup and usage of Celery for asynchronous document ingestion in the AI Brain application.

**What is Celery?**
- Distributed task queue for Python
- Handles long-running tasks asynchronously
- Improves API response times (returns instantly instead of waiting 2+ minutes)
- Enables horizontal scaling (add more workers to process more documents simultaneously)

**Architecture:**
```
FastAPI (Web Server)
    ↓
Redis (Message Broker)
    ↓
Celery Workers (Process Tasks)
    ↓
PostgreSQL (Results Storage)
```

---

## 🚀 Installation

### 1. Install Redis (Message Broker)

**Windows (using Chocolatey):**
```powershell
choco install redis-64 -y
```

**Windows (using WSL):**
```bash
sudo apt-get install redis-server
```

**Start Redis:**
```powershell
redis-server
```

**Verify Redis is running:**
```powershell
redis-cli ping
# Should return: PONG
```

### 2. Install Python Dependencies

```powershell
cd ai_brain
pip install -r requirements.txt
```

This installs:
- `celery[redis]==5.3.4` - Celery with Redis support
- `redis==5.0.1` - Redis Python client
- `flower==2.0.1` - Web-based monitoring UI (optional)

### 3. Update Environment Variables

Add to your `.env` file:
```dotenv
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
DATA_DIR=data
```

---

## 🎯 Running the System

You need **3 processes** running simultaneously:

### Terminal 1: Redis Server
```powershell
redis-server
```

### Terminal 2: Celery Worker
```powershell
cd ai_brain
celery -A celery_app worker --loglevel=info --pool=solo
```

**Options:**
- `--loglevel=info`: Log level (debug, info, warning, error)
- `--pool=solo`: Use solo pool on Windows (required)
- `--concurrency=4`: Number of concurrent tasks (default: CPU count)
- `--queues=default,high_priority`: Specific queues to process

### Terminal 3: FastAPI Server
```powershell
cd ai_brain
python run_server.py
```

### Terminal 4 (Optional): Flower Monitoring UI
```powershell
cd ai_brain
celery -A celery_app flower
```

Then open: http://localhost:5555

---

## 📊 Monitoring Tasks

### 1. Using Flower (Web UI)

Best option for production monitoring:
- Real-time task status
- Worker health
- Task history
- Performance graphs

Access at: http://localhost:5555

### 2. Using Celery CLI

**List active tasks:**
```powershell
celery -A celery_app inspect active
```

**List scheduled tasks:**
```powershell
celery -A celery_app inspect scheduled
```

**Worker stats:**
```powershell
celery -A celery_app inspect stats
```

**Ping workers:**
```powershell
celery -A celery_app inspect ping
```

### 3. Using API Endpoints

**Check task status:**
```bash
GET http://localhost:8000/api/v1/task/{task_id}/status
```

Response:
```json
{
  "task_id": "3c5e42a8-7f9a-4c5d-9e3f-8b1a2c3d4e5f",
  "state": "PROGRESS",
  "ready": false,
  "successful": null,
  "progress": {
    "current": 60,
    "total": 100,
    "status": "Generating embeddings...",
    "stage": "embedding"
  }
}
```

**States:**
- `PENDING`: Task waiting in queue
- `PROGRESS`: Task currently processing
- `SUCCESS`: Task completed successfully
- `FAILURE`: Task failed
- `RETRY`: Task being retried

---

## 🔧 Usage Examples

### 1. Upload Document (Async)

**Request:**
```bash
POST http://localhost:8000/api/v1/project/1/document/upload
Content-Type: multipart/form-data

file: document.pdf
```

**Response (Immediate - <100ms):**
```json
{
  "status": "queued",
  "message": "Document upload successful. Ingestion started.",
  "document_id": null,
  "chunks_created": 0,
  "embeddings_created": 0,
  "task_id": "3c5e42a8-7f9a-4c5d-9e3f-8b1a2c3d4e5f"
}
```

### 2. Poll Task Status

```javascript
// Frontend polling example
const taskId = "3c5e42a8-7f9a-4c5d-9e3f-8b1a2c3d4e5f";

async function pollTaskStatus() {
  const response = await fetch(`/api/v1/task/${taskId}/status`);
  const data = await response.json();
  
  if (data.state === 'PROGRESS') {
    console.log(`Progress: ${data.progress.current}%`);
    console.log(`Stage: ${data.progress.status}`);
    setTimeout(pollTaskStatus, 1000); // Poll every second
  } else if (data.state === 'SUCCESS') {
    console.log('Ingestion completed!');
    console.log(data.result);
  } else if (data.state === 'FAILURE') {
    console.error('Ingestion failed:', data.error);
  }
}

pollTaskStatus();
```

### 3. Manual Task Submission (Python)

```python
from tasks.ingestion_tasks import ingest_document_async

# Submit task
task = ingest_document_async.delay(
    project_id=1,
    file_path='/path/to/document.pdf',
    filename='document.pdf'
)

print(f"Task ID: {task.id}")
print(f"State: {task.state}")

# Wait for result (blocking)
result = task.get(timeout=1800)  # 30 min timeout
print(result)
```

---

## 🔒 Security Features

### 1. Task Serialization
- **JSON only** (no pickle) - prevents code injection
- All data validated before serialization

### 2. Resource Limits
- **Time limits**: 30 min hard limit, 25 min soft limit
- **Memory limits**: 500MB per worker process
- **Worker recycling**: Workers restart after 1000 tasks (prevents memory leaks)

### 3. Input Validation
- File path sanitization (prevents directory traversal)
- File size limits (prevents DoS)
- File type validation

### 4. Error Handling
- Automatic retry with exponential backoff
- Sensitive data not logged
- Failed tasks tracked for debugging

---

## 🎛️ Configuration

### Task Priority Queues

**High Priority:**
```python
task = my_task.apply_async(queue='high_priority', priority=10)
```

**Default Priority:**
```python
task = my_task.apply_async(queue='default', priority=5)
```

**Low Priority:**
```python
task = my_task.apply_async(queue='low_priority', priority=1)
```

### Periodic Tasks (Celery Beat)

Defined in `celery_app.py`:

```python
beat_schedule={
    'cleanup-old-files-daily': {
        'task': 'tasks.maintenance.cleanup_old_files',
        'schedule': 86400.0,  # 24 hours
    },
}
```

**Start Beat Scheduler:**
```powershell
celery -A celery_app beat --loglevel=info
```

---

## 📈 Performance Tuning

### 1. Worker Concurrency

**CPU-bound tasks (OCR, embedding generation):**
```powershell
celery -A celery_app worker --concurrency=4
```

**I/O-bound tasks (database, API calls):**
```powershell
celery -A celery_app worker --concurrency=10
```

### 2. Prefetch Multiplier

Controls how many tasks a worker fetches ahead:
```python
# In celery_app.py
worker_prefetch_multiplier=4  # Fetch 4 tasks per worker
```

### 3. Result Expiration

Results auto-expire to save Redis memory:
```python
result_expires=3600  # 1 hour
```

---

## 🐛 Troubleshooting

### Issue: Tasks stuck in PENDING
**Solution:** Check if Celery workers are running
```powershell
celery -A celery_app inspect active
```

### Issue: Connection refused to Redis
**Solution:** Start Redis server
```powershell
redis-server
```

### Issue: Import errors in tasks
**Solution:** Ensure `celery_app.py` includes tasks
```python
celery_app = Celery(
    'ai_brain',
    include=['tasks.ingestion_tasks', 'tasks.maintenance_tasks']
)
```

### Issue: Tasks timing out
**Solution:** Increase time limit
```python
@celery_app.task(time_limit=3600)  # 60 minutes
```

---

## 📚 Additional Resources

- **Celery Documentation**: https://docs.celeryq.dev/
- **Redis Documentation**: https://redis.io/documentation
- **Flower Documentation**: https://flower.readthedocs.io/

---

## 🚀 Production Deployment

### Systemd Service (Linux)

**celery-worker.service:**
```ini
[Unit]
Description=Celery Worker
After=network.target redis.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/ai_brain
Environment="PATH=/var/www/ai_brain/venv/bin"
ExecStart=/var/www/ai_brain/venv/bin/celery -A celery_app worker \
    --loglevel=info \
    --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  celery-worker:
    build: .
    command: celery -A celery_app worker --loglevel=info
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
  
  flower:
    build: .
    command: celery -A celery_app flower
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery-worker
```

---

**Need help?** Check logs at `logs/app.log` or Flower monitoring at http://localhost:5555
