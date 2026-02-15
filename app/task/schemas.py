"""Task schemas (Pydantic models)."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.task.domain.models import TaskStatus, Priority


class CreateTaskRequest(BaseModel):
    """Create task request schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    project_id: UUID
    priority: Priority = Priority.MEDIUM
    assigned_to_user_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    tags: List[str] = []
    estimated_hours: Optional[float] = Field(None, ge=0)

    @field_validator('due_date')
    @classmethod
    def strip_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Strip timezone info to ensure compatibility with TIMESTAMP WITHOUT TIME ZONE."""
        if v is not None and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class UpdateTaskRequest(BaseModel):
    """Update task request schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[Priority] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0)
    actual_hours: Optional[float] = Field(None, ge=0)
    tags: Optional[List[str]] = None

    @field_validator('due_date')
    @classmethod
    def strip_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Strip timezone info to ensure compatibility with TIMESTAMP WITHOUT TIME ZONE."""
        if v is not None and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class AssignTaskRequest(BaseModel):
    """Assign task request schema."""
    assigned_to_user_id: UUID


class ChangeTaskStatusRequest(BaseModel):
    """Change task status request schema."""
    status: TaskStatus
    blocked_reason: Optional[str] = None


class AddTaskCommentRequest(BaseModel):
    """Add task comment request schema."""
    content: str = Field(..., min_length=1, max_length=5000)


class TaskResponse(BaseModel):
    """Task response schema."""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: Priority
    assigned_to_user_id: Optional[UUID]
    created_by_user_id: UUID
    watchers: List[UUID]
    tags: List[str]
    due_date: Optional[datetime]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Task list response schema."""
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int


class CommentResponse(BaseModel):
    """Comment response schema."""
    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskStatisticsResponse(BaseModel):
    """Task statistics response schema."""
    total_tasks: int
    tasks_by_status: dict
    tasks_by_priority: dict
    overdue_tasks: int
    completed_this_month: int

