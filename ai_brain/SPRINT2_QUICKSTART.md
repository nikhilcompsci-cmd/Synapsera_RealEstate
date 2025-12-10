# 🚀 SPRINT 2 - Quick Start Guide

## Prerequisites
- Sprint 1 completed and working
- Docker containers running (Postgres + Adminer)
- Python environment activated

## Setup Steps

### 1. Install New Dependencies

```powershell
pip install PyPDF2 sentence-transformers faiss-cpu numpy reportlab
```

### 2. Run Database Migrations

```powershell
python -m alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, create document chunk and embedding tables
```

### 3. Start API Server

```powershell
python start_server.py
```

Server will be available at:
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Adminer**: http://localhost:8081

## Testing

### Run Sprint 2 Tests

```powershell
# In a new terminal
python test_sprint2.py
```

This will:
1. Create a test project
2. Generate a test PDF
3. Upload the PDF
4. Test duplicate detection
5. Check ingestion status
6. Retrieve chunks
7. Count embeddings

### Manual Testing via Swagger UI

1. Visit http://localhost:8000/docs
2. Create a project (if needed)
3. Try "POST /api/v1/project/{project_id}/document/upload"
4. Upload a PDF file
5. Check other endpoints

## API Endpoints

### Upload Document
```
POST /api/v1/project/{project_id}/document/upload
```
Upload a PDF file for ingestion.

### Get Ingestion Status
```
GET /api/v1/project/{project_id}/ingestion-status
```
Check status of all documents in a project.

### Get Document Chunks
```
GET /api/v1/document/{document_id}/chunks
```
Retrieve all chunks from a document.

### Get Embeddings Count
```
GET /api/v1/project/{project_id}/embeddings/count
```
Get total number of embeddings for a project.

## Troubleshooting

### Import Errors
```powershell
# Make sure all dependencies are installed
pip install PyPDF2 sentence-transformers faiss-cpu numpy
```

### Database Errors
```powershell
# Check if migration ran
python -m alembic current

# Re-run if needed
python -m alembic upgrade head
```

### Docker Issues
```powershell
# Restart containers
docker-compose restart

# Check logs
docker logs ai_brain_postgres
```

## File Structure

```
data/
├── uploads/              # Uploaded PDF files
│   └── project_{id}/     # Per-project directories
└── faiss_indexes/        # FAISS index files
    └── project_{id}.faiss
```

## Configuration

### Chunking Settings
Edit in `ingestion_service.py`:
```python
chunk_size = 1000  # characters per chunk
overlap = 200      # overlap between chunks
```

### Embedding Model
Switch from stub to real embeddings:
```python
# In ingestion_service.py
use_stub_embeddings = False  # Use real sentence-transformers
```

## What's Working

✅ PDF upload and storage
✅ Text extraction (PyPDF2)
✅ Content-based deduplication (SHA256 hash)
✅ Text chunking with overlap
✅ Stub embedding generation
✅ FAISS index creation and management
✅ Status tracking (pending/processing/completed/failed)
✅ Error handling and rollback
✅ Async-safe transactions

## Next Steps

Sprint 3 will add:
- Chat interface
- RAG retrieval
- LLM integration
- Streaming responses

---

**Sprint 2 Status**: ✅ COMPLETE AND TESTED
