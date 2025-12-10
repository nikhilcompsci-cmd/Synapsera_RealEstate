# AI Brain - Real Estate Document Analysis

AI-powered document analysis system with RAG (Retrieval-Augmented Generation) capabilities for real estate projects.

## 🏗️ Architecture

```
ai_brain/
├── api/              # FastAPI routers and schemas
├── config/           # Application settings
├── db/               # Database models, session, and repositories
├── ingestion/        # Document processing and chunking
├── rag/              # Retrieval and LLM engine
├── services/         # Business logic (FAISS, embeddings)
├── ui/               # Frontend interface
├── utils/            # Helper utilities
└── alembic/          # Database migrations
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Poetry (recommended) or pip

### 1. Start Database

```powershell
docker-compose up -d
```

This starts:
- PostgreSQL on `localhost:5432`
- Adminer (DB admin UI) on `http://localhost:8080`

### 2. Install Dependencies

Using Poetry:
```powershell
poetry install
poetry shell
```

Or using pip:
```powershell
pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic pydantic-settings python-multipart
```

### 3. Initialize Database

```powershell
# Create first migration
alembic revision --autogenerate -m "create projects table"

# Apply migration
alembic upgrade head
```

### 4. Run Application

```powershell
uvicorn main:app --reload
```

API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## 📡 API Endpoints (Sprint 1)

### Health Check
```
GET /health
```

### Projects
```
POST /api/v1/project      # Create new project
GET  /api/v1/project      # List all projects
```

## 🗄️ Database Access

**Adminer**: http://localhost:8080
- System: `PostgreSQL`
- Server: `postgres`
- Username: `postgres`
- Password: `postgres`
- Database: `ai_brain`

## 🧪 Testing

```powershell
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html
```

## 📝 Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_brain
DEBUG=true
```

## 🛠️ Development

### Create New Migration

```powershell
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Rollback Migration

```powershell
alembic downgrade -1
```

## 📚 Tech Stack

- **FastAPI**: Modern async web framework
- **SQLAlchemy 2.0**: Async ORM
- **Alembic**: Database migrations
- **Pydantic v2**: Data validation
- **PostgreSQL**: Database
- **Docker**: Containerization

## 🎯 Sprint Status

✅ **Sprint 1**: Foundation & Project Management
- [x] Project structure
- [x] Database setup with async SQLAlchemy
- [x] FastAPI application scaffold
- [x] Project CRUD endpoints
- [x] Alembic migrations
- [x] Docker Compose setup

🔜 **Sprint 2**: Document Ingestion (Upcoming)
🔜 **Sprint 3**: RAG & Chat Interface (Upcoming)

## 📄 License

Proprietary - All Rights Reserved
