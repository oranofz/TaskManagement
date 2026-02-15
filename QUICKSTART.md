# Quick Start Guide

## Prerequisites Checklist

- [ ] Python 3.13+ installed
- [ ] Docker Desktop installed and running
- [ ] Git installed (optional)

## Installation Steps

### 1. Navigate to project directory
```powershell
cd C:\Users\oran-\PycharmProjects\TaskManagement
```

### 2. Run automated setup (PowerShell)
```powershell
.\setup.ps1
```

This script will:
- Check Python version
- Install all Python dependencies
- Start Docker containers (PostgreSQL & Redis)
- Generate JWT RSA keys
- Create .env file from template
- Create logs directory

### 3. Start the application
```powershell
uvicorn main:app --reload --port 8000
```

### 4. Verify installation
Open browser and visit:
- Health Check: http://localhost:8000/health
- API Docs: http://localhost:8000/docs

Expected health check response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-15T10:30:00.000Z",
  "version": "1.0.0",
  "environment": "development",
  "database": "connected",
  "redis": "connected"
}
```

## Manual Setup (Alternative)

If automated setup doesn't work:

### 1. Install dependencies
```powershell
pip install -r requirements.txt
```

### 2. Start infrastructure
```powershell
docker-compose up -d
```

### 3. Generate JWT keys
```powershell
python generate_keys.py
```

### 4. Create .env file
```powershell
Copy-Item .env.example .env
```

### 5. Start application
```powershell
uvicorn main:app --reload --port 8000
```

## Testing the API

### 1. Register a User
```powershell
curl -X POST "http://localhost:8000/api/v1/auth/register" `
  -H "Content-Type: application/json" `
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "SecurePass123!@#",
    "tenant_id": "00000000-0000-0000-0000-000000000001"
  }'
```

### 2. Login
```powershell
curl -X POST "http://localhost:8000/api/v1/auth/login" `
  -H "Content-Type: application/json" `
  -d '{
    "email": "admin@example.com",
    "password": "SecurePass123!@#"
  }'
```

Save the `access_token` from the response.

### 3. Create a Task
```powershell
curl -X POST "http://localhost:8000/api/v1/tasks" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "X-Tenant-ID: 00000000-0000-0000-0000-000000000001" `
  -H "Content-Type: application/json" `
  -d '{
    "title": "First Task",
    "description": "This is my first task",
    "project_id": "00000000-0000-0000-0000-000000000001",
    "priority": "HIGH",
    "tags": ["test"]
  }'
```

### 4. Get Tasks
```powershell
curl -X GET "http://localhost:8000/api/v1/tasks" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "X-Tenant-ID: 00000000-0000-0000-0000-000000000001"
```

## Troubleshooting

### Docker services not starting
```powershell
# Check if Docker Desktop is running
docker ps

# If not, start Docker Desktop and retry
docker-compose up -d
```

### Database connection failed
```powershell
# Check if PostgreSQL is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Restart services
docker-compose restart
```

### Redis connection failed
```powershell
# Check Redis status
docker-compose ps

# View Redis logs
docker-compose logs redis
```

### JWT keys not found
```powershell
# Generate keys manually
python generate_keys.py

# Verify keys exist
Test-Path keys/jwt_private.pem
Test-Path keys/jwt_public.pem
```

### Import errors
```powershell
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Development Commands

### Run tests
```powershell
pytest
```

### Run tests with coverage
```powershell
pytest --cov=app --cov-report=html
```

### View coverage report
```powershell
start htmlcov/index.html
```

### Stop Docker services
```powershell
docker-compose down
```

### Stop and remove volumes
```powershell
docker-compose down -v
```

### View application logs
```powershell
Get-Content logs/app_*.log -Tail 50
```

### Database migrations
```powershell
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Environment Variables

Key environment variables in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/task_management
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-change-in-production
JWT_PRIVATE_KEY_PATH=keys/jwt_private.pem
JWT_PUBLIC_KEY_PATH=keys/jwt_public.pem
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_PER_MINUTE=60
```

## Next Steps

1. Review ARCHITECTURE.md for detailed design
2. Explore /docs for interactive API documentation
3. Run tests to verify functionality
4. Check logs/ directory for application logs
5. Customize .env for your environment
6. Set up database migrations with Alembic

## Support

For issues or questions:
1. Check IMPLEMENTATION_SUMMARY.md for implementation details
2. Review ARCHITECTURE.md for design decisions
3. Check application logs in logs/ directory
4. Verify all services are running with `docker-compose ps`

