"""Task queries."""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from app.shared.cqrs.query import Query
from app.task.domain.models import TaskStatus


@dataclass
class GetTaskByIdQuery(Query):
    """Get task by ID query."""
    task_id: UUID
    tenant_id: UUID


@dataclass
class GetUserTasksQuery(Query):
    """Get user tasks query."""
    tenant_id: UUID
    user_id: Optional[UUID] = None
    status: Optional[TaskStatus] = None
    page: int = 1
    page_size: int = 20


@dataclass
class GetTaskStatisticsQuery(Query):
    """Get task statistics query."""
    tenant_id: UUID

