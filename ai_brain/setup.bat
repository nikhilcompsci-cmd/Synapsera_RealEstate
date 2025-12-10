@echo off
echo ====================================
echo AI Brain - Quick Setup Script
echo ====================================
echo.

echo Step 1: Starting Docker containers...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker containers
    exit /b 1
)
echo ✓ Docker containers started
echo.

echo Step 2: Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak > nul
echo ✓ PostgreSQL should be ready
echo.

echo Step 3: Running database migrations...
alembic upgrade head
if %errorlevel% neq 0 (
    echo ERROR: Failed to run migrations
    exit /b 1
)
echo ✓ Database migrations completed
echo.

echo Step 4: Testing database connection...
python test_setup.py
if %errorlevel% neq 0 (
    echo ERROR: Database connection test failed
    exit /b 1
)
echo.

echo ====================================
echo ✨ Setup Complete!
echo ====================================
echo.
echo You can now start the application:
echo   uvicorn main:app --reload
echo.
echo Or run it with Python:
echo   python main.py
echo.
echo API Documentation: http://localhost:8000/docs
echo Database Admin: http://localhost:8080
echo ====================================
