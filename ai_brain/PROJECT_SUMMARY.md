# AI Brain - Real Estate Document Analysis System
## Project Summary & Technical Documentation

**Version:** 0.1.0  
**Status:** Development (Feature Branch: Improve_Chunks_Accuracy)  
**Last Updated:** December 11, 2025

---

## 📋 Executive Summary

AI Brain is a production-grade **AI-powered document analysis system** specifically designed for real estate document processing. The system leverages **RAG (Retrieval-Augmented Generation)** to enable intelligent question-answering over uploaded documents.

### Key Capabilities
- ✅ **Asynchronous Document Ingestion** (PDF processing with OCR fallback)
- ✅ **Intelligent Chunking & Embedding** (Sentence transformers + FAISS vector search)
- ✅ **LLM-Powered Q&A** (OpenAI integration with context-aware responses)
- ✅ **Comprehensive Failure Recovery** (Smart retry, error classification, auto-recovery)
- ✅ **Production-Ready Infrastructure** (Celery + Redis + PostgreSQL + Sentry)

---

## 🏗️ System Architecture

### Technology Stack

**Backend Framework:**
- FastAPI 0.109.0 (async REST API)
- Python 3.12
- Uvicorn (ASGI server)

**Database:**
- PostgreSQL (with asyncpg driver)
- SQLAlchemy 2.0 (async ORM)
- Alembic (migrations)

**Task Queue:**
- Celery 5.3.4 (distributed task processing)
- Redis (message broker + result backend)

**AI/ML Components:**
- Sentence Transformers (text embeddings)
- FAISS (vector similarity search)
- OpenAI GPT (LLM for answer generation)
- PDFPlumber (PDF text extraction)
- Pytesseract (OCR for scanned PDFs)

**Monitoring & Observability:**
- Sentry (error tracking & admin alerts)
- Structured logging (file + console)
- Performance metrics tracking

---

## 📊 Database Schema

### Core Tables

**1. projects**
- Project management and organization
- Relationships: one-to-many with documents and failed_documents

**2. documents**
- Uploaded document metadata
- Tracks: filename, file_path, file_size, upload_date, processing status

**3. chunks**
- Text chunks extracted from documents
- Fields: chunk_text, chunk_index, embedding (vector)
- Indexed for fast retrieval

**4. failed_documents** ⭐ NEW
- Comprehensive failure tracking and recovery
- 21 fields including error classification, retry management, resolution tracking
- 11 indexes for query performance
- Status: retrying, permanently_failed, resolved, ignored

**5. processing_checkpoints** ⭐ NEW
- Resume capability after failures
- Stores intermediate results (extracted text, chunks, embeddings)
- TTL-based expiration

### Enums

**ErrorType:**
- transient, permanent, user_fixable, system_issue, rate_limit, timeout, unknown

**FailureStatus:**
- retrying, permanently_failed, resolved, ignored

---

## 🔄 Document Ingestion Pipeline

### Phase 1: Upload & Validation
```
1. User uploads PDF via REST API
2. File saved to data/projects/{project_id}/
3. Basic validation (file type, size)
4. Task queued in Celery
```

### Phase 2: Async Processing (Celery Task)
```
1. PDF Text Extraction
   - Try direct text extraction (PDFPlumber)
   - Fallback to OCR if scanned (Pytesseract)
   
2. Text Chunking
   - Split into semantic chunks
   - Preserve context and structure
   
3. Generate Embeddings
   - Sentence transformers model
   - Create vector representations
   
4. Store in Vector Database
   - Save chunks to PostgreSQL
   - Build FAISS index for search
   
5. Update Document Status
   - Mark as processed
   - Record metadata
```

### Phase 3: Error Handling
```
IF error occurs:
  1. Classify error type (7 categories)
  2. Sanitize error message (remove PII)
  3. Record in failed_documents table
  4. Determine retry strategy
  5. Alert admin if system issue
  6. Track in Sentry for monitoring
```

---

## 🤖 RAG (Retrieval-Augmented Generation)

### Query Processing Flow

**1. User Query:**
```
User: "What is the property address?"
```

**2. Query Embedding:**
```python
query_vector = embedding_model.encode(user_query)
```

**3. Similarity Search:**
```python
# Search FAISS index for top-k similar chunks
similar_chunks = faiss_index.search(query_vector, k=5)
```

**4. Context Preparation:**
```python
context = "\n\n".join([chunk.text for chunk in similar_chunks])
```

**5. LLM Generation:**
```python
prompt = f"""
Context: {context}

Question: {user_query}

Answer based on the context above.
"""
answer = openai.chat.completions.create(messages=[prompt])
```

**6. Response:**
```
Assistant: "The property is located at 123 Main Street..."
```

---

## 🛡️ Failure Recovery System

### Error Classification Service

**7 Error Categories:**
1. **Transient** - Temporary issues (network glitches, timeouts)
   - Retry: 5 times, 60s delay, exponential backoff
   
