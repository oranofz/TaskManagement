"""JWT token utilities."""
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional
from uuid import UUID
from jose import jwt, JWTError
from app.config import settings
from loguru import logger


class JWTHandler:
    """JWT token handler for encoding and decoding tokens."""

    @staticmethod
    def create_access_token(
        user_id: UUID,
        email: str,
        tenant_id: UUID,
        roles: list[str],
        permissions: list[str],
        department_id: Optional[UUID] = None
    ) -> str:
        """
        Create access token.

        Args:
            user_id: User ID
            email: User email
            tenant_id: Tenant ID
            roles: User roles
            permissions: User permissions
            department_id: Department ID (optional)

        Returns:
            JWT access token
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "tenant_id": str(tenant_id),
            "roles": roles,
            "permissions": permissions,
            "department_id": str(department_id) if department_id else None,
            "iat": now,
            "exp": expire,
            "type": "access"
        }

        try:
            token = jwt.encode(
                payload,
                settings.jwt_private_key,
                algorithm=settings.jwt_algorithm
            )
            return token
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise

    @staticmethod
    def create_refresh_token(
        user_id: UUID,
        tenant_id: UUID,
        jti: str
    ) -> str:
        """
        Create refresh token.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            jti: JWT ID (unique token identifier)

        Returns:
            JWT refresh token
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        expire = now + timedelta(days=settings.refresh_token_expire_days)

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "jti": jti,
            "iat": now,
            "exp": expire,
            "type": "refresh"
        }

        try:
            token = jwt.encode(
                payload,
                settings.jwt_private_key,
                algorithm=settings.jwt_algorithm
            )
            return token
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token

        Returns:
            Token payload

        Raises:
            JWTError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_public_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            logger.warning(f"Invalid token: {e}")
            raise


jwt_handler = JWTHandler()

