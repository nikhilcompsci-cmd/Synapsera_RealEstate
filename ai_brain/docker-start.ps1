# Quick Start Script for Docker Deployment
# Run this after docker-compose build completes

Write-Host "=== AI Brain Docker Quick Start ===" -ForegroundColor Green
Write-Host ""

# Step 1: Check Docker is running
Write-Host "Step 1: Checking Docker status..." -ForegroundColor Yellow
$dockerRunning = docker info 2>$null
if (-not $dockerRunning) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker is running" -ForegroundColor Green
Write-Host ""

# Step 2: Start services
Write-Host "Step 2: Starting all services..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start services" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Services started" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for database
Write-Host "Step 3: Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $dbReady = docker-compose exec -T postgres pg_isready -U postgres 2>$null
    if ($dbReady -like "*accepting connections*") {
        Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
        break
    }
    $attempt++
    Write-Host "  Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if ($attempt -eq $maxAttempts) {
    Write-Host "ERROR: PostgreSQL did not start in time" -ForegroundColor Red
    docker-compose logs postgres
    exit 1
}
Write-Host ""

# Step 4: Run migrations
Write-Host "Step 4: Running database migrations..." -ForegroundColor Yellow
docker-compose exec -T app python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Database migration failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Migrations completed" -ForegroundColor Green
Write-Host ""

# Step 5: Check service status
Write-Host "Step 5: Checking service status..." -ForegroundColor Yellow
docker-compose ps
Write-Host ""

# Step 6: Display access information
Write-Host "=== AI Brain Services Ready ===" -ForegroundColor Green
Write-Host ""
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health Check:      http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "Database Admin:    http://localhost:8081" -ForegroundColor Cyan
Write-Host "  Login: postgres / postgres / ai_brain" -ForegroundColor Gray
Write-Host ""
Write-Host "View logs:         docker-compose logs -f app" -ForegroundColor Yellow
Write-Host "Stop services:     docker-compose down" -ForegroundColor Yellow
Write-Host ""

# Step 7: Test health endpoint
Write-Host "Step 7: Testing health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Health check passed: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠ Health check not ready yet. Service may still be starting..." -ForegroundColor Yellow
    Write-Host "  Run: curl http://localhost:8000/health" -ForegroundColor Gray
}
Write-Host ""

Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "Open http://localhost:8000/docs to start using the API" -ForegroundColor Cyan
