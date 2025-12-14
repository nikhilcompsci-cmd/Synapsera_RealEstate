# Retry Architecture Diagram - Failed Document Recovery System

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DOCUMENT UPLOAD FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐
│  User    │
│ Uploads  │
│Document  │
└────┬─────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Upload Endpoint                              │
│  POST /api/v1/documents/upload                                              │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ 1. Validate file (size, type, hash)                         │           │
│  │ 2. Save to uploads/ directory                               │           │
│  │ 3. Try Celery async OR fallback to sync                     │           │
│  └─────────────────────────────────────────────────────────────┘           │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
        ┌───────▼────────┐             ┌────────▼────────┐
        │ Redis Available│             │ Redis Down      │
        │ ASYNC MODE     │             │ SYNC MODE       │
        └───────┬────────┘             └────────┬────────┘
                │                               │
                │                               │
┌───────────────▼───────────────────────────────▼─────────────────────────────┐
│                      CELERY TASK: ingest_document_async                      │
│  tasks/ingestion_tasks.py                                                    │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ STAGE 1: Validation (0-20%)                                 │           │
│  │ STAGE 2: Extraction (20-40%)                                │           │
│  │ STAGE 3: Chunking (40-60%)                                  │           │
│  │ STAGE 4: Embedding (60-80%)                                 │           │
│  │ STAGE 5: Indexing (80-100%)                                 │           │
│  └─────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                ┌─────────────────┴─────────────────┐
                │                                   │
         ┌──────▼──────┐                     ┌─────▼─────┐
         │   SUCCESS   │                     │  FAILURE  │
         └──────┬──────┘                     └─────┬─────┘
                │                                   │
                │                                   ▼
                │                    ┌──────────────────────────────┐
                │                    │  ERROR CLASSIFICATION        │
                │                    │  services/error_classifier.py│
                │                    └──────────┬───────────────────┘
                │                               │
                │                               ▼
                │              ┌────────────────────────────────────────────┐
                │              │    Classify Error Type                     │
                │              │    ┌─────────────────────────────────┐    │
                │              │    │ • Transient    (network, Redis) │    │
                │              │    │ • Permanent    (corrupted file) │    │
                │              │    │ • User-Fixable (password, size) │    │
                │              │    │ • System-Issue (disk full, OOM) │    │
                │              │    │ • Rate-Limit   (API throttle)   │    │
                │              │    │ • Timeout      (process timeout)│    │
                │              │    │ • Unknown      (unclassified)   │    │
                │              │    └─────────────────────────────────┘    │
                │              └──────────┬─────────────────────────────────┘
                │                         │
                │                         ▼
                │              ┌────────────────────────────────────────────┐
                │              │    Get Retry Configuration                 │
                │              │    ┌─────────────────────────────────┐    │
                │              │    │ • max_retries: 0-10             │    │
                │              │    │ • retry_delay: 0-300s           │    │
                │              │    │ • exponential_backoff: bool     │    │
                │              │    │ • notify_user: bool             │    │
                │              │    │ • alert_admin: bool             │    │
                │              │    │ • can_auto_retry: bool          │    │
                │              │    └─────────────────────────────────┘    │
                │              └──────────┬─────────────────────────────────┘
                │                         │
                │                         ▼
                │              ┌────────────────────────────────────────────┐
                │              │    Record in Database                      │
                │              │    services/failed_documents_service.py    │
                │              │    ┌─────────────────────────────────┐    │
                │              │    │ failed_documents table:         │    │
                │              │    │ • project_id, filename, path    │    │
                │              │    │ • error_type, error_message     │    │
                │              │    │ • retry_count, max_retries      │    │
                │              │    │ • status, next_retry_at         │    │
                │              │    │ • failed_stage, task_id         │    │
                │              │    └─────────────────────────────────┘    │
                │              └──────────┬─────────────────────────────────┘
                │                         │
                │                         ▼
                │              ┌────────────────────────────────────────────┐
                │              │    Should Retry?                           │
                │              └──────┬──────────────────┬──────────────────┘
                │                     │                  │
                │              ┌──────▼────────┐  ┌──────▼─────────────┐
                │              │ can_auto_retry│  │ cannot retry       │
                │              │ = true        │  │ (permanent, user)  │
                │              └──────┬────────┘  └──────┬─────────────┘
                │                     │                  │
                │                     │                  ▼
                │                     │         ┌─────────────────────┐
                │                     │         │ PERMANENTLY_FAILED  │
                │                     │         │ • Notify user       │
                │                     │         │ • Alert admin (if   │
                │                     │         │   system issue)     │
                │                     │         └─────────────────────┘
                │                     │
                │                     ▼
                │         ┌───────────────────────────┐
                │         │   Apply Retry Logic       │
                │         │   ┌──────────────────┐    │
                │         │   │ retry_count < max│    │
                │         │   │ retries?         │    │
                │         │   └────┬─────────────┘    │
                │         │        │                  │
                │         │   ┌────▼─────────────┐    │
                │         │   │ Calculate delay: │    │
                │         │   │ - Base delay     │    │
                │         │   │ - Exponential    │    │
                │         │   │   backoff:       │    │
                │         │   │   delay * 2^retry│    │
                │         │   └────┬─────────────┘    │
                │         └────────┼──────────────────┘
                │                  │
                │                  ▼
                │         ┌────────────────────────┐
                │         │ Celery Retry Queue     │
                │         │ • Status: RETRYING     │
                │         │ • next_retry_at set    │
                │         └────────┬───────────────┘
                │                  │
                │                  │
                ▼                  │
        ┌────────────────┐         │
        │   RESOLVED     │         │
        │   • Update DB  │         │
        │   • Mark doc   │         │
        │     complete   │         │
        └────────────────┘         │
                                   │
                                   └──────────┐
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AUTOMATED RETRY PROCESSOR                               │
│  Celery Beat Scheduled Task (every 5 minutes)                               │
│  tasks/retry_processor_tasks.py                                             │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │ 1. Query: SELECT * FROM failed_documents                    │           │
│  │    WHERE status = 'retrying'                                │           │
│  │    AND retry_count < max_retries                            │           │
│  │    AND (next_retry_at IS NULL OR next_retry_at <= NOW())   │           │
│  │                                                             │           │
│  │ 2. For each document:                                       │           │
│  │    - Re-submit to ingest_document_async                    │           │
│  │    - Increment retry_count                                 │           │
│  │    - Update last_retry_at                                  │           │
│  └─────────────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   └──────────┐
                                              │
                                              ▼
                                   ┌─────────────────────┐
                                   │  Retry Loop Back    │
                                   │  to Celery Task     │
                                   └─────────────────────┘
