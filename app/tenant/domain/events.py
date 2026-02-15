"""Tenant domain events."""
from dataclasses import dataclass
from uuid import UUID
from app.shared.events.handler import DomainEvent


@dataclass
class TenantCreated(DomainEvent):
    """Tenant created event."""
    pass


@dataclass
class TenantSettingsUpdated(DomainEvent):
    """Tenant settings updated event."""
    pass


@dataclass
class TenantDeactivated(DomainEvent):
    """Tenant deactivated event."""
    pass

