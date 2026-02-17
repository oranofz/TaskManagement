"""Auth domain models."""
from datetime import datetime, UTC
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from app.shared.database import Base


def get_utc_now():
    """Get current UTC time as timezone-naive datetime (for PostgreSQL TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    """User aggregate root."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    roles = Column(ARRAY(String), nullable=False, default=[])
    permissions = Column(ARRAY(String), nullable=False, default=[])
    department_id = Column(UUID(as_uuid=True), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    last_password_change_at = Column(DateTime, nullable=False, default=get_utc_now)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)
    updated_at = Column(DateTime, nullable=False, default=get_utc_now, onupdate=get_utc_now)


class RefreshToken(Base):
    """Refresh token entity."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    jti = Column(String(255), nullable=False, unique=True)
    parent_token_id = Column(UUID(as_uuid=True), nullable=True)
    family_id = Column(UUID(as_uuid=True), nullable=False)
    device_fingerprint = Column(String(500), nullable=True)
    is_revoked = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)


class PasswordResetToken(Base):
    """Password reset token entity."""

    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    is_used = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)