```

---

## 🔄 Retry State Machine

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FAILED DOCUMENT LIFECYCLE                         │
└──────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────┐
                            │   FAILURE   │
                            │  (Exception) │
                            └──────┬──────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  Error Classification       │
                    └──────────────┬──────────────┘
                                   │
            ┌──────────────────────┴──────────────────────┐
            │                                             │
     ┌──────▼────────┐                          ┌────────▼──────────┐
     │ can_auto_retry│                          │ cannot_auto_retry │
     │ = true        │                          │ = false           │
     └──────┬────────┘                          └────────┬──────────┘
            │                                            │
            ▼                                            ▼
    ┌───────────────┐                          ┌─────────────────────┐
    │   RETRYING    │                          │ PERMANENTLY_FAILED  │
    │ ┌───────────┐ │                          │ • User-fixable error│
    │ │retry_count│ │                          │ • Permanent error   │
    │ │< max      │ │                          │ • No retry allowed  │
    │ └─────┬─────┘ │                          └─────────────────────┘
    │       │       │                                     │
    │  ┌────▼────┐  │                                     │
    │  │ Retry   │  │                                     │
    │  │ Attempt │  │                                     │
    │  └────┬────┘  │                                     │
    │       │       │                                     │
    └───────┼───────┘                                     │
            │                                             │
      ┌─────┴─────┐                                       │
      │           │                                       │
  ┌───▼───┐  ┌────▼────┐                                 │
  │SUCCESS│  │ FAILURE  │                                 │
  └───┬───┘  └────┬─────┘                                 │
      │           │                                       │
      │      ┌────▼─────────────┐                         │
      │      │retry_count < max?│                         │
      │      └────┬─────────┬───┘                         │
      │           │         │                             │
      │      ┌────▼───┐ ┌───▼────────────────┐            │
      │      │  YES   │ │       NO           │            │
      │      └────┬───┘ └───┬────────────────┘            │
      │           │         │                             │
      │           │    ┌────▼─────────────────┐           │
      │           │    │ PERMANENTLY_FAILED   │           │
      │           │    │ (exceeded max_retries)│          │
      │           │    └──────────────────────┘           │
      │           │                                       │
      │      ┌────▼──────────────┐                        │
      │      │ Schedule Next     │                        │
      │      │ Retry (RETRYING)  │                        │
      │      └────┬──────────────┘                        │
      │           │                                       │
      │           └───────────┐                           │
      │                       │                           │
      ▼                       ▼                           ▼
┌──────────┐         ┌────────────────┐         ┌─────────────┐
│ RESOLVED │         │   Auto Retry   │         │   IGNORED   │
│          │         │   (Beat Task)  │         │  (Manual)   │
└──────────┘         └────────────────┘         └─────────────┘
```

