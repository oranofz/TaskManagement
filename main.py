"""Main FastAPI application."""
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.config import settings
from app.shared.database import engine
from app.shared.cache.redis_client import redis_client
from app.shared.middleware.error_handler import error_handler_middleware
from app.shared.middleware.logging import logging_middleware
from app.shared.middleware.tenant_resolver import tenant_resolver_middleware
from app.shared.middleware.auth import auth_middleware
from app.shared.middleware.rate_limiter import rate_limit_middleware
from app.auth.router import router as auth_router
from app.task.router import router as task_router


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")

    # Connect to Redis
    try:
        await redis_client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.error("Redis is required for the application to run. Please ensure Redis is running.")
        raise RuntimeError(f"Failed to connect to Redis: {e}")

    # Verify database connection
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Database is required for the application to run. Please ensure PostgreSQL is running.")
        raise RuntimeError(f"Failed to connect to database: {e}")

    # Create database tables (in production, use Alembic migrations)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Disconnect from Redis
    await redis_client.disconnect()

    # Close database connections
    await engine.dispose()

    logger.info("Application shut down successfully")


app = FastAPI(
    title="Enterprise Task Management System",
    description="Multi-tenant task management with advanced authentication and authorization",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "clientId": "swagger-ui",
        "appName": "Enterprise Task Management System",
        "usePkceWithAuthorizationCodeGrant": True
    },
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)


# Configure OpenAPI security scheme
def custom_openapi():
    """Custom OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from the /api/v1/auth/login endpoint"
        },
        "TenantHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Tenant-ID",
            "description": "Your tenant UUID (optional if provided in login)"
        }
    }

    # Apply security globally to all endpoints except auth endpoints
    for path, path_item in openapi_schema["paths"].items():
        # Skip auth endpoints (login, register) and health checks from requiring authentication
        if "/auth/login" in path or "/auth/register" in path or "/health" in path or "/ready" in path or "/live" in path or '/docs' in path or path == "/":
            continue

        for operation in path_item.values():
            if isinstance(operation, dict) and "security" not in operation:
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Tenant-ID", "X-Correlation-ID"]
)


# Add custom middleware (order matters!)
# Correct order: ErrorHandler → Logging → SecurityHeaders → TenantResolver → Auth → RateLimiter
@app.middleware("http")
async def error_handler(request: Request, call_next):
    """Global error handler."""
    return await error_handler_middleware(request, call_next)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Request logging."""
    return await logging_middleware(request, call_next)


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Relaxed CSP for Swagger UI/ReDoc documentation pages
    # In production, consider hosting Swagger UI assets locally and using stricter CSP
    if request.url.path in ["/docs", "/redoc"] or request.url.path.startswith("/openapi"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://cdn.jsdelivr.net; "
            "font-src 'self' data:; "
            "object-src 'none'"
        )
    else:
        # Strict CSP for API endpoints
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'"

    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.middleware("http")
async def tenant_resolver(request: Request, call_next):
    """Tenant resolution."""
    return await tenant_resolver_middleware(request, call_next)


@app.middleware("http")
async def authentication(request: Request, call_next):
    """Authentication."""
    return await auth_middleware(request, call_next)


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    """Rate limiting."""
    return await rate_limit_middleware(request, call_next)




# Include routers
app.include_router(auth_router)
app.include_router(task_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment
    }

    # Check database connection
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    # Check Redis connection
    try:
        if redis_client.redis:
            await redis_client.redis.ping()
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "disconnected"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["redis"] = "disconnected"
        health_status["status"] = "unhealthy"
        logger.error(f"Redis health check failed: {e}")

    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks if app can serve traffic."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        if redis_client.redis:
            await redis_client.redis.ping()
        else:
            return JSONResponse(
                content={"status": "not_ready", "reason": "Redis not connected"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            content={"status": "not_ready", "reason": str(e)},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe - checks if app is alive."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Enterprise Task Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
