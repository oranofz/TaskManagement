# Setup and Run Script for Windows

Write-Host "Enterprise Task Management System - Setup" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Step 1: Check Python version
Write-Host "Step 1: Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(1[3-9]|[2-9][0-9])") {
    Write-Host "✓ Python version OK: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python 3.13+ required. Found: $pythonVersion" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Install dependencies
Write-Host "Step 2: Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Start Docker services
Write-Host "Step 3: Starting Docker services (PostgreSQL & Redis)..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker services started" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to start Docker services" -ForegroundColor Red
    Write-Host "  Make sure Docker Desktop is running" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 4: Wait for services to be ready
Write-Host "Step 4: Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host "✓ Services should be ready" -ForegroundColor Green
Write-Host ""

# Step 5: Generate JWT keys
Write-Host "Step 5: Generating JWT keys..." -ForegroundColor Yellow
if (!(Test-Path "keys/jwt_private.pem")) {
    python generate_keys.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ JWT keys generated" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to generate JWT keys" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ JWT keys already exist" -ForegroundColor Green
}
Write-Host ""

# Step 6: Create .env file if not exists
Write-Host "Step 6: Checking environment configuration..." -ForegroundColor Yellow
if (!(Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env file from .env.example" -ForegroundColor Green
    Write-Host "  Please review and update .env file with your configuration" -ForegroundColor Yellow
} else {
    Write-Host "✓ .env file exists" -ForegroundColor Green
}
Write-Host ""

# Step 7: Create logs directory
Write-Host "Step 7: Creating logs directory..." -ForegroundColor Yellow
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}
Write-Host "✓ Logs directory ready" -ForegroundColor Green
Write-Host ""

# Step 8: Initialize database
Write-Host "Step 8: Initializing database..." -ForegroundColor Yellow
Write-Host "  Creating database tables..." -ForegroundColor Cyan
python init_db.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database initialized successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to initialize database" -ForegroundColor Red
    Write-Host "  Please check that PostgreSQL is running and .env is configured correctly" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

Write-Host "=========================================" -ForegroundColor Green
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Starting the application..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Access the application at:" -ForegroundColor Cyan
Write-Host "  API: http://localhost:8000" -ForegroundColor White
Write-Host "  Interactive Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the application" -ForegroundColor Yellow
Write-Host ""

# Step 9: Start the application
uvicorn main:app --reload --port 8000