---

## 📊 Retry Configuration by Error Type

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ERROR TYPE → RETRY CONFIGURATION                       │
└─────────────────────────────────────────────────────────────────────────────┘

╔════════════════╦═════════╦══════════╦═══════════╦══════════╦═════════╗
║  Error Type    ║ Max     ║ Initial  ║ Exp.      ║ Notify   ║ Alert   ║
║                ║ Retries ║ Delay    ║ Backoff   ║ User     ║ Admin   ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ TRANSIENT      ║    5    ║   60s    ║    YES    ║    NO    ║   NO    ║
║ (network,      ║         ║          ║ 60→120→   ║          ║         ║
║  Redis down)   ║         ║          ║ 240→480s  ║          ║         ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ RATE_LIMIT     ║   10    ║  300s    ║    YES    ║    NO    ║   YES   ║
║ (API throttle) ║         ║  (5min)  ║ 5→10→20   ║          ║         ║
║                ║         ║          ║ →40 min   ║          ║         ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ TIMEOUT        ║    2    ║  120s    ║    NO     ║    NO    ║   NO    ║
║ (process time) ║         ║  (2min)  ║           ║          ║         ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ SYSTEM_ISSUE   ║    3    ║  300s    ║    YES    ║   YES    ║   YES   ║
║ (disk full,    ║         ║  (5min)  ║ 5→10→20   ║          ║  URGENT ║
║  OOM)          ║         ║          ║ min       ║          ║         ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ PERMANENT      ║    0    ║   N/A    ║    N/A    ║   YES    ║   NO    ║
║ (corrupted)    ║         ║          ║           ║          ║         ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ USER_FIXABLE   ║    0    ║   N/A    ║    N/A    ║   YES    ║   NO    ║
║ (password,     ║         ║          ║           ║  ACTION  ║         ║
║  file size)    ║         ║          ║           ║ REQUIRED ║         ║
╠════════════════╬═════════╬══════════╬═══════════╬══════════╬═════════╣
║ UNKNOWN        ║    3    ║   60s    ║    YES    ║    NO    ║   NO    ║
║ (unclassified) ║         ║  (1min)  ║ 1→2→4 min ║          ║         ║
╚════════════════╩═════════╩══════════╩═══════════╩══════════╩═════════╝

Legend:
  Exp. Backoff = Exponential Backoff (delay doubles each retry)
  Notify User  = Send notification to user who uploaded
  Alert Admin  = Send alert to system administrators
