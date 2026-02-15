"""Authentication middleware."""
from typing import Callable, Optional
from uuid import UUID
from fastapi import Request, Response, HTTPException, status
from jose import JWTError
from loguru import logger
from app.shared.security.jwt import jwt_handler
from app.shared.context import set_user_id, set_tenant_id, get_correlation_id


async def auth_middleware(request: Request, call_next: Callable) -> Response:
    """
    Authentication middleware.
    Validates JWT token and sets user context.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response
    """
    # Skip authentication for public endpoints
    public_paths = [
        "/",
        "/health",
        "/ready",
        "/live",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/favicon.ico",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh"
    ]

    # Public path prefixes (for docs assets, static files, well-known URIs)
    public_prefixes = [
        "/.well-known/",  # Browser auto-requests (security.txt, etc.)
        "/static/",       # Static files
    ]

    path = request.url.path

    # Check exact match
    if path in public_paths:
        return await call_next(request)

    # Check prefix match for browser auto-requests and static assets
    if any(path.startswith(prefix) for prefix in public_prefixes):
        return await call_next(request)

    # Get authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning(
            "Missing or invalid authorization header",
            correlation_id=get_correlation_id(),
            path=request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt_handler.decode_token(token)

        # Set user context
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        set_user_id(user_id)
        set_tenant_id(tenant_id)

        # Store user info in request state for route handlers
        request.state.user_id = user_id
        request.state.tenant_id = tenant_id
        request.state.roles = payload.get("roles", [])
        request.state.permissions = payload.get("permissions", [])
        request.state.department_id = UUID(payload["department_id"]) if payload.get("department_id") else None

        logger.debug(
            "User authenticated",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            correlation_id=get_correlation_id()
        )

    except JWTError as e:
        logger.warning(
            f"Invalid JWT token: {e}",
            correlation_id=get_correlation_id(),
            path=request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(
            f"Authentication error: {e}",
            correlation_id=get_correlation_id(),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

    response = await call_next(request)
    return response

