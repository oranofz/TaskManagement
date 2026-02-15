# Enterprise Task Management System

A production-ready, multi-tenant task management system built with FastAPI, implementing CQRS pattern, domain-driven design, and advanced authentication/authorization.

## Architecture Overview

This system follows a **Modular Monolith** architecture with clear bounded contexts:
- **Auth**: Authentication, MFA, JWT token management
- **Tenant**: Multi-tenancy, organization hierarchy
- **Task**: Task management with CQRS pattern
- **Shared**: Cross-cutting concerns (events, caching, middleware, security)

### Key Features

- ✅ **Multi-tenant architecture** with data isolation
- ✅ **CQRS pattern** for command/query separation
- ✅ **Domain-driven design** with aggregates and events
- ✅ **Advanced authentication**: JWT (RS256), refresh token rotation, MFA support
- ✅ **Authorization**: RBAC + Permission-based + Resource-based
- ✅ **Distributed caching** with Redis
- ✅ **Event-driven architecture** with domain events
- ✅ **Password security**: Argon2id hashing, HaveIBeenPwned integration
- ✅ **Production-ready**: Structured logging, health checks, rate limiting

### Technology Stack

- **Language**: Python 3.13
- **Framework**: FastAPI 0.115+
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Validation**: Pydantic v2
- **Auth**: PyJWT (RS256), passlib (Argon2)
- **Testing**: pytest, pytest-asyncio

## Quick Start

### Prerequisites

- Python 3.13+
- Docker Desktop (running)
- PostgreSQL 16 (via Docker)
- Redis 7 (via Docker)

### Automated Setup & Run (Recommended)

**Single command to setup and start:**

```powershell
.\setup.ps1
```

This script will:
1. ✅ Check Python 3.13+ installation
2. ✅ Install all dependencies from requirements.txt
3. ✅ Start Docker containers (PostgreSQL + Redis)
4. ✅ Generate RSA keys for JWT (if not exist)
5. ✅ Create .env configuration file
6. ✅ Create logs directory
7. ✅ Initialize database (create all tables)
8. ✅ **Automatically start the application**

**The application will be running at:**
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Manual Setup (Alternative)

If you prefer manual control:

### Manual Setup (Alternative)

If you prefer manual control:

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Start infrastructure** (PostgreSQL + Redis):
```bash
docker-compose up -d
```

3. **Generate JWT keys**:
```bash
python generate_keys.py
```

4. **Create `.env` file**:
```bash
Copy-Item .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**:
```bash
python init_db.py
```

6. **Start the application**:
```bash
uvicorn main:app --reload --port 8000
```


## API Documentation

See `/docs` for interactive OpenAPI documentation.

## Security Features

- Password requirements: 12+ chars, uppercase, lowercase, number, special char
- JWT RS256 with refresh token rotation
- RBAC + Permission-based + Resource-based authorization
- Multi-tenant data isolation
- Rate limiting per tenant

## Testing

```bash
pytest --cov=app --cov-report=html
```

## License

Proprietary - All rights reserved

