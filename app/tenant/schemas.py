"""Tenant schemas (Pydantic models)."""
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class CreateTenantRequest(BaseModel):
    """Create tenant request schema."""
    name: str = Field(..., min_length=1, max_length=255)
    subdomain: str = Field(..., min_length=1, max_length=100)
    subscription_plan: str = Field(default="BASIC")
    max_users: int = Field(default=10, ge=1)
    settings: Dict[str, Any] = {}


class UpdateTenantRequest(BaseModel):
    """Update tenant request schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subscription_plan: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=1)
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Tenant response schema."""
    id: UUID
    name: str
    subdomain: str
    subscription_plan: str
    max_users: int
    is_active: bool
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

