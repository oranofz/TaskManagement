"""Request context management using context variables."""
from contextvars import ContextVar
from typing import Optional
from uuid import UUID


tenant_id_context: ContextVar[Optional[UUID]] = ContextVar("tenant_id", default=None)
user_id_context: ContextVar[Optional[UUID]] = ContextVar("user_id", default=None)
correlation_id_context: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_tenant_id() -> Optional[UUID]:
    """Get current tenant ID from context."""
    return tenant_id_context.get()


def set_tenant_id(tenant_id: UUID) -> None:
    """Set tenant ID in context."""
    tenant_id_context.set(tenant_id)


def get_user_id() -> Optional[UUID]:
    """Get current user ID from context."""
    return user_id_context.get()


def set_user_id(user_id: UUID) -> None:
    """Set user ID in context."""
    user_id_context.set(user_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_context.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_context.set(correlation_id)

