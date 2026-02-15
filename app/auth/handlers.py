"""Auth command and query handlers."""
import hashlib
from datetime import timedelta
from uuid import uuid4

import pyotp
from fastapi import HTTPException, status
from loguru import logger

from app.auth.commands import (
    RegisterUserCommand,
    LoginCommand,
    RefreshTokenCommand,
    LogoutCommand
)
from app.auth.domain.events import UserRegistered, UserLoggedIn
from app.auth.domain.models import User, RefreshToken
from app.auth.queries import GetUserByIdQuery
from app.auth.repository import AuthRepository
from app.auth.schemas import TokenResponse, UserResponse
from app.config import settings
from app.shared.database import get_utc_now
from app.shared.events.dispatcher import event_dispatcher
from app.shared.security.authorization import Role, Permission
from app.shared.security.jwt import jwt_handler
from app.shared.security.password import password_handler


class RegisterUserHandler:
    """Handler for user registration."""

    def __init__(self, repository: AuthRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: RegisterUserCommand) -> UserResponse:
        """Handle user registration."""
        # Check if user already exists
        existing_user = await self.repository.get_user_by_email(
            command.email,
            command.tenant_id
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Check if password is compromised
        is_compromised = await password_handler.check_compromised_password(command.password)
        if is_compromised:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This password has been compromised in a data breach. Please choose a different password."
            )

        # Hash password
        password_hash = password_handler.hash_password(command.password)

        # Create user with default role and permissions
        user = User(
            tenant_id=command.tenant_id,
            email=command.email,
            username=command.username,
            password_hash=password_hash,
            roles=[Role.MEMBER],
            permissions=[Permission.TASKS_READ, Permission.TASKS_CREATE],
            is_active=True,
            email_verified=False
        )

        user = await self.repository.create_user(user)

        # Emit event
        event = UserRegistered(
            aggregate_id=user.id,
            tenant_id=user.tenant_id,
            payload={"email": user.email, "username": user.username}
        )
        await event_dispatcher.dispatch(event)

        logger.info("User registered", user_id=str(user.id), tenant_id=str(user.tenant_id))

        return UserResponse.model_validate(user)


class LoginHandler:
    """Handler for user login."""

    def __init__(self, repository: AuthRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: LoginCommand) -> TokenResponse:
        """Handle user login."""
        # Get user
        user = await self.repository.get_user_by_email(command.email, command.tenant_id)

        if not user:
            logger.warning("Login failed: User not found", tenant_id=str(command.tenant_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not user.is_active:
            logger.warning("Login failed: User inactive", user_id=str(user.id), tenant_id=str(user.tenant_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Verify password
        password_valid = password_handler.verify_password(command.password, user.password_hash)

        if not password_valid:
            logger.warning("Login failed: Invalid password", user_id=str(user.id), tenant_id=str(user.tenant_id))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Check MFA if enabled
        if user.mfa_enabled:
            if not command.mfa_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MFA code required"
                )

            totp = pyotp.TOTP(user.mfa_secret)
            if not totp.verify(command.mfa_code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code"
                )

        # Create tokens
        access_token = jwt_handler.create_access_token(
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
            roles=user.roles,
            permissions=user.permissions,
            department_id=user.department_id
        )

        # Create refresh token
        jti = str(uuid4())
        family_id = uuid4()
        refresh_token_str = jwt_handler.create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            jti=jti
        )

        # Store refresh token
        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        refresh_token = RefreshToken(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_hash=token_hash,
            jti=jti,
            family_id=family_id,
            device_fingerprint=command.device_fingerprint,
            expires_at=get_utc_now() + timedelta(days=settings.refresh_token_expire_days)
        )
        await self.repository.create_refresh_token(refresh_token)

        # Update last login
        user.last_login_at = get_utc_now()
        await self.repository.update_user(user)

        # Emit event
        event = UserLoggedIn(
            aggregate_id=user.id,
            tenant_id=user.tenant_id,
            payload={"email": user.email}
        )
        await event_dispatcher.dispatch(event)

        logger.info("User logged in", user_id=str(user.id), tenant_id=str(user.tenant_id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            expires_in=settings.access_token_expire_minutes * 60
        )


class RefreshTokenHandler:
    """Handler for token refresh."""

    def __init__(self, repository: AuthRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: RefreshTokenCommand) -> TokenResponse:
        """Handle token refresh."""
        # Decode refresh token
        try:
            payload = jwt_handler.decode_token(command.refresh_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get stored refresh token
        stored_token = await self.repository.get_refresh_token_by_jti(
            payload["jti"],
            payload["tenant_id"]
        )

        if not stored_token or stored_token.is_revoked:
            # Token reuse detected - revoke entire family
            if stored_token:
                await self.repository.revoke_token_family(
                    stored_token.family_id,
                    stored_token.tenant_id
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Get user
        user = await self.repository.get_user_by_id(
            stored_token.user_id,
            stored_token.tenant_id
        )

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Revoke old refresh token
        await self.repository.revoke_refresh_token(payload["jti"], payload["tenant_id"])

        # Create new tokens
        access_token = jwt_handler.create_access_token(
            user_id=user.id,
            email=user.email,
            tenant_id=user.tenant_id,
            roles=user.roles,
            permissions=user.permissions,
            department_id=user.department_id
        )

        # Create new refresh token
        new_jti = str(uuid4())
        new_refresh_token = jwt_handler.create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            jti=new_jti
        )

        # Store new refresh token
        token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        refresh_token = RefreshToken(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_hash=token_hash,
            jti=new_jti,
            parent_token_id=stored_token.id,
            family_id=stored_token.family_id,
            device_fingerprint=stored_token.device_fingerprint,
            expires_at=get_utc_now() + timedelta(days=settings.refresh_token_expire_days)
        )
        await self.repository.create_refresh_token(refresh_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.access_token_expire_minutes * 60
        )


class GetUserByIdHandler:
    """Handler for get user by ID query."""

    def __init__(self, repository: AuthRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, query: GetUserByIdQuery) -> UserResponse:
        """Handle get user by ID."""
        user = await self.repository.get_user_by_id(query.user_id, query.tenant_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse.model_validate(user)


class LogoutHandler:
    """Handler for user logout."""

    def __init__(self, repository: AuthRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: LogoutCommand) -> None:
        """Handle user logout by revoking refresh token."""
        # Decode refresh token to get jti
        try:
            payload = jwt_handler.decode_token(command.refresh_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Revoke the refresh token
        await self.repository.revoke_refresh_token(payload["jti"], command.tenant_id)

        logger.info("User logged out, token revoked", jti=payload['jti'], tenant_id=str(command.tenant_id))


