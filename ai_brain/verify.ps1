# AI Brain - Project Verification Script
# Run this to verify the complete project structure

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AI BRAIN - PROJECT STRUCTURE VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "c:\Learning\My Project\Synapsera_RealEstate\ai_brain"
Set-Location $projectRoot

# Check if we're in the right directory
if (-not (Test-Path "main.py")) {
    Write-Host "ERROR: Not in the correct directory!" -ForegroundColor Red
    Write-Host "Please run this script from: $projectRoot" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Current directory: $projectRoot" -ForegroundColor Green
Write-Host ""

# Function to check file existence
function Test-FileExists {
    param([string]$path, [string]$description)
    if (Test-Path $path) {
        Write-Host "  ✓ $description" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ✗ $description - MISSING!" -ForegroundColor Red
        return $false
    }
}

# Check main files
Write-Host "Main Files:" -ForegroundColor Cyan
Test-FileExists "main.py" "main.py"
Test-FileExists "pyproject.toml" "pyproject.toml"
Test-FileExists "docker-compose.yml" "docker-compose.yml"
Test-FileExists "alembic.ini" "alembic.ini"
Test-FileExists "README.md" "README.md"
Test-FileExists ".env.example" ".env.example"
Test-FileExists ".gitignore" ".gitignore"
Write-Host ""

# Check API files
Write-Host "API Layer:" -ForegroundColor Cyan
Test-FileExists "api\project_router.py" "api/project_router.py"
Test-FileExists "api\schemas.py" "api/schemas.py"
Test-FileExists "api\document_router.py" "api/document_router.py (placeholder)"
Test-FileExists "api\chat_router.py" "api/chat_router.py (placeholder)"
Write-Host ""

# Check Config files
Write-Host "Configuration:" -ForegroundColor Cyan
Test-FileExists "config\settings.py" "config/settings.py"
Write-Host ""

# Check Database files
Write-Host "Database Layer:" -ForegroundColor Cyan
Test-FileExists "db\session.py" "db/session.py"
Test-FileExists "db\models.py" "db/models.py"
Test-FileExists "db\repositories\project_repository.py" "db/repositories/project_repository.py"
Write-Host ""

# Check Alembic
Write-Host "Migrations (Alembic):" -ForegroundColor Cyan
Test-FileExists "alembic\env.py" "alembic/env.py"
Test-FileExists "alembic\script.py.mako" "alembic/script.py.mako"
Test-FileExists "alembic\versions\001_create_projects_table.py" "alembic/versions/001_create_projects_table.py"
Write-Host ""

# Check other directories
Write-Host "Other Modules:" -ForegroundColor Cyan
Test-FileExists "ingestion\pdf_extractor.py" "ingestion/pdf_extractor.py (placeholder)"
Test-FileExists "rag\retriever.py" "rag/retriever.py (placeholder)"
Test-FileExists "services\faiss_service.py" "services/faiss_service.py (placeholder)"
Test-FileExists "ui\index.html" "ui/index.html (placeholder)"
Test-FileExists "utils\helpers.py" "utils/helpers.py (placeholder)"
Write-Host ""

# Check Docker status
Write-Host "Docker Status:" -ForegroundColor Cyan
try {
    $containers = docker ps --filter "name=ai_brain" --format "{{.Names}}" 2>$null
    if ($containers) {
        foreach ($container in $containers) {
            Write-Host "  ✓ Container running: $container" -ForegroundColor Green
        }
    } else {
        Write-Host "  ! No containers running (run 'docker-compose up -d')" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ! Docker not available or not running" -ForegroundColor Yellow
}
Write-Host ""

# Check Python dependencies
Write-Host "Python Environment:" -ForegroundColor Cyan
try {
    $python = python --version 2>&1
    Write-Host "  ✓ $python" -ForegroundColor Green
    
    $packages = @("fastapi", "sqlalchemy", "alembic", "uvicorn", "pydantic")
    foreach ($pkg in $packages) {
        $installed = pip show $pkg 2>$null
        if ($installed) {
            $version = ($installed | Select-String "Version:" | Out-String).Split(":")[1].Trim()
            Write-Host "  ✓ $pkg $version" -ForegroundColor Green
        } else {
            Write-Host "  ✗ $pkg - NOT INSTALLED" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "  ! Python not available in PATH" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VERIFICATION COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Install dependencies: poetry install (or pip install)" -ForegroundColor White
Write-Host "  2. Start database: docker-compose up -d" -ForegroundColor White
Write-Host "  3. Run migrations: alembic upgrade head" -ForegroundColor White
Write-Host "  4. Start API: uvicorn main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Or use the automated setup:" -ForegroundColor Yellow
Write-Host "  .\setup.bat" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  - README.md - General overview" -ForegroundColor White
Write-Host "  - SPRINT1_COMPLETE.md - Detailed setup guide" -ForegroundColor White
Write-Host ""
