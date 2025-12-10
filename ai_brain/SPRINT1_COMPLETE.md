# 🚀 Sprint 1 - Setup & Verification Guide

## ✅ SPRINT 1 DELIVERABLES COMPLETED

### 📁 Project Structure
```
ai_brain/
├── api/
│   ├── __init__.py
│   ├── project_router.py      ✅ POST & GET /project endpoints
│   ├── schemas.py              ✅ Pydantic v2 schemas
│   ├── document_router.py      (placeholder for Sprint 2)
│   └── chat_router.py          (placeholder for Sprint 3)
├── config/
│   ├── __init__.py
│   └── settings.py             ✅ BaseSettings with environment support
├── db/
│   ├── __init__.py
│   ├── session.py              ✅ Async engine + AsyncSessionLocal + get_db_session()
│   ├── models.py               ✅ Base + Project model
│   └── repositories/
│       ├── __init__.py
│       └── project_repository.py ✅ No commit/rollback in repo
├── alembic/
│   ├── env.py                  ✅ Async Alembic configuration
│   ├── script.py.mako
│   └── versions/
│       └── 001_create_projects_table.py ✅ Initial migration
├── main.py                     ✅ FastAPI app with lifespan, CORS, routers
├── docker-compose.yml          ✅ Postgres + Adminer
├── pyproject.toml              ✅ All dependencies
├── alembic.ini                 ✅ Alembic config
├── .env.example
├── .gitignore
├── README.md
├── setup.bat                   ✅ Automated setup script
└── test_setup.py               ✅ Database verification script
```

### 🎯 Sprint 1 Goals - ALL MET

1. ✅ **FastAPI App Scaffold**: `main.py` with lifespan, CORS, routers
2. ✅ **Settings**: `config/settings.py` using Pydantic BaseSettings
3. ✅ **Async Database**: `db/session.py` with AsyncEngine + async_sessionmaker
4. ✅ **ORM Models**: Base class + Project model with timestamps
5. ✅ **Repository Pattern**: ProjectRepository with NO commit/rollback
6. ✅ **API Endpoints**:
   - POST /api/v1/project (create project)
   - GET /api/v1/project (list projects)
   - GET /health (health check)
7. ✅ **Alembic**: Initialized with async support + first migration
8. ✅ **Docker Compose**: PostgreSQL + Adminer
9. ✅ **Dependencies**: pyproject.toml with all required packages

---

## 🛠️ SETUP INSTRUCTIONS

### Option A: Automated Setup (Recommended)

```powershell
cd "c:\Learning\My Project\Synapsera_RealEstate\ai_brain"
.\setup.bat
```

This script will:
1. Start Docker containers
2. Wait for PostgreSQL
3. Run Alembic migrations
4. Test database connection

### Option B: Manual Setup

#### 1. Install Dependencies

```powershell
# Using Poetry (recommended)
poetry install
poetry shell

# OR using pip
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic pydantic-settings python-multipart
```

#### 2. Start Database

```powershell
docker-compose up -d
```

Wait 5-10 seconds for PostgreSQL to initialize.

#### 3. Run Migrations

```powershell
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, create projects table
```

#### 4. Verify Setup

```powershell
python test_setup.py
```

Expected output:
```
🔍 Testing database connection...
✅ Database connection successful!
✅ Found 0 projects in database
✨ All tests passed! Ready to start the application.
```

---

## 🚀 RUNNING THE APPLICATION

### Start the API Server

```powershell
uvicorn main:app --reload
```

Or:

```powershell
python main.py
```

### Access Points

- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Database Admin (Adminer)**: http://localhost:8080

---

## 🧪 TESTING THE API

### 1. Health Check

**Request:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-12-09T12:00:00.000000"
}
```

### 2. Create a Project

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/project" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown Office Complex",
    "description": "Analysis of commercial real estate documentation"
  }'
```

**Expected Response:**
```json
{
  "id": 1,
  "name": "Downtown Office Complex",
  "description": "Analysis of commercial real estate documentation",
  "created_at": "2025-12-09T12:00:00.000000",
  "updated_at": "2025-12-09T12:00:00.000000"
}
```

### 3. List All Projects

**Request:**
```bash
curl http://localhost:8000/api/v1/project
```

