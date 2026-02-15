"""Auth API router."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.auth.schemas import (
    RegisterUserRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    UserResponse
)
from app.auth.commands import RegisterUserCommand, LoginCommand, RefreshTokenCommand, LogoutCommand
from app.auth.handlers import RegisterUserHandler, LoginHandler, RefreshTokenHandler
from app.auth.repository import AuthRepository
from app.shared.database import get_db


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterUserRequest,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new user.

    Returns the created user details.

    Note: For multi-tenant systems, tenant_id should be provided in the request body
    during registration. In production, you may want to validate the tenant exists
    or use a different tenant resolution strategy (subdomain, header, etc.).
    """
    repository = AuthRepository(db)
    handler = RegisterUserHandler(repository)

    command = RegisterUserCommand(
        email=request.email,
        username=request.username,
        password=request.password,
        tenant_id=request.tenant_id
    )

    result = await handler.handle(command)
    return result


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Login user and get access token.

    Returns JWT access token and refresh token for authentication.

    Tenant resolution strategy (in order of precedence):
    1. tenant_id in request body (if provided)
    2. X-Tenant-ID header

    In production, tenant_id is required.
    """
    from uuid import UUID
    from app.shared.context import get_tenant_id
    from app.config import settings

    repository = AuthRepository(db)
    handler = LoginHandler(repository)

    # Determine tenant_id using multiple strategies
    tenant_id = None

    # Option 1: Check if LoginRequest has tenant_id (requires schema update)
    if hasattr(request, 'tenant_id') and request.tenant_id:
        tenant_id = request.tenant_id

    # Option 2: Try to get from context (set by tenant_resolver_middleware from X-Tenant-ID header)
    if not tenant_id:
        tenant_id = get_tenant_id()

    # In production, tenant_id is required
    if not tenant_id:
        if settings.environment == "production":
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant ID is required. Provide either tenant_id in request body or X-Tenant-ID header."
            )
        else:
            # Only for development/testing - use default tenant
            tenant_id = UUID("00000000-0000-0000-0000-000000000001")
            logger.warning(f"Using default tenant_id for login in {settings.environment}: {request.email}")

    command = LoginCommand(
        email=request.email,
        password=request.password,
        tenant_id=tenant_id,
        mfa_code=request.mfa_code,
        device_fingerprint=request.device_fingerprint
    )

    result = await handler.handle(command)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Refresh access token using a valid refresh token.

    Returns new access token and refresh token pair.
    Old refresh token is automatically revoked.
    """
    repository = AuthRepository(db)
    handler = RefreshTokenHandler(repository)

    command = RefreshTokenCommand(refresh_token=request.refresh_token)

    result = await handler.handle(command)
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Logout user and revoke refresh token."""
    from app.shared.context import get_tenant_id
    from app.auth.handlers import LogoutHandler

    repository = AuthRepository(db)
    handler = LogoutHandler(repository)

    # Get tenant_id from context (set by tenant_resolver_middleware)
    tenant_id = get_tenant_id()
    if not tenant_id:
        from uuid import UUID
        tenant_id = UUID("00000000-0000-0000-0000-000000000001")
        logger.warning(f"Using default tenant_id for logout")

    command = LogoutCommand(
        refresh_token=request.refresh_token,
        tenant_id=tenant_id
    )

    await handler.handle(command)