2. **Rate Limit** - API quota exceeded
   - Retry: 10 times, 300s delay, exponential backoff
   
3. **Timeout** - Operations taking too long
   - Retry: 3 times, 120s delay
   
4. **System Issue** - Infrastructure problems
   - Retry: 5 times, 120s delay, **ALERT ADMIN**
   
5. **User Fixable** - Bad file, wrong format
   - Retry: 3 times, 60s delay, notify user
   
6. **Permanent** - Cannot be fixed (corrupted file)
   - No retry, mark as failed
   
7. **Unknown** - Unclassified errors
   - Retry: 3 times, 60s delay

### Auto-Recovery Features

**Smart Retry Logic:**
- Error-specific retry strategies
- Exponential backoff to prevent overload
- Max retries to prevent infinite loops
- Retry scheduling (next_retry_at field)

**Sanitization:**
- Remove file paths, IPs, passwords, API keys
- Anonymize user data in error messages
- Safe for logging and sharing

**Admin Notifications:**
- Sentry integration for critical errors
- Email/Slack alerts (configured in Sentry)
- Real-time error dashboard

**Metrics & Monitoring:**
- Failure rate by error type
- Retry success rate
- Processing duration
- System health status

---

## 🔐 Security Features

### Environment-Based Fallback Control ⭐ NEW

**Development Mode:**
- Celery/Redis optional (graceful fallback to sync)
- Application starts with warnings
- Slower processing but functional

**Production Mode:**
- Celery/Redis REQUIRED (strict enforcement)
- Application fails to start if Redis unavailable
- HTTP 503 if Celery unavailable
- NO silent degradation

### Data Protection

**Sanitization:**
- PII removal from error messages
- Path anonymization
- Credential scrubbing

**Access Control:**
- Project-level isolation
- User-based document filtering
- Foreign key constraints with CASCADE

**Error Tracking:**
- Sentry integration (opt-in)
- Full stack traces with context
- User context tracking

---

## 📈 Performance & Scalability

### Current Optimizations

**Database:**
- 11+ indexes on failed_documents
- Composite indexes for common queries
- Async queries with connection pooling

**Task Processing:**
- Distributed Celery workers
- Priority queues
- Task retry with backoff
- Result caching in Redis

**Vector Search:**
- FAISS indexing for fast similarity search
- Batch embedding generation
- Efficient chunk storage

### Monitoring Metrics

**Key Performance Indicators:**
- Document processing time
- Error rate by type
- Queue depth and latency
- Database query performance
- API response time

---

## 🚀 Deployment

### Requirements

**Infrastructure:**
- Python 3.12+
- PostgreSQL 12+
- Redis 6+
- Tesseract OCR (for scanned PDFs)

**Environment Variables:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Redis/Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Environment
ENVIRONMENT=production  # or development
DEBUG=false

# OpenAI
OPENAI_API_KEY=sk-...