```

---

## 🗄️ Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          failed_documents TABLE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┬────────────────┬─────────────────────────────────┐
│ Column               │ Type           │ Description                     │
├──────────────────────┼────────────────┼─────────────────────────────────┤
│ id                   │ INTEGER PK     │ Primary key                     │
│ project_id           │ INTEGER FK     │ → projects.id                   │
│ user_id              │ INTEGER        │ User who uploaded               │
│ filename             │ VARCHAR(500)   │ Original filename               │
│ file_path            │ TEXT           │ Absolute path to file           │
│ file_size            │ INTEGER        │ File size in bytes              │
│ error_type           │ ENUM           │ transient, permanent, etc.      │
│ error_message        │ TEXT           │ Sanitized error message         │
│ error_details        │ TEXT           │ Full stack trace (debug)        │
│ retry_count          │ INTEGER        │ Current retry attempts          │
│ max_retries          │ INTEGER        │ Maximum allowed retries         │
│ last_retry_at        │ TIMESTAMP      │ Last retry timestamp            │
│ next_retry_at        │ TIMESTAMP      │ Scheduled next retry            │
│ status               │ ENUM           │ retrying, permanently_failed... │
│ failed_stage         │ VARCHAR(100)   │ extraction, chunking, etc.      │
│ processing_duration  │ FLOAT          │ Time spent before failure (sec) │
│ task_id              │ VARCHAR(255)   │ Celery task ID                  │
│ resolution_notes     │ TEXT           │ Admin resolution notes          │
│ created_at           │ TIMESTAMP      │ First failure timestamp         │
│ updated_at           │ TIMESTAMP      │ Last update                     │
│ resolved_at          │ TIMESTAMP      │ Resolution timestamp            │
└──────────────────────┴────────────────┴─────────────────────────────────┘

INDEXES:
  • idx_failed_documents_project_id (project_id)
  • idx_failed_documents_status (status)
  • idx_failed_documents_error_type (error_type)
  • idx_failed_documents_task_id (task_id)
  • idx_failed_documents_retry_schedule (status, next_retry_at) ← RETRY QUERY
  • idx_failed_documents_project_status (project_id, status)
  • idx_failed_documents_created_status (created_at, status)

┌─────────────────────────────────────────────────────────────────────────────┐
│                      processing_checkpoints TABLE                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┬────────────────┬─────────────────────────────────┐
│ Column               │ Type           │ Description                     │
├──────────────────────┼────────────────┼─────────────────────────────────┤
│ id                   │ INTEGER PK     │ Primary key                     │
│ document_identifier  │ VARCHAR(255)   │ Unique doc hash (filename+proj) │
│ project_id           │ INTEGER FK     │ → projects.id                   │
│ stage                │ VARCHAR(50)    │ extraction, chunking, embedding │
│ checkpoint_data      │ TEXT (JSON)    │ Stage-specific results          │
│ created_at           │ TIMESTAMP      │ Checkpoint creation time        │
│ expires_at           │ TIMESTAMP      │ Auto-cleanup after 7 days       │
└──────────────────────┴────────────────┴─────────────────────────────────┘

INDEXES:
  • idx_checkpoints_document_id (document_identifier) ← UNIQUE
  • idx_checkpoints_expires_at (expires_at) ← CLEANUP QUERY
```

---

## 🔁 Retry Query Logic

```sql
-- Automated Retry Processor Query (runs every 5 minutes)
SELECT *
FROM failed_documents
WHERE status = 'retrying'
  AND retry_count < max_retries
  AND (next_retry_at IS NULL OR next_retry_at <= NOW())
ORDER BY next_retry_at ASC NULLS FIRST
LIMIT 50;

-- Manual Retry from Admin Dashboard
UPDATE failed_documents
SET next_retry_at = NOW() + INTERVAL '0 seconds',
    status = 'retrying',
    updated_at = NOW()
WHERE id = $1;

-- Mark as Resolved (after successful ingestion)
UPDATE failed_documents
SET status = 'resolved',
    resolved_at = NOW(),
    resolution_notes = 'Successfully processed on retry',
    updated_at = NOW()
WHERE id = $1;

-- Mark as Permanently Failed (exceeded retries)
UPDATE failed_documents
SET status = 'permanently_failed',
    next_retry_at = NULL,
    updated_at = NOW()
WHERE id = $1;
```

---

## 📡 API Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FAILED DOCUMENTS API ENDPOINTS                         │
└─────────────────────────────────────────────────────────────────────────────┘

GET /api/v1/documents/failed
├─ Query Parameters:
│  ├─ project_id: int (optional)
│  ├─ status: retrying|permanently_failed|resolved|ignored
│  ├─ error_type: transient|permanent|user_fixable|system_issue|...
│  ├─ limit: int (default 100)
│  └─ offset: int (default 0)
├─ Response: FailedDocumentListResponse
│  ├─ items: List[FailedDocumentResponse]
│  ├─ total_count: int
│  ├─ limit: int
│  └─ offset: int
└─ Use Case: Admin dashboard, user failed uploads list

