"""Auth domain events."""
from dataclasses import dataclass
from app.shared.events.handler import DomainEvent


@dataclass
class UserRegistered(DomainEvent):
    """User registered event."""
    pass


@dataclass
class UserLoggedIn(DomainEvent):
    """User logged in event."""
    pass