**Expected Response:**
```json
[
  {
    "id": 1,
    "name": "Downtown Office Complex",
    "description": "Analysis of commercial real estate documentation",
    "created_at": "2025-12-09T12:00:00.000000",
    "updated_at": "2025-12-09T12:00:00.000000"
  }
]
```

### Using Interactive Docs

Visit http://localhost:8000/docs and use the built-in Swagger UI to:
1. Click on an endpoint
2. Click "Try it out"
3. Fill in the request body (for POST)
4. Click "Execute"
5. View the response

---

## 🗄️ DATABASE ACCESS

### Adminer (Web Interface)

1. Navigate to http://localhost:8080
2. Login with:
   - **System**: PostgreSQL
   - **Server**: postgres
   - **Username**: postgres
   - **Password**: postgres
   - **Database**: ai_brain

### Command Line (psql)

```powershell
docker exec -it ai_brain_postgres psql -U postgres -d ai_brain
```

Then run SQL:
```sql
-- View all projects
SELECT * FROM projects;

-- Count projects
SELECT COUNT(*) FROM projects;
```

---

## 🔍 ARCHITECTURE VERIFICATION

### ✅ Clean Architecture Principles

1. **Separation of Concerns**:
   - `api/` - HTTP layer (routers, schemas)
   - `db/` - Data layer (models, repositories, session)
   - `config/` - Configuration layer
   - `services/` - Business logic layer (ready for Sprint 2)

2. **Dependency Injection**:
   - `get_db_session()` dependency in routers
   - Repository pattern with session injection

3. **Async Patterns**:
   - All database operations are async
   - Proper async context managers
   - No blocking I/O

4. **Transaction Management**:
   - ✅ Repositories do NOT commit/rollback
   - ✅ Transaction control in router layer
   - ✅ Exception handling with rollback

### ✅ Code Quality Checklist

- [x] Type hints everywhere
- [x] Pydantic v2 for validation
- [x] SQLAlchemy 2.0 async patterns
- [x] No nested begin() calls
- [x] Proper error handling
- [x] Environment variable support
- [x] CORS configuration
- [x] Database connection pooling
- [x] Migration versioning
- [x] Modular structure (not monolithic)

---

## 🐛 TROUBLESHOOTING

### Database Connection Fails

```powershell
# Check if containers are running
docker ps

# Check PostgreSQL logs
docker logs ai_brain_postgres

# Restart containers
docker-compose down
docker-compose up -d
```

### Migration Errors

```powershell
# Check current migration version
alembic current

# View migration history
alembic history

# Rollback if needed
alembic downgrade -1

# Re-run migrations
alembic upgrade head
```

### Import Errors

Make sure you're in the correct directory:
```powershell
cd "c:\Learning\My Project\Synapsera_RealEstate\ai_brain"
```

And that dependencies are installed:
```powershell
pip list | Select-String -Pattern "fastapi|sqlalchemy|alembic"
```

---

## 📊 NEXT STEPS (Sprint 2 Preview)

Sprint 2 will add:
- Document upload endpoint
- PDF extraction (PyPDF2/pdfplumber)
- Text chunking with overlap
- Document model + repository
- Chunk model + repository
- Document-Project relationship

---

## 📝 NOTES FOR FUTURE SPRINTS

### Repository Pattern Rules
- Repositories should NEVER call `commit()`, `rollback()`, or `begin()`
- Always use `flush()` to get IDs without committing
- Let the router/controller handle transactions

### Async Best Practices
- Always use `async with` for sessions
- Use `await` for all database operations
- Use `AsyncSession` type hints
- Don't mix sync and async code

### Alembic Migrations
- Generate migrations with: `alembic revision --autogenerate -m "message"`
- Always review auto-generated migrations
- Test migrations in dev before production
- Keep migrations small and focused

---

## ✅ SPRINT 1 SIGN-OFF

**Status**: ✅ COMPLETE

All deliverables met:
- ✅ Project structure created
- ✅ FastAPI app running
- ✅ Database configured and migrated
- ✅ All required endpoints working
- ✅ Clean architecture implemented
- ✅ Proper async transaction patterns
- ✅ No nested begin() or commit() in repositories
- ✅ Docker Compose setup
- ✅ Documentation complete

**Ready for Sprint 2!** 🚀
