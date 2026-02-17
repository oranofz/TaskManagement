"""Task API router."""
from typing import Optional, Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.task.schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    AssignTaskRequest,
    ChangeTaskStatusRequest,
    AddTaskCommentRequest
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
from app.shared.security.authorization import require_permission, Permission, check_resource_access
from app.shared.cqrs.mediator import mediator
from app.shared.response import (
    create_success_response,
    create_paginated_response
)
from fastapi import HTTPException


router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


def setup_task_mediator(db: AsyncSession) -> None:
    """Register task handlers with mediator for current request."""
    repository = TaskRepository(db)

    # Register command handlers
    mediator.register_command_handler(
        CreateTaskCommand,
        lambda cmd: CreateTaskHandler(repository).handle(cmd)
    )
    mediator.register_command_handler(
        UpdateTaskCommand,
        lambda cmd: UpdateTaskHandler(repository).handle(cmd)
    )
    mediator.register_command_handler(
        AssignTaskCommand,
        lambda cmd: AssignTaskHandler(repository).handle(cmd)
    )
    mediator.register_command_handler(
        ChangeTaskStatusCommand,
        lambda cmd: ChangeTaskStatusHandler(repository).handle(cmd)
    )
    mediator.register_command_handler(
        DeleteTaskCommand,
        lambda cmd: DeleteTaskHandler(repository).handle(cmd)
    )
    mediator.register_command_handler(
        AddTaskCommentCommand,
        lambda cmd: AddTaskCommentHandler(repository).handle(cmd)
    )

    # Register query handlers
    mediator.register_query_handler(
        GetTaskByIdQuery,
        lambda q: GetTaskByIdHandler(repository).handle(q)
    )
    mediator.register_query_handler(
        GetUserTasksQuery,
        lambda q: GetUserTasksHandler(repository).handle(q)
    )
    mediator.register_query_handler(
        GetTaskStatisticsQuery,
        lambda q: GetTaskStatisticsHandler(repository).handle(q)
    )


@router.get("", response_model=Dict[str, Any])
async def get_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get paginated list of tasks with filtering and sorting."""
    # Authorization check
    require_permission(Permission.TASKS_READ, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    query = GetUserTasksQuery(
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    result = await mediator.query(query)

    # Wrap in StandardResponse with pagination
    return create_paginated_response(
        items=[task.model_dump() for task in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total
    ).model_dump()


@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task(
    task_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get task by ID."""
    # Authorization check
    require_permission(Permission.TASKS_READ, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    query = GetTaskByIdQuery(
        task_id=task_id,
        tenant_id=request.state.tenant_id
    )

    task = await mediator.query(query)

    # Resource-based authorization check
    has_access = check_resource_access(
        user_id=request.state.user_id,
        user_roles=request.state.roles,
        user_permissions=request.state.permissions,
        resource_owner_id=task.created_by_user_id,
        resource_assigned_to_id=task.assigned_to_user_id,
        user_department_id=getattr(request.state, 'department_id', None),
        resource_department_id=None  # Task doesn't have direct department, check through project
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )

    return create_success_response(task.model_dump()).model_dump()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_task(
    task_request: CreateTaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new task."""
    # Authorization check
    require_permission(Permission.TASKS_CREATE, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

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

    result = await mediator.send(command)
    return create_success_response(result.model_dump()).model_dump()


@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task(
    task_id: UUID,
    task_request: UpdateTaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update a task."""
    # Authorization check
    require_permission(Permission.TASKS_UPDATE, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    # First get the task to check resource access
    query = GetTaskByIdQuery(
        task_id=task_id,
        tenant_id=request.state.tenant_id
    )
    existing_task = await mediator.query(query)

    # Resource-based authorization check
    has_access = check_resource_access(
        user_id=request.state.user_id,
        user_roles=request.state.roles,
        user_permissions=request.state.permissions,
        resource_owner_id=existing_task.created_by_user_id,
        resource_assigned_to_id=existing_task.assigned_to_user_id,
        user_department_id=getattr(request.state, 'department_id', None),
        resource_department_id=None
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to update this task"
        )

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

    result = await mediator.send(command)
    return create_success_response(result.model_dump()).model_dump()


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a task (soft delete)."""
    # Authorization check
    require_permission(Permission.TASKS_DELETE, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    # First get the task to check resource access
    query = GetTaskByIdQuery(
        task_id=task_id,
        tenant_id=request.state.tenant_id
    )
    existing_task = await mediator.query(query)

    # Resource-based authorization check
    has_access = check_resource_access(
        user_id=request.state.user_id,
        user_roles=request.state.roles,
        user_permissions=request.state.permissions,
        resource_owner_id=existing_task.created_by_user_id,
        resource_assigned_to_id=existing_task.assigned_to_user_id,
        user_department_id=getattr(request.state, 'department_id', None),
        resource_department_id=None
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to delete this task"
        )

    command = DeleteTaskCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id
    )

    await mediator.send(command)


@router.patch("/{task_id}/assign", response_model=Dict[str, Any])
async def assign_task(
    task_id: UUID,
    assign_request: AssignTaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Assign task to a user."""
    # Authorization check
    require_permission(Permission.TASKS_ASSIGN, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    command = AssignTaskCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        assigned_to_user_id=assign_request.assigned_to_user_id,
        assigned_by_user_id=request.state.user_id
    )

    result = await mediator.send(command)
    return create_success_response(result.model_dump()).model_dump()


@router.patch("/{task_id}/status", response_model=Dict[str, Any])
async def change_task_status(
    task_id: UUID,
    status_request: ChangeTaskStatusRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Change task status."""
    # Authorization check
    require_permission(Permission.TASKS_UPDATE, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    command = ChangeTaskStatusCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        new_status=status_request.status,
        user_id=request.state.user_id,
        blocked_reason=status_request.blocked_reason
    )

    result = await mediator.send(command)
    return create_success_response(result.model_dump()).model_dump()


@router.post("/{task_id}/comments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def add_task_comment(
    task_id: UUID,
    comment_request: AddTaskCommentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Add a comment to a task."""
    # Authorization check
    require_permission(Permission.TASKS_READ, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    command = AddTaskCommentCommand(
        task_id=task_id,
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        content=comment_request.content
    )

    result = await mediator.send(command)
    return create_success_response(result.model_dump()).model_dump()


@router.get("/reports/statistics", response_model=Dict[str, Any])
async def get_task_statistics(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get task statistics."""
    # Authorization check
    require_permission(Permission.REPORTS_VIEW, request.state.permissions)

    # Setup mediator with handlers
    setup_task_mediator(db)

    query = GetTaskStatisticsQuery(tenant_id=request.state.tenant_id)

    result = await mediator.query(query)
    return create_success_response(result.model_dump()).model_dump()

