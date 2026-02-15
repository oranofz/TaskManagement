"""Auth queries."""
from dataclasses import dataclass
from uuid import UUID
from app.shared.cqrs.query import Query


@dataclass
class GetUserByIdQuery(Query):
    """Get user by ID query."""
    user_id: UUID
    tenant_id: UUID


@dataclass
class GetUserByEmailQuery(Query):
    """Get user by email query."""
    email: str
    tenant_id: UUID


@dataclass
class GetUserPermissionsQuery(Query):
    """Get user permissions query."""
    user_id: UUID
    tenant_id: UUID

