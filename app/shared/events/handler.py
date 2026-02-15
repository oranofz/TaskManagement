"""Base domain event."""
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class DomainEvent:
    """Base domain event class."""

    event_id: UUID = field(default_factory=uuid4)
    event_type: str = field(default="")
    aggregate_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = field(default=1)
    payload: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set event type from class name if not provided."""
        if not self.event_type:
            self.event_type = self.__class__.__name__

