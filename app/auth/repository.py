"""Auth repository for data access."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.domain.models import User, RefreshToken
from loguru import logger


class AuthRepository:
    """Repository for auth data access."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        self.session = session

    async def get_user_by_id(self, user_id: UUID, tenant_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str, tenant_id: UUID) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        """Create new user."""
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info(f"User created: {user.id}")
        return user

    async def update_user(self, user: User) -> User:
        """Update user."""
        await self.session.commit()
        await self.session.refresh(user)
        logger.info(f"User updated: {user.id}")
        return user

    async def create_refresh_token(self, refresh_token: RefreshToken) -> RefreshToken:
        """Create refresh token."""
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_refresh_token_by_jti(self, jti: str, tenant_id: UUID) -> Optional[RefreshToken]:
        """Get refresh token by JTI."""
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.jti == jti,
                RefreshToken.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, jti: str, tenant_id: UUID) -> None:
        """Revoke refresh token."""
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.jti == jti,
                RefreshToken.tenant_id == tenant_id
            )
        )
        token = result.scalar_one_or_none()
        if token:
            token.is_revoked = True
            await self.session.commit()
            logger.info(f"Refresh token revoked: {jti}")

    async def revoke_token_family(self, family_id: UUID, tenant_id: UUID) -> None:
        """Revoke entire token family."""
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == family_id,
                RefreshToken.tenant_id == tenant_id
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
        await self.session.commit()
        logger.warning(f"Token family revoked: {family_id}")

