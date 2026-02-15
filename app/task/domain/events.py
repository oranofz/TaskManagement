"""Task domain events."""
from dataclasses import dataclass
from uuid import UUID
from app.shared.events.handler import DomainEvent


@dataclass
class TaskCreated(DomainEvent):
    """Task created event."""
    pass


@dataclass
class TaskUpdated(DomainEvent):
    """Task updated event."""
    pass


@dataclass
class TaskAssigned(DomainEvent):
    """Task assigned event."""
    pass


@dataclass
class TaskStatusChanged(DomainEvent):
    """Task status changed event."""
    pass


@dataclass
class TaskCompleted(DomainEvent):
    """Task completed event."""
    pass


@dataclass
class TaskDeleted(DomainEvent):
    """Task deleted event."""
    pass


@dataclass
class TaskCommentAdded(DomainEvent):
    """Task comment added event."""
    pass

