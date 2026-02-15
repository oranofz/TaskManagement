"""Auth domain events."""
from dataclasses import dataclass
from uuid import UUID
from app.shared.events.handler import DomainEvent


@dataclass
class UserRegistered(DomainEvent):
    """User registered event."""
    pass


@dataclass
class UserLoggedIn(DomainEvent):
    """User logged in event."""
    pass


@dataclass
class PasswordChanged(DomainEvent):
    """Password changed event."""
    pass


@dataclass
class MFAEnabled(DomainEvent):
    """MFA enabled event."""
    pass


@dataclass
class PermissionsChanged(DomainEvent):
    """Permissions changed event."""
    pass


@dataclass
class RoleAssigned(DomainEvent):
    """Role assigned event."""
    pass

