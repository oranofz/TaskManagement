"""Mediator pattern implementation for CQRS."""
from typing import Any, Callable, Dict, Type, TypeVar
from app.shared.cqrs.command import Command
from app.shared.cqrs.query import Query
from loguru import logger


TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)


class Mediator:
    """Mediator for dispatching commands and queries to handlers."""

    def __init__(self) -> None:
        """Initialize mediator."""
        self._command_handlers: Dict[Type[Command], Callable] = {}
        self._query_handlers: Dict[Type[Query], Callable] = {}

    def register_command_handler(
        self,
        command_type: Type[TCommand],
        handler: Callable[[TCommand], Any]
    ) -> None:
        """
        Register command handler.

        Args:
            command_type: Command type
            handler: Handler function
        """
        self._command_handlers[command_type] = handler
        logger.debug(f"Registered command handler for {command_type.__name__}")

    def register_query_handler(
        self,
        query_type: Type[TQuery],
        handler: Callable[[TQuery], Any]
    ) -> None:
        """
        Register query handler.

        Args:
            query_type: Query type
            handler: Handler function
        """
        self._query_handlers[query_type] = handler
        logger.debug(f"Registered query handler for {query_type.__name__}")

    async def send(self, command: TCommand) -> Any:
        """
        Send command to handler.

        Args:
            command: Command instance

        Returns:
            Handler result

        Raises:
            ValueError: If no handler registered
        """
        command_type = type(command)
        handler = self._command_handlers.get(command_type)

        if not handler:
            raise ValueError(f"No handler registered for command {command_type.__name__}")

        logger.info(f"Dispatching command: {command_type.__name__}")
        result = await handler(command)
        logger.info(f"Command {command_type.__name__} completed")

        return result

    async def query(self, query: TQuery) -> Any:
        """
        Send query to handler.

        Args:
            query: Query instance

        Returns:
            Handler result

        Raises:
            ValueError: If no handler registered
        """
        query_type = type(query)
        handler = self._query_handlers.get(query_type)

        if not handler:
            raise ValueError(f"No handler registered for query {query_type.__name__}")

        logger.debug(f"Dispatching query: {query_type.__name__}")
        result = await handler(query)
        logger.debug(f"Query {query_type.__name__} completed")

        return result


mediator = Mediator()

