"""Task commands."""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.shared.cqrs.command import Command
from app.task.domain.models import TaskStatus, Priority


@dataclass
class CreateTaskCommand(Command):
    """Create task command."""
    tenant_id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    priority: Priority
    assigned_to_user_id: Optional[UUID]
    created_by_user_id: UUID
    due_date: Optional[datetime]
    tags: List[str]
    estimated_hours: Optional[float]


@dataclass
class UpdateTaskCommand(Command):
    """Update task command."""
    task_id: UUID
    tenant_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    tags: Optional[List[str]] = None


@dataclass
class AssignTaskCommand(Command):
    """Assign task command."""
    task_id: UUID
    tenant_id: UUID
    assigned_to_user_id: UUID
    assigned_by_user_id: UUID


@dataclass
class ChangeTaskStatusCommand(Command):
    """Change task status command."""
    task_id: UUID
    tenant_id: UUID
    new_status: TaskStatus
    user_id: UUID
    blocked_reason: Optional[str] = None


@dataclass
class DeleteTaskCommand(Command):
    """Delete task command."""
    task_id: UUID
    tenant_id: UUID
    user_id: UUID


@dataclass
class AddTaskCommentCommand(Command):
    """Add task comment command."""
    task_id: UUID
    tenant_id: UUID
    user_id: UUID
    content: str

