# Docker Setup and Run Instructions for AI Brain

## Prerequisites
- Docker Desktop installed and running
- At least 4GB RAM available for Docker
- OpenAI API key (required for embeddings)

## Quick Start

### 1. Configure Environment Variables
Edit `environment/.env.docker` and update:
```bash
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 2. Build and Start All Services
```powershell
# Build Docker images
docker-compose build

# Start all services (FastAPI, Celery, PostgreSQL, Redis)
docker-compose up -d

# View logs
docker-compose logs -f app
```

### 3. Run Database Migrations
```powershell
# Run migrations inside the app container
docker-compose exec app python -m alembic upgrade head
```

### 4. Verify Services
```powershell
# Check service status
docker-compose ps

# Test FastAPI endpoint
curl http://localhost:8000/docs

# Test health endpoint
curl http://localhost:8000/health
```

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| FastAPI App | 8000 | Main API server |
| PostgreSQL | 5433 | Database |
| Redis | 6379 | Cache & Celery broker |
| Celery Worker | N/A | Background task processor |
| Adminer | 8081 | Database admin UI |

## Common Commands

### Build and Run
```powershell
# Build images (run after code changes)
docker-compose build

# Start services in background
docker-compose up -d

# Start and view logs
docker-compose up

# Stop services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v
```

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f celery_worker
docker-compose logs -f postgres
```

### Execute Commands Inside Containers
```powershell
# Run migrations
docker-compose exec app python -m alembic upgrade head

# Access Python shell
docker-compose exec app python

# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d ai_brain

# Access Redis CLI
docker-compose exec redis redis-cli
```

### Restart Services
```powershell
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart app
docker-compose restart celery_worker
```

### Scale Celery Workers
```powershell
# Run 3 Celery workers
docker-compose up -d --scale celery_worker=3
```

## Development Workflow

### Code Changes
After modifying code:
```powershell
# Rebuild and restart
docker-compose build app celery_worker
docker-compose up -d app celery_worker

# Or use restart for minor changes (if code is mounted)
docker-compose restart app celery_worker
```

### Database Changes (Migrations)
```powershell
# Create new migration
docker-compose exec app python -m alembic revision -m "your_migration_message"

# Apply migrations
docker-compose exec app python -m alembic upgrade head

# Rollback one migration
docker-compose exec app python -m alembic downgrade -1
```

## Troubleshooting

### Services Won't Start
```powershell
# Check logs for errors
docker-compose logs app
docker-compose logs postgres

# Verify Docker resources
docker system df
docker system prune
```

### Database Connection Issues
```powershell
# Check PostgreSQL is ready
docker-compose exec postgres pg_isready -U postgres

# Check connection from app
docker-compose exec app python -c "from db.session import engine; print('Connected')"
```

### Redis Connection Issues
```powershell
# Check Redis is running
docker-compose exec redis redis-cli ping

# Should return: PONG
```

### Port Already in Use
```powershell
# Find process using port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess

# Or change port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Use 8001 on host instead
```

### Out of Disk Space
```powershell
# Remove unused images and volumes
docker system prune -a --volumes

# Warning: This removes all unused Docker data
```

## Production Deployment

### Security Updates for Production
1. **Update `environment/.env.docker`:**
   - Change `ENV=production`
   - Set strong passwords for PostgreSQL
   - Enable Sentry monitoring
   - Set `DEBUG=false`

2. **Update `docker-compose.yml`:**
   - Remove exposed ports (5433, 6379, 8081)
   - Use Docker secrets for sensitive data
   - Add resource limits
   - Enable restart policies

3. **Enable HTTPS:**
   - Add nginx reverse proxy
   - Configure SSL certificates
   - Update CORS settings

### Backup and Restore
```powershell
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres ai_brain > backup.sql

# Restore PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U postgres ai_brain

# Backup FAISS indices and documents
docker cp ai_brain_app:/app/data ./backup/data
```

## Monitoring

### View Resource Usage
```powershell
# Container stats
docker stats

# Disk usage
docker system df
```

### Access Adminer (Database UI)
1. Open: http://localhost:8081
2. Login:
   - System: PostgreSQL
   - Server: postgres
   - Username: postgres
   - Password: postgres
   - Database: ai_brain

## Environment Variables Reference

See `environment/.env.docker` for all available configuration options:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `OPENAI_API_KEY` - OpenAI API key (required)
- `ENV` - Environment (development/production)
- `DEBUG` - Enable debug mode (true/false)
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)
- `MAX_FILE_SIZE_MB` - Maximum upload file size
- `ENABLE_DOCUMENT_AI` - Enable Google Document AI (true/false)
- `SENTRY_DSN` - Sentry error tracking DSN

## Next Steps

After successful deployment:
1. Test document upload: http://localhost:8000/docs
2. Create a project via API
3. Upload a PDF document
4. Check Celery worker logs for processing
5. Query documents via RAG endpoint

For API documentation, visit: http://localhost:8000/docs
