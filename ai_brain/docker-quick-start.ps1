# Quick Docker Start Script
# Handles building and starting AI Brain in Docker

param(
    [switch]$NoBuild,
    [switch]$Logs
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== AI Brain Docker Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location "c:\Learning\My Project\Synapsera_RealEstate\ai_brain"

# Step 1: Build (unless -NoBuild is specified)
if (-not $NoBuild) {
    Write-Host "Step 1: Building Docker images..." -ForegroundColor Yellow
    Write-Host "  This may take 5-10 minutes on first build (downloading PyTorch ~900MB)" -ForegroundColor Gray
    Write-Host ""
    
    docker-compose build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Build complete" -ForegroundColor Green
    Write-Host ""
}

# Step 2: Start services
Write-Host "Step 2: Starting services..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for PostgreSQL
Write-Host "Step 3: Waiting for PostgreSQL..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $dbReady = docker-compose exec -T postgres pg_isready -U postgres 2>$null
    if ($dbReady -match "accepting connections") {
        Write-Host "✅ PostgreSQL ready" -ForegroundColor Green
        break
    }
    $attempt++
    Start-Sleep -Seconds 2
    Write-Host "  Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
}

if ($attempt -eq $maxAttempts) {
    Write-Host "❌ PostgreSQL timeout" -ForegroundColor Red
    docker-compose logs postgres
    exit 1
}
Write-Host ""

# Step 4: Wait for app to start
Write-Host "Step 4: Waiting for app container..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$appRunning = docker-compose ps app 2>$null | Select-String "Up"
if (-not $appRunning) {
    Write-Host "⚠️  App container not running. Checking logs..." -ForegroundColor Yellow
    docker-compose logs --tail=20 app
    Write-Host ""
    Write-Host "Run 'docker-compose logs app' for full logs" -ForegroundColor Gray
} else {
    Write-Host "✅ App container running" -ForegroundColor Green
}
Write-Host ""

# Step 5: Run migrations
Write-Host "Step 5: Running database migrations..." -ForegroundColor Yellow
docker-compose exec -T app python -m alembic upgrade head 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Migration failed or app not ready" -ForegroundColor Yellow
    Write-Host "  You can run migrations manually: docker-compose exec app python -m alembic upgrade head" -ForegroundColor Gray
} else {
    Write-Host "✅ Migrations complete" -ForegroundColor Green
}
Write-Host ""

# Step 6: Display status
Write-Host "=== Service Status ===" -ForegroundColor Cyan
docker-compose ps
Write-Host ""

# Step 7: Display access info
Write-Host "=== Access Information ===" -ForegroundColor Green
Write-Host "API Documentation:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health Check:       http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "Database Admin:     http://localhost:8081" -ForegroundColor Cyan
Write-Host "  Login: postgres / postgres / ai_brain" -ForegroundColor Gray
Write-Host ""
Write-Host "=== Useful Commands ===" -ForegroundColor Yellow
Write-Host "View logs:          docker-compose logs -f app" -ForegroundColor Gray
Write-Host "View all logs:      docker-compose logs -f" -ForegroundColor Gray
Write-Host "Stop services:      docker-compose down" -ForegroundColor Gray
Write-Host "Restart services:   docker-compose restart" -ForegroundColor Gray
Write-Host ""

# Show logs if requested
if ($Logs) {
    Write-Host "=== Live Logs (press Ctrl+C to exit) ===" -ForegroundColor Cyan
    docker-compose logs -f
}