GET /api/v1/documents/failed/{failed_document_id}
├─ Path Parameters:
│  └─ failed_document_id: int
├─ Response: FailedDocumentResponse
└─ Use Case: View detailed error information

POST /api/v1/documents/failed/{failed_document_id}/retry
├─ Path Parameters:
│  └─ failed_document_id: int
├─ Request Body: RetryFailedDocumentRequest
│  └─ retry_delay_seconds: int | null (0-3600)
├─ Response: FailedDocumentResponse (updated)
└─ Use Case: Manual retry trigger from admin/user dashboard

PATCH /api/v1/documents/failed/{failed_document_id}
├─ Path Parameters:
│  └─ failed_document_id: int
├─ Request Body: UpdateFailedDocumentRequest
│  ├─ status: resolved|permanently_failed|ignored
│  └─ resolution_notes: string | null
├─ Response: FailedDocumentResponse (updated)
└─ Use Case: Admin marks as resolved/ignored after manual fix

DELETE /api/v1/documents/failed/{failed_document_id}
├─ Path Parameters:
│  └─ failed_document_id: int
├─ Response: 204 No Content
└─ Use Case: Delete failed document record and file

GET /api/v1/documents/failed/metrics
├─ Query Parameters:
│  ├─ project_id: int (optional)
│  └─ days: int (default 7)
├─ Response: FailureMetricsResponse
│  ├─ total_failures: int
│  ├─ by_error_type: dict
│  ├─ by_status: dict
│  ├─ avg_retry_count: float
│  └─ success_rate: float
└─ Use Case: Monitoring dashboard, failure analytics

