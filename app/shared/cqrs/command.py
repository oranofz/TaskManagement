"""Base command interface."""
from abc import ABC
from dataclasses import dataclass


@dataclass
class Command(ABC):
    """Base command class for CQRS pattern."""
    pass

