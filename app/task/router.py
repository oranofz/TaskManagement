"""Task API router."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.task.schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    AssignTaskRequest,
    ChangeTaskStatusRequest,
    AddTaskCommentRequest,
    TaskResponse,
    TaskListResponse,
    CommentResponse,
    TaskStatisticsResponse
)
from app.task.commands import (
    CreateTaskCommand,
    UpdateTaskCommand,
    AssignTaskCommand,
    ChangeTaskStatusCommand,
    DeleteTaskCommand,
    AddTaskCommentCommand
)
from app.task.queries import GetTaskByIdQuery, GetUserTasksQuery, GetTaskStatisticsQuery
from app.task.handlers import (
    CreateTaskHandler,
    UpdateTaskHandler,
    AssignTaskHandler,
    ChangeTaskStatusHandler,
    DeleteTaskHandler,
    AddTaskCommentHandler,
    GetTaskByIdHandler,
    GetUserTasksHandler,
    GetTaskStatisticsHandler
)
from app.task.repository import TaskRepository
from app.task.domain.models import TaskStatus
from app.shared.database import get_db
from app.shared.security.authorization import require_permission, Permission


router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """Get paginated list of tasks."""
    # Authorization check
    require_permission(Permission.TASKS_READ, request.state.permissions)

    repository = TaskRepository(db)
    handler = GetUserTasksHandler(repository)

    query = GetUserTasksQuery(
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        status=status,
        page=page,
        page_size=page_size
    )

    return await handler.handle(query)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Get task by ID."""
    # Authorization check
    require_permission(Permission.TASKS_READ, request.state.permissions)

    repository = TaskRepository(db)
    handler = GetTaskByIdHandler(repository)

    query = GetTaskByIdQuery(
        task_id=task_id,
        tenant_id=request.state.tenant_id
    )

    return await handler.handle(query)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_request: CreateTaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Create a new task."""
    # Authorization check
    require_permission(Permission.TASKS_CREATE, request.state.permissions)

    repository = TaskRepository(db)
    handler = CreateTaskHandler(repository)

    command = CreateTaskCommand(
        tenant_id=request.state.tenant_id,
        project_id=task_request.project_id,
        title=task_request.title,
        description=task_request.description,
        priority=task_request.priority,
        assigned_to_user_id=task_request.assigned_to_user_id,
        created_by_user_id=request.state.user_id,
        due_date=task_request.due_date,
        tags=task_request.tags,
        estimated_hours=task_request.estimated_hours
    )

    return await handler.handle(command)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_request: UpdateTaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Update a task."""
    # Authorization check
    require_permission(Permission.TASKS_UPDATE, request.state.permissions)

    repository = TaskRepository(db)
    handler = UpdateTaskHandler(repository)

    command = UpdateTaskCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        title=task_request.title,
        description=task_request.description,
        priority=task_request.priority,
        due_date=task_request.due_date,
        estimated_hours=task_request.estimated_hours,
        actual_hours=task_request.actual_hours,
        tags=task_request.tags
    )

    return await handler.handle(command)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a task (soft delete)."""
    # Authorization check
    require_permission(Permission.TASKS_DELETE, request.state.permissions)

    repository = TaskRepository(db)
    handler = DeleteTaskHandler(repository)

    command = DeleteTaskCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id
    )

    await handler.handle(command)


@router.patch("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: UUID,
    assign_request: AssignTaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Assign task to a user."""
    # Authorization check
    require_permission(Permission.TASKS_ASSIGN, request.state.permissions)

    repository = TaskRepository(db)
    handler = AssignTaskHandler(repository)

    command = AssignTaskCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        assigned_to_user_id=assign_request.assigned_to_user_id,
        assigned_by_user_id=request.state.user_id
    )

    return await handler.handle(command)


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def change_task_status(
    task_id: UUID,
    status_request: ChangeTaskStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """Change task status."""
    # Authorization check
    require_permission(Permission.TASKS_UPDATE, request.state.permissions)

    repository = TaskRepository(db)
    handler = ChangeTaskStatusHandler(repository)

    command = ChangeTaskStatusCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        new_status=status_request.status,
        user_id=request.state.user_id,
        blocked_reason=status_request.blocked_reason
    )

    return await handler.handle(command)


@router.post("/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_task_comment(
    task_id: UUID,
    comment_request: AddTaskCommentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> CommentResponse:
    """Add a comment to a task."""
    # Authorization check
    require_permission(Permission.TASKS_READ, request.state.permissions)

    repository = TaskRepository(db)
    handler = AddTaskCommentHandler(repository)

    command = AddTaskCommentCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        content=comment_request.content
    )

    return await handler.handle(command)


@router.get("/reports/statistics", response_model=TaskStatisticsResponse)
async def get_task_statistics(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TaskStatisticsResponse:
    """Get task statistics."""
    # Authorization check
    require_permission(Permission.REPORTS_VIEW, request.state.permissions)

    repository = TaskRepository(db)
    handler = GetTaskStatisticsHandler(repository)

    query = GetTaskStatisticsQuery(tenant_id=request.state.tenant_id)

    return await handler.handle(query)

