"""Event dispatcher for domain events."""
from typing import Callable, Dict, List, Type
from app.shared.events.handler import DomainEvent
from loguru import logger


class EventDispatcher:
    """Event dispatcher for publishing domain events."""

    def __init__(self) -> None:
        """Initialize event dispatcher."""
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}

    def register_handler(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None]
    ) -> None:
        """
        Register event handler.

        Args:
            event_type: Event type
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.debug(f"Registered event handler for {event_type.__name__}")

    async def dispatch(self, event: DomainEvent) -> None:
        """
        Dispatch event to all registered handlers.

        Args:
            event: Domain event
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        logger.info(
            f"Dispatching event: {event_type.__name__}",
            event_id=str(event.event_id),
            aggregate_id=str(event.aggregate_id),
            tenant_id=str(event.tenant_id)
        )

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Error in event handler for {event_type.__name__}: {e}",
                    event_id=str(event.event_id),
                    exc_info=True
                )


event_dispatcher = EventDispatcher()

