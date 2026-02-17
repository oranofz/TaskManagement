"""Auth commands."""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from app.shared.cqrs.command import Command


@dataclass
class RegisterUserCommand(Command):
    """Register user command."""
    email: str
    username: str
    password: str
    tenant_id: UUID


@dataclass
class LoginCommand(Command):
    """Login command."""
    email: str
    password: str
    tenant_id: UUID
    mfa_code: Optional[str] = None
    device_fingerprint: Optional[str] = None


@dataclass
class RefreshTokenCommand(Command):
    """Refresh token command."""
    refresh_token: str


@dataclass
class LogoutCommand(Command):
    """Logout command."""
    refresh_token: str
    tenant_id: UUID


@dataclass
class EnableMFACommand(Command):
    """Enable MFA command."""
    user_id: UUID
    tenant_id: UUID


@dataclass
class VerifyMFACommand(Command):
    """Verify MFA command."""
    user_id: UUID
    tenant_id: UUID
    code: str


@dataclass
class RequestPasswordResetCommand(Command):
    """Request password reset command."""
    email: str
    tenant_id: UUID


@dataclass
class ResetPasswordCommand(Command):
    """Reset password command."""
    token: str
    new_password: str

