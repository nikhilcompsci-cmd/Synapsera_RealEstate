# Environment Configuration Files

This folder contains all environment configuration files for the AI Brain application.

## Files

### `.env` (Active Configuration)
The active environment configuration file. This file is git-ignored and contains your actual secrets and configuration.

**To set up:**
```powershell
# Copy from example
Copy-Item environment\.env.example environment\.env

# Edit with your values
notepad environment\.env
```

### `.env.example`
Template for local development. Contains all required environment variables with example values.

### `.env.development.example`
Development-specific configuration template.

### `.env.production.example`
Production-specific configuration template with security best practices.

### `.env.sentry.example`
Sentry error tracking configuration template.

### `.env.docker`
Docker-specific environment configuration used by `docker-compose.yml`.

## Usage

### Local Development
1. Copy `.env.example` to `.env`
2. Update values in `.env` with your API keys and settings
3. The application automatically loads `environment/.env` via `config/settings.py`

### Docker Deployment
1. Update `environment/.env.docker` with your configuration
2. Run: `docker-compose up -d`

### Environment Variables Reference

#### Database
- `DATABASE_URL` - PostgreSQL connection string
- `DB_ECHO` - Enable SQL query logging (true/false)

#### OpenAI
- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `OPENAI_MODEL` - Model to use (default: gpt-4o-mini)
- `OPENAI_TEMPERATURE` - Response randomness (0.0-1.0)
- `OPENAI_MAX_TOKENS` - Maximum response length

#### Redis & Celery
- `REDIS_URL` - Redis connection string
- `CELERY_BROKER_URL` - Celery message broker URL
- `CELERY_RESULT_BACKEND` - Celery result storage URL

#### Application
- `ENV` - Environment (development/production)
- `DEBUG` - Debug mode (true/false)
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

#### Document AI (Optional)
- `ENABLE_DOCUMENT_AI` - Enable Google Document AI (true/false)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google Cloud credentials JSON
- `DOCUMENT_AI_PROJECT_ID` - Google Cloud project ID
- `DOCUMENT_AI_LOCATION` - Document AI location (us/eu/asia)
- `DOCUMENT_AI_PROCESSOR_ID` - Document AI processor ID

#### Sentry (Optional)
- `SENTRY_DSN` - Sentry error tracking DSN
- `SENTRY_ENVIRONMENT` - Environment name for Sentry
- `SENTRY_TRACES_SAMPLE_RATE` - Trace sampling rate (0.0-1.0)

#### File Upload
- `MAX_FILE_SIZE_MB` - Maximum upload file size in MB
- `UPLOAD_DIR` - Directory for uploaded files

## Security Notes

⚠️ **IMPORTANT:**
- Never commit `.env` files with real secrets to git
- Use example files as templates only
- Rotate API keys regularly
- Use strong passwords for production databases
- Enable TLS/SSL for production Redis and PostgreSQL

## Troubleshooting

### Application can't find .env file
Make sure the file is at `environment/.env` relative to the project root.

### Environment variables not loading
1. Check file path in `config/settings.py` (`env_file="environment/.env"`)
2. Verify file permissions
3. Check for syntax errors in `.env` file

### Docker can't find env file
Update `docker-compose.yml` to reference `environment/.env.docker`:
```yaml
env_file:
  - environment/.env.docker
```