# Sentry (optional)
SENTRY_DSN=https://...
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=production
```

### Startup Process

**1. Database Migration:**
```bash
alembic upgrade head
```

**2. Start Celery Workers:**
```bash
celery -A celery_app worker --loglevel=info
```

**3. Start API Server:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**4. Verify Health:**
```bash
curl http://localhost:8000/api/v1/health
```

---

## 📝 API Endpoints

### Document Management

**POST /api/v1/projects/{project_id}/documents**
- Upload document for ingestion
- Returns: task_id for status tracking

**GET /api/v1/projects/{project_id}/documents**
- List all documents in project
- Pagination support

**GET /api/v1/documents/{document_id}**
- Get document details

**DELETE /api/v1/documents/{document_id}**
- Delete document and associated data

### Question Answering

**POST /api/v1/projects/{project_id}/chat**
- Ask questions about documents
- Returns: AI-generated answer with sources

### System Health

**GET /api/v1/health**
- System health check
- Database connectivity
- Queue status

---

## 🧪 Testing

### Test Coverage

**Unit Tests:**
- Error classification (60+ patterns)
- Failed documents service (8 methods)
- API schemas validation

**Integration Tests:**
- Database models
- Celery task execution
- End-to-end document processing

**Environment Tests:**
- Production fallback behavior
- Development graceful degradation
- Configuration validation

**Test Results:**
- ✅ 7/7 integration tests passing
- ✅ 5/5 environment tests passing
- ✅ 3/3 code verification tests passing

---

## 📚 Documentation

### Available Documentation

1. **FAILURE_RECOVERY_IMPLEMENTATION.md** (600+ lines)
   - Complete system guide
   - Usage examples
   - Deployment steps

2. **RETRY_ARCHITECTURE_DIAGRAM.md** (800+ lines)
   - Visual architecture
   - State machine diagrams
   - Database schema visualization

3. **ENVIRONMENT_FALLBACK.md**
   - Production vs development behavior
   - Configuration guide
   - Troubleshooting

4. **SENTRY_SETUP.md**
   - Error tracking setup
   - Alert configuration
   - Dashboard guide

5. **DEPLOYMENT_COMPLETE.md**
   - Deployment summary
   - Verification steps
   - Monitoring queries

---

## 🎯 Recent Achievements

### Sprint Completion Summary

**✅ Failure Recovery System (COMPLETE)**
- Database models with 21 fields for comprehensive tracking
- Intelligent error classification (7 categories, 60+ patterns)
- Smart retry logic with exponential backoff
- Failed documents service (8 methods)
- Database migration successfully applied (revision 003)
- Integration tests: 7/7 passing

**✅ Environment-Based Security (COMPLETE)**
- Production strict mode (fails fast)
- Development graceful fallback
- Environment detection and validation
- Comprehensive testing

**✅ Sentry Integration (COMPLETE)**
- Error tracking with full context
- Admin alert system
- Performance monitoring
- Email/Slack notification support

**✅ Production Readiness (COMPLETE)**
- Structured logging with rotation
- Database optimizations (11+ indexes)
- Security hardening
- Comprehensive documentation

---

## 🔮 Future Roadmap

### Phase 1: Performance (1-2 weeks)
- [ ] Batch processing (5-10 parallel tasks)
- [ ] Resume/checkpoint system
- [ ] Progress tracking WebSocket
- [ ] Document quality validation

### Phase 2: Intelligence (2-3 weeks)
- [ ] Smart semantic chunking
- [ ] Advanced OCR preprocessing
- [ ] Metadata extraction
- [ ] Hybrid search (BM25 + vector)

### Phase 3: Scale (3-4 weeks)
- [ ] Multi-format support (Word, Excel, images)
- [ ] Caching layer (Redis + CDN)
- [ ] Monitoring dashboard
- [ ] Security enhancements (PII detection)

### Phase 4: Advanced Features (Ongoing)
- [ ] Multi-language support
- [ ] Document relationship mapping
- [ ] Active learning
- [ ] Version control

---

## 📊 Current Statistics

### System Metrics

**Database:**
- 5 tables (projects, documents, chunks, failed_documents, processing_checkpoints)
- 2 custom enums (ErrorType, FailureStatus)
- 20+ indexes for optimized queries

**Code Base:**
- 10+ Python modules
- 5,000+ lines of production code
- 2,000+ lines of documentation
- 1,000+ lines of tests

**Features:**
- 7 error classification categories
- 60+ error detection patterns
- 8 failed document service methods
- 11 database indexes on failed_documents
- 4 comprehensive documentation files

---

## 🛠️ Maintenance & Operations

### Regular Tasks

**Daily:**
- Monitor Sentry for critical errors
- Check failed document queue
- Verify Celery worker health

**Weekly:**
- Review error trends
- Analyze retry success rates
- Check database performance
- Cleanup old logs

**Monthly:**
- Database maintenance (VACUUM, ANALYZE)
- Review and optimize indexes
- Update dependencies
- Performance benchmarking

### Troubleshooting

**Common Issues:**

1. **Celery not processing tasks**
   - Check: Redis connection
   - Check: Worker processes running
   - Logs: `logs/app.log`

2. **High error rate**
   - Check: Sentry dashboard
   - Review: Failed documents by error_type
   - Action: Check external service status

3. **Slow document processing**
   - Check: Queue depth
   - Check: Worker count
   - Optimize: Add more workers

---

## 👥 Team & Contact

**Development Team:** AI Brain Team  
**Repository:** nikhilcompsci-cmd/Synapsera_RealEstate  
**Branch:** feature/Improve_Chunks_Accuracy  
**Environment:** Development (staging for production)

---

## 📋 Quick Reference

### Start Development Environment
```bash
# 1. Start Redis
redis-server

# 2. Start Celery worker
python start_celery_worker.py

# 3. Start API
python run_server.py
```

### Run Tests
```bash
# Integration tests
python test_failure_recovery_system.py

# Environment tests
python test_environment_fallback.py

# Code verification
python test_code_verification.py
```

### Database Operations
```bash
# Create migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Check current version
alembic current

# Rollback
alembic downgrade -1
```

### Monitor Logs
```bash
# Tail application logs
tail -f logs/app.log

# Search for errors
grep "ERROR" logs/app.log

# Find admin alerts
grep "ADMIN ALERT" logs/app.log
```

---

## ✅ Production Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Configure production database URL
- [ ] Set up Redis cluster (high availability)
- [ ] Deploy Celery workers (3+ instances)
- [ ] Configure Sentry DSN and enable
- [ ] Set up email/Slack alerts in Sentry
- [ ] Configure SSL/TLS for API
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Run load tests
- [ ] Set up monitoring dashboard
- [ ] Document incident response procedures
- [ ] Train operations team

---

## 📄 License & Legal

**Project Status:** Internal Development  
**Confidentiality:** Proprietary  
**Data Handling:** PII sanitization enabled  
**Compliance:** Ready for GDPR/privacy requirements

---

**Document End**

_This project summary is auto-generated based on codebase analysis and should be updated as the system evolves._
