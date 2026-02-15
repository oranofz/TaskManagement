"""Task aggregate for domain logic."""
from typing import Optional
from uuid import UUID
from datetime import datetime, UTC
from app.task.domain.models import Task, TaskStatus


class TaskAggregate:
    """Task aggregate for business logic and validation."""

    def __init__(self, task: Task) -> None:
        """Initialize task aggregate."""
        self.task = task

    def can_transition_to(self, new_status: TaskStatus) -> tuple[bool, Optional[str]]:
        """
        Check if status transition is valid.

        Args:
            new_status: Target status

        Returns:
            Tuple of (is_valid, error_message)
        """
        current = self.task.status

        # Cannot transition from DONE
        if current == TaskStatus.DONE and new_status != TaskStatus.DONE:
            return False, "Cannot transition from DONE status"

        # Valid transitions
        valid_transitions = {
            TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
            TaskStatus.IN_PROGRESS: [TaskStatus.IN_REVIEW, TaskStatus.BLOCKED, TaskStatus.TODO],
            TaskStatus.IN_REVIEW: [TaskStatus.DONE, TaskStatus.IN_PROGRESS],
            TaskStatus.BLOCKED: [TaskStatus.TODO, TaskStatus.IN_PROGRESS],
            TaskStatus.DONE: [TaskStatus.DONE],
            TaskStatus.CANCELLED: [TaskStatus.CANCELLED]
        }

        if new_status not in valid_transitions.get(current, []):
            return False, f"Invalid transition from {current} to {new_status}"

        # Additional validations
        if new_status == TaskStatus.IN_REVIEW and not self.task.assigned_to_user_id:
            return False, "Task must be assigned before moving to IN_REVIEW"

        if new_status == TaskStatus.BLOCKED and not self.task.blocked_reason:
            return False, "Blocked reason is required when status is BLOCKED"

        return True, None

    def assign_to(self, user_id: UUID) -> None:
        """Assign task to user."""
        self.task.assigned_to_user_id = user_id
        self.task.updated_at = datetime.now(UTC).replace(tzinfo=None)
        if self.task.version is not None:
            self.task.version += 1

    def change_status(self, new_status: TaskStatus, blocked_reason: Optional[str] = None) -> None:
        """
        Change task status with validation.

        Args:
            new_status: New status
            blocked_reason: Reason if status is BLOCKED

        Raises:
            ValueError: If transition is invalid
        """
        is_valid, error = self.can_transition_to(new_status)
        if not is_valid:
            raise ValueError(error)

        self.task.status = new_status
        if blocked_reason:
            self.task.blocked_reason = blocked_reason
        self.task.updated_at = datetime.now(UTC).replace(tzinfo=None)
        if self.task.version is not None:
            self.task.version += 1

    def update_details(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[datetime] = None,
        estimated_hours: Optional[float] = None
    ) -> None:
        """Update task details."""
        if title:
            self.task.title = title
        if description is not None:
            self.task.description = description
        if priority:
            self.task.priority = priority
        if due_date is not None:
            self.task.due_date = due_date
        if estimated_hours is not None:
            self.task.estimated_hours = estimated_hours

        self.task.updated_at = datetime.now(UTC).replace(tzinfo=None)
        if self.task.version is not None:
            self.task.version += 1

