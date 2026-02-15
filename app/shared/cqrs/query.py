"""Base query interface."""
from abc import ABC
from dataclasses import dataclass


@dataclass
class Query(ABC):
    """Base query class for CQRS pattern."""
    pass

