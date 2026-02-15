"""Auth schemas (Pydantic models)."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.shared.security.password import password_handler


class RegisterUserRequest(BaseModel):
    """Register user request schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=12)
    tenant_id: UUID

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        is_valid, error = password_handler.validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str
    tenant_id: Optional[UUID] = None  # Optional: can be provided in body or will be resolved from header
    mfa_code: Optional[str] = None
    device_fingerprint: Optional[str] = None


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request schema."""
    refresh_token: str


class EnableMFAResponse(BaseModel):
    """Enable MFA response schema."""
    secret: str
    qr_code_url: str


class VerifyMFARequest(BaseModel):
    """Verify MFA request schema."""
    code: str


class RequestPasswordResetRequest(BaseModel):
    """Request password reset schema."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""
    token: str
    new_password: str = Field(..., min_length=12)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        is_valid, error = password_handler.validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    tenant_id: UUID
    email: str
    username: str
    roles: List[str]
    permissions: List[str]
    department_id: Optional[UUID]
    is_active: bool
    email_verified: bool
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

