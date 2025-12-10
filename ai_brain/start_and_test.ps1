# Synapsera Real Estate AI Brain - Quick Start & Test
# ====================================================

Write-Host "`n" -NoNewline
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "  SYNAPSERA REAL ESTATE AI BRAIN - QUICK START" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Check if database is running
Write-Host "[1/6] Checking database..." -ForegroundColor Cyan
$dockerRunning = docker ps --format "{{.Names}}" 2>$null | Select-String "ai_brain_postgres"
if ($dockerRunning) {
    Write-Host "      ✓ Database is running" -ForegroundColor Green
} else {
    Write-Host "      ✗ Database not running. Starting..." -ForegroundColor Yellow
    Write-Host "      Running: docker-compose up -d" -ForegroundColor Gray
    docker-compose up -d
    Start-Sleep -Seconds 5
    Write-Host "      ✓ Database started" -ForegroundColor Green
}

# Start the server in background
Write-Host "`n[2/6] Starting API server..." -ForegroundColor Cyan
Write-Host "      Running: python run_server.py (in background)" -ForegroundColor Gray

$job = Start-Job -ScriptBlock {
    Set-Location "C:\Learning\My Project\Synapsera_RealEstate\ai_brain"
    python run_server.py
}

Write-Host "      Waiting for server to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Test health endpoint
Write-Host "`n[3/6] Testing health endpoint..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
    Write-Host "      ✓ Server is healthy: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "      ✗ Server not responding. Check manually." -ForegroundColor Red
    Write-Host "      Error: $_" -ForegroundColor Red
    Stop-Job $job
    Remove-Job $job
    exit 1
}

# Create a test project
Write-Host "`n[4/6] Creating test project..." -ForegroundColor Cyan
try {
    $projectData = @{
        name = "Downtown Luxury Apartments - Test $(Get-Date -Format 'HHmmss')"
        description = "Automated test project for API validation"
    } | ConvertTo-Json

    $project = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/project" `
        -Method Post `
        -ContentType "application/json" `
        -Body $projectData

    Write-Host "      ✓ Project created with ID: $($project.id)" -ForegroundColor Green
    Write-Host "      Name: $($project.name)" -ForegroundColor Gray
    $projectId = $project.id
} catch {
    Write-Host "      ✗ Failed to create project" -ForegroundColor Red
    Write-Host "      Error: $_" -ForegroundColor Red
}

# List projects
Write-Host "`n[5/6] Listing all projects..." -ForegroundColor Cyan
try {
    $projects = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/project" -Method Get
    Write-Host "      ✓ Found $($projects.Count) project(s)" -ForegroundColor Green
    foreach ($p in $projects) {
        Write-Host "        - ID: $($p.id), Name: $($p.name)" -ForegroundColor Gray
    }
} catch {
    Write-Host "      ✗ Failed to list projects" -ForegroundColor Red
}

# Display instructions
Write-Host "`n[6/6] Server is ready for testing!" -ForegroundColor Cyan
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "  AVAILABLE ENDPOINTS" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "  🌐 Interactive API Docs:  " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  📊 Database Admin:       " -NoNewline
Write-Host "http://localhost:8081" -ForegroundColor Green
Write-Host "  ❤️  Health Check:         " -NoNewline
Write-Host "http://localhost:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "  QUICK TESTS" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Test commands
Write-Host "  Get project by ID:" -ForegroundColor White
Write-Host "  Invoke-RestMethod http://localhost:8000/api/v1/project/$projectId" -ForegroundColor Gray
Write-Host ""

Write-Host "  List all projects:" -ForegroundColor White
Write-Host "  Invoke-RestMethod http://localhost:8000/api/v1/project" -ForegroundColor Gray
Write-Host ""

Write-Host "  Upload a document (use Swagger UI - easier):" -ForegroundColor White
Write-Host "  http://localhost:8000/docs#/Document/upload_document_api_v1_document_upload_post" -ForegroundColor Gray
Write-Host ""

Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "  💡 TIP: Open " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Green -NoNewline
Write-Host " in your browser"
Write-Host "      for the best testing experience!"
Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Keep script running and show server output
try {
    while ($true) {
        $output = Receive-Job $job
        if ($output) {
            Write-Host $output
        }
        Start-Sleep -Seconds 1
        
        # Check if job is still running
        if ($job.State -ne "Running") {
            Write-Host "`n⚠️  Server stopped unexpectedly" -ForegroundColor Red
            break
        }
    }
} finally {
    Write-Host "`n`nStopping server..." -ForegroundColor Yellow
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
    Write-Host "Server stopped." -ForegroundColor Green
}