GET /api/v1/health
├─ Response: SystemHealthResponse
│  ├─ status: healthy|degraded|unhealthy
│  ├─ celery_workers: int
│  ├─ redis_connected: bool
│  ├─ database_connected: bool
│  ├─ failed_tasks_24h: int
│  └─ success_rate_24h: float
└─ Use Case: Health check monitoring, alerting systems
```

---

## ⏰ Scheduled Tasks (Celery Beat)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CELERY BEAT SCHEDULE                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ process-retry-queue                                                  │
├──────────────────────────────────────────────────────────────────────┤
│ Task: tasks.retry.process_retry_queue                                │
│ Schedule: Every 5 minutes (300 seconds)                              │
│ Queue: low_priority                                                  │
│ Description: Automatically processes failed documents pending retry  │
│ Logic:                                                               │
│   1. Query failed_documents WHERE status='retrying' AND              │
│      retry_count < max_retries AND next_retry_at <= NOW()           │
│   2. For each document: re-submit to ingest_document_async           │
│   3. Increment retry_count, update last_retry_at                     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ cleanup-orphaned-failed-files                                        │
├──────────────────────────────────────────────────────────────────────┤
│ Task: tasks.maintenance.cleanup_orphaned_failed_files                │
│ Schedule: Daily (86400 seconds)                                      │
│ Queue: low_priority                                                  │
│ Description: Delete files from permanently failed/resolved uploads   │
│ Logic:                                                               │
│   1. Query failed_documents WHERE                                    │
│      (status='permanently_failed' OR status='resolved') AND          │
│      created_at < NOW() - INTERVAL '7 days'                          │
│   2. For each: validate path, delete file, log metrics               │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ cleanup-expired-checkpoints                                          │
├──────────────────────────────────────────────────────────────────────┤
│ Task: tasks.maintenance.cleanup_expired_checkpoints                  │
│ Schedule: Daily (86400 seconds)                                      │
│ Queue: low_priority                                                  │
│ Description: Delete expired processing checkpoints                   │
│ Logic:                                                               │
│   1. DELETE FROM processing_checkpoints                              │
│      WHERE expires_at < NOW()                                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYER ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│   User      │
│  Upload     │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ INPUT VALIDATION                                                 │
│ ✓ File type: PDF only                                           │
│ ✓ File size: < 100MB                                            │
│ ✓ SHA256 hash: duplicate check                                  │
│ ✓ Project ID: exists in database                                │
│ ✓ File path: within uploads/ directory (no traversal)           │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ ERROR SANITIZATION                                               │
│ ✓ Remove user paths: /home/user → /home/[user]                  │
│ ✓ Remove IPs: 192.168.1.1 → [IP]                                │
│ ✓ Remove passwords: password=abc → password=[REDACTED]          │
│ ✓ Remove API keys: api_key=xyz → api_key=[REDACTED]             │
│ ✓ Remove tokens: token=xyz → token=[REDACTED]                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ DATABASE SECURITY                                                │
│ ✓ Parameterized queries (SQLAlchemy ORM)                        │
│ ✓ Foreign key constraints with CASCADE                          │
│ ✓ Enum constraints (error_type, status)                         │
│ ✓ Index on sensitive queries                                    │
│ ✓ Audit trail: created_at, updated_at, user_id                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ LOGGING SECURITY                                                 │
│ ✓ Sanitized error messages in logs                              │
│ ✓ Task ID tracking for audit                                    │
│ ✓ User ID tracking for accountability                           │
│ ✓ No sensitive data in INFO/WARNING logs                        │
│ ✓ Full details only in ERROR logs (admin access)                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📈 Monitoring & Metrics

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MONITORING DASHBOARD                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ FAILURE METRICS (Last 24 Hours)                                 │
├──────────────────────────────────────────────────────────────────┤
│ Total Failures:           45                                     │
│ Success Rate:             94.5%                                  │
│ Avg Retry Count:          1.8                                    │
│                                                                  │
│ By Error Type:                                                   │
│   ├─ Transient:          30 (66.7%)                              │
│   ├─ Timeout:            8  (17.8%)                              │
│   ├─ Rate Limit:         5  (11.1%)                              │
│   ├─ User Fixable:       2  (4.4%)                               │
│   └─ System Issue:       0  (0.0%)                               │
│                                                                  │
│ By Status:                                                       │
│   ├─ Retrying:           12 (26.7%)                              │
│   ├─ Resolved:           31 (68.9%)                              │
│   ├─ Permanently Failed: 2  (4.4%)                               │
│   └─ Ignored:            0  (0.0%)                               │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ SYSTEM HEALTH                                                    │
├──────────────────────────────────────────────────────────────────┤
│ Status:              ✅ HEALTHY                                  │
│ Celery Workers:      2 active                                    │
│ Redis:               ✅ Connected                                │
│ Database:            ✅ Connected                                │
│ Avg Processing Time: 45.3 seconds                                │
│ Queue Depth:         3 documents                                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ ALERTS & NOTIFICATIONS                                           │
├──────────────────────────────────────────────────────────────────┤
│ ⚠️  Rate Limit Threshold: 5 failures in last hour               │
│     → Admin Alert Sent                                           │
│                                                                  │
│ 📧  User Notifications Pending: 2                                │
│     → Password-protected PDFs require user action                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment Checklist

```
□ 1. Apply Database Migration
    cd ai_brain
    alembic upgrade head

□ 2. Verify Models Imported
    python -c "from db.models_failed_documents import FailedDocument; print('✅')"

□ 3. Verify Services Imported
    python -c "from services.error_classifier import error_classifier; print('✅')"
    python -c "from services.failed_documents_service import failed_documents_service; print('✅')"

□ 4. Restart Celery Workers
    celery -A celery_app control shutdown
    celery -A celery_app worker --loglevel=info --pool=solo

□ 5. Start Celery Beat (Scheduled Tasks)
    celery -A celery_app beat --loglevel=info

□ 6. Restart API Server
    python run_server.py

□ 7. Verify System Health
    curl http://localhost:8000/api/v1/health

□ 8. Test Failure Recording
    # Upload a corrupted PDF and verify it appears in failed_documents table
    # Query: SELECT * FROM failed_documents ORDER BY created_at DESC LIMIT 1;

□ 9. Monitor Logs
    tail -f logs/app.log
    # Watch for "Failed document recorded for tracking" messages

□ 10. Setup Monitoring Dashboard
    # Configure Flower: celery -A celery_app flower
    # Access: http://localhost:5555
```

---

**Legend:**
- 🔄 Automatic Process
- 👤 User Action Required
- 🔧 Admin Intervention
- ⏰ Scheduled Task
- 📊 Monitoring Point
- 🔐 Security Check
