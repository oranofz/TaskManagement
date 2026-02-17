"""Task command and query handlers."""
from app.task.commands import (
    CreateTaskCommand,
    UpdateTaskCommand,
    AssignTaskCommand,
    ChangeTaskStatusCommand,
    DeleteTaskCommand,
    AddTaskCommentCommand
)
from app.task.queries import GetTaskByIdQuery, GetUserTasksQuery, GetTaskStatisticsQuery
from app.task.repository import TaskRepository
from app.task.domain.models import Task, Comment, AuditLogEntry
from app.task.domain.aggregates import TaskAggregate
from app.task.domain.events import (
    TaskCreated,
    TaskUpdated,
    TaskAssigned,
    TaskStatusChanged,
    TaskDeleted,
    TaskCommentAdded
)
from app.task.schemas import TaskResponse, TaskListResponse, CommentResponse, TaskStatisticsResponse
from app.shared.events.dispatcher import event_dispatcher
from app.shared.cache.redis_client import redis_client
from app.shared.cache.decorators import cached
from fastapi import HTTPException, status
from loguru import logger


class CreateTaskHandler:
    """Handler for task creation."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: CreateTaskCommand) -> TaskResponse:
        """Handle task creation."""
        task = Task(
            tenant_id=command.tenant_id,
            project_id=command.project_id,
            title=command.title,
            description=command.description,
            priority=command.priority,
            assigned_to_user_id=command.assigned_to_user_id,
            created_by_user_id=command.created_by_user_id,
            due_date=command.due_date,
            tags=command.tags,
            estimated_hours=command.estimated_hours
        )

        task = await self.repository.create_task(task)

        # Emit event
        event = TaskCreated(
            aggregate_id=task.id,
            tenant_id=task.tenant_id,
            payload={
                "title": task.title,
                "project_id": str(task.project_id),
                "created_by": str(task.created_by_user_id)
            }
        )
        await event_dispatcher.dispatch(event)

        # Invalidate cache
        await redis_client.delete_pattern(f"tenant:{command.tenant_id}:*:tasks:*")

        logger.info(f"Task created: {task.id}")

        return TaskResponse.model_validate(task)


class UpdateTaskHandler:
    """Handler for task update."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: UpdateTaskCommand) -> TaskResponse:
        """Handle task update."""
        task = await self.repository.get_task_by_id(command.task_id, command.tenant_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Use aggregate to update
        aggregate = TaskAggregate(task)
        aggregate.update_details(
            title=command.title,
            description=command.description,
            priority=command.priority,
            due_date=command.due_date,
            estimated_hours=command.estimated_hours
        )

        if command.actual_hours is not None:
            task.actual_hours = command.actual_hours

        if command.tags is not None:
            task.tags = command.tags

        task = await self.repository.update_task(task)

        # Emit event
        event = TaskUpdated(
            aggregate_id=task.id,
            tenant_id=task.tenant_id,
            payload={"task_id": str(task.id)}
        )
        await event_dispatcher.dispatch(event)

        # Invalidate cache
        await redis_client.delete_pattern(f"tenant:{command.tenant_id}:*:tasks:*")

        return TaskResponse.model_validate(task)


class AssignTaskHandler:
    """Handler for task assignment."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: AssignTaskCommand) -> TaskResponse:
        """Handle task assignment."""
        task = await self.repository.get_task_by_id(command.task_id, command.tenant_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Use aggregate to assign
        aggregate = TaskAggregate(task)
        aggregate.assign_to(command.assigned_to_user_id)

        task = await self.repository.update_task(task)

        # Emit event
        event = TaskAssigned(
            aggregate_id=task.id,
            tenant_id=task.tenant_id,
            payload={
                "task_id": str(task.id),
                "assigned_to": str(command.assigned_to_user_id),
                "assigned_by": str(command.assigned_by_user_id)
            }
        )
        await event_dispatcher.dispatch(event)

        # Invalidate cache
        await redis_client.delete_pattern(f"tenant:{command.tenant_id}:*:tasks:*")

        return TaskResponse.model_validate(task)


class ChangeTaskStatusHandler:
    """Handler for changing task status."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: ChangeTaskStatusCommand) -> TaskResponse:
        """Handle status change."""
        task = await self.repository.get_task_by_id(command.task_id, command.tenant_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Use aggregate to change status
        aggregate = TaskAggregate(task)
        try:
            aggregate.change_status(command.new_status, command.blocked_reason)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        task = await self.repository.update_task(task)

        # Create audit log
        audit_log = AuditLogEntry(
            tenant_id=task.tenant_id,
            task_id=task.id,
            user_id=command.user_id,
            action="status_changed",
            changes={"new_status": command.new_status.value}
        )
        await self.repository.add_audit_log(audit_log)

        # Emit event
        event = TaskStatusChanged(
            aggregate_id=task.id,
            tenant_id=task.tenant_id,
            payload={
                "task_id": str(task.id),
                "new_status": command.new_status.value,
                "user_id": str(command.user_id)
            }
        )
        await event_dispatcher.dispatch(event)

        # Invalidate cache
        await redis_client.delete_pattern(f"tenant:{command.tenant_id}:*:tasks:*")

        return TaskResponse.model_validate(task)


class DeleteTaskHandler:
    """Handler for task deletion."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: DeleteTaskCommand) -> None:
        """Handle task deletion."""
        success = await self.repository.soft_delete_task(command.task_id, command.tenant_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Emit event
        event = TaskDeleted(
            aggregate_id=command.task_id,
            tenant_id=command.tenant_id,
            payload={"task_id": str(command.task_id), "deleted_by": str(command.user_id)}
        )
        await event_dispatcher.dispatch(event)

        # Invalidate cache
        await redis_client.delete_pattern(f"tenant:{command.tenant_id}:*:tasks:*")


class AddTaskCommentHandler:
    """Handler for adding task comments."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, command: AddTaskCommentCommand) -> CommentResponse:
        """Handle adding comment."""
        # Verify task exists
        task = await self.repository.get_task_by_id(command.task_id, command.tenant_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        comment = Comment(
            tenant_id=command.tenant_id,
            task_id=command.task_id,
            user_id=command.user_id,
            content=command.content
        )

        comment = await self.repository.add_comment(comment)

        # Emit event
        event = TaskCommentAdded(
            aggregate_id=command.task_id,
            tenant_id=command.tenant_id,
            payload={
                "task_id": str(command.task_id),
                "comment_id": str(comment.id),
                "user_id": str(command.user_id)
            }
        )
        await event_dispatcher.dispatch(event)

        return CommentResponse.model_validate(comment)


class GetTaskByIdHandler:
    """Handler for getting task by ID."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, query: GetTaskByIdQuery) -> TaskResponse:
        """Handle get task by ID."""
        task = await self.repository.get_task_by_id(query.task_id, query.tenant_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        return TaskResponse.model_validate(task)


class GetUserTasksHandler:
    """Handler for getting user tasks with caching."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, query: GetUserTasksQuery) -> TaskListResponse:
        """Handle get user tasks with Redis caching."""
        return await self._get_tasks_cached(query)

    @cached(ttl=60, key_prefix="tasks:list")
    async def _get_tasks_cached(self, query: GetUserTasksQuery) -> TaskListResponse:
        """Fetch tasks from database with caching."""
        tasks, total = await self.repository.get_user_tasks(
            tenant_id=query.tenant_id,
            user_id=query.user_id,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order
        )

        return TaskListResponse(
            items=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=query.page,
            page_size=query.page_size
        )



class GetTaskStatisticsHandler:
    """Handler for getting task statistics with caching."""

    def __init__(self, repository: TaskRepository) -> None:
        """Initialize handler."""
        self.repository = repository

    async def handle(self, query: GetTaskStatisticsQuery) -> TaskStatisticsResponse:
        """Handle get task statistics with Redis caching."""
        return await self._get_statistics_cached(query)

    @cached(ttl=300, key_prefix="tasks:statistics")
    async def _get_statistics_cached(self, query: GetTaskStatisticsQuery) -> TaskStatisticsResponse:
        """Fetch statistics from database with caching."""
        stats = await self.repository.get_task_statistics(query.tenant_id)

        return TaskStatisticsResponse(
            total_tasks=stats["total_tasks"],
            tasks_by_status={k.value: v for k, v in stats["tasks_by_status"].items()},
            tasks_by_priority={},
            overdue_tasks=stats["overdue_tasks"],
            completed_this_month=0
        )


