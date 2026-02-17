"""Auth API router."""
from typing import Any, Dict
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.auth.schemas import (
    RegisterUserRequest,
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    VerifyMFARequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest
)
from app.auth.commands import (
    RegisterUserCommand,
    LoginCommand,
    RefreshTokenCommand,
    LogoutCommand,
    EnableMFACommand,
    VerifyMFACommand,
    RequestPasswordResetCommand,
    ResetPasswordCommand
)
from app.auth.handlers import (
    RegisterUserHandler,
    LoginHandler,
    RefreshTokenHandler,
    EnableMFAHandler,
    VerifyMFAHandler,
    RequestPasswordResetHandler,
    ResetPasswordHandler
)
from app.auth.repository import AuthRepository
from app.shared.database import get_db
from app.shared.response import create_success_response


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterUserRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
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
    return create_success_response(result.model_dump()).model_dump()


@router.post("/login", response_model=Dict[str, Any])
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
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
    return create_success_response(result.model_dump()).model_dump()


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Refresh access token using a valid refresh token.

    Returns new access token and refresh token pair.
    Old refresh token is automatically revoked.
    """
    repository = AuthRepository(db)
    handler = RefreshTokenHandler(repository)

    command = RefreshTokenCommand(refresh_token=request.refresh_token)

    result = await handler.handle(command)
    return create_success_response(result.model_dump()).model_dump()


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


@router.post("/mfa/enable", response_model=Dict[str, Any])
async def enable_mfa(
    request_obj: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Enable TOTP-based MFA for the current user.

    Returns the TOTP secret and a provisioning URL for QR code generation.
    User must verify the MFA code using /mfa/verify to complete setup.
    """
    from app.shared.context import get_user_id, get_tenant_id

    user_id = get_user_id()
    tenant_id = get_tenant_id()

    if not user_id or not tenant_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    repository = AuthRepository(db)
    handler = EnableMFAHandler(repository)

    command = EnableMFACommand(
        user_id=user_id,
        tenant_id=tenant_id
    )

    result = await handler.handle(command)
    return create_success_response(result).model_dump()


@router.post("/mfa/verify", response_model=Dict[str, Any])
async def verify_mfa(
    request: VerifyMFARequest,
    request_obj: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Verify MFA setup with a TOTP code.

    Completes MFA setup by verifying the user can generate valid codes.
    """
    from app.shared.context import get_user_id, get_tenant_id

    user_id = get_user_id()
    tenant_id = get_tenant_id()

    if not user_id or not tenant_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    repository = AuthRepository(db)
    handler = VerifyMFAHandler(repository)

    command = VerifyMFACommand(
        user_id=user_id,
        tenant_id=tenant_id,
        code=request.code
    )

    result = await handler.handle(command)
    return create_success_response(result).model_dump()


@router.post("/password/reset-request", response_model=Dict[str, Any])
async def request_password_reset(
    request: RequestPasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Initiate password reset flow.

    Sends a password reset link to the user's email (if it exists).
    Always returns success to prevent user enumeration.
    """
    from app.shared.context import get_tenant_id
    from uuid import UUID

    tenant_id = get_tenant_id()
    if not tenant_id:
        tenant_id = UUID("00000000-0000-0000-0000-000000000001")

    repository = AuthRepository(db)
    handler = RequestPasswordResetHandler(repository)

    command = RequestPasswordResetCommand(
        email=request.email,
        tenant_id=tenant_id
    )

    result = await handler.handle(command)
    return create_success_response(result).model_dump()


@router.post("/password/reset", response_model=Dict[str, Any])
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Complete password reset with token.

    Validates the reset token and sets the new password.
    """
    repository = AuthRepository(db)
    handler = ResetPasswordHandler(repository)

    command = ResetPasswordCommand(
        token=request.token,
        new_password=request.new_password
    )

    result = await handler.handle(command)
    return create_success_response(result).model_dump()
