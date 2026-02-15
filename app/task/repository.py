"""Task repository for data access."""
from datetime import datetime, UTC
from typing import Optional, List
from uuid import UUID

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.task.domain.models import Task, Comment, AuditLogEntry, TaskStatus


class TaskRepository:
    """Repository for task data access."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        self.session = session

    async def get_task_by_id(self, task_id: UUID, tenant_id: UUID) -> Optional[Task]:
        """Get task by ID with tenant isolation."""
        result = await self.session.execute(
            select(Task).where(
                Task.id == task_id,
                Task.tenant_id == tenant_id,
                Task.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_user_tasks(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        status: Optional[TaskStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Task], int]:
        """Get paginated tasks with filters."""
        query = select(Task).where(
            Task.tenant_id == tenant_id,
            Task.is_deleted == False
        )

        if user_id:
            query = query.where(
                (Task.assigned_to_user_id == user_id) | (Task.created_by_user_id == user_id)
            )

        if status:
            query = query.where(Task.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Get paginated results
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Task.created_at.desc())

        result = await self.session.execute(query)
        tasks = list(result.scalars().all())

        return tasks, total

    async def create_task(self, task: Task) -> Task:
        """Create new task."""
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info(f"Task created: {task.id}")
        return task

    async def update_task(self, task: Task) -> Task:
        """Update task."""
        task.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.session.commit()
        await self.session.refresh(task)
        logger.info(f"Task updated: {task.id}")
        return task

    async def soft_delete_task(self, task_id: UUID, tenant_id: UUID) -> bool:
        """Soft delete task."""
        task = await self.get_task_by_id(task_id, tenant_id)
        if task:
            task.is_deleted = True
            task.updated_at = datetime.now(UTC).replace(tzinfo=None)
            await self.session.commit()
            logger.info(f"Task deleted: {task_id}")
            return True
        return False

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment to task."""
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        logger.info(f"Comment added to task: {comment.task_id}")
        return comment

    async def get_task_comments(self, task_id: UUID, tenant_id: UUID) -> List[Comment]:
        """Get all comments for a task."""
        result = await self.session.execute(
            select(Comment).where(
                Comment.task_id == task_id,
                Comment.tenant_id == tenant_id
            ).order_by(Comment.created_at.asc())
        )
        return list(result.scalars().all())

    async def add_audit_log(self, audit_log: AuditLogEntry) -> None:
        """Add audit log entry."""
        self.session.add(audit_log)
        await self.session.commit()

    async def get_task_statistics(self, tenant_id: UUID) -> dict:
        """Get task statistics for tenant."""
        # Total tasks
        total_result = await self.session.execute(
            select(func.count()).where(
                Task.tenant_id == tenant_id,
                Task.is_deleted == False
            )
        )
        total = total_result.scalar_one()

        # Tasks by status
        status_result = await self.session.execute(
            select(Task.status, func.count()).where(
                Task.tenant_id == tenant_id,
                Task.is_deleted == False
            ).group_by(Task.status)
        )
        tasks_by_status = {status: count for status, count in status_result.all()}

        # Overdue tasks
        overdue_result = await self.session.execute(
            select(func.count()).where(
                Task.tenant_id == tenant_id,
                Task.is_deleted == False,
                Task.due_date < datetime.now(UTC).replace(tzinfo=None),
                Task.status != TaskStatus.DONE
            )
        )
        overdue = overdue_result.scalar_one()

        return {
            "total_tasks": total,
            "tasks_by_status": tasks_by_status,
            "overdue_tasks": overdue
        }

