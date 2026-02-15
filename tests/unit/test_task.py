"""Unit tests for task management."""
import pytest
from uuid import uuid4
from fastapi import HTTPException
from app.task.domain.models import Task, TaskStatus, Priority
from app.task.domain.aggregates import TaskAggregate
from app.task.repository import TaskRepository
from app.task.commands import (
    CreateTaskCommand,
    UpdateTaskCommand,
    AssignTaskCommand,
    ChangeTaskStatusCommand,
    DeleteTaskCommand,
    AddTaskCommentCommand
)
from app.task.handlers import (
    CreateTaskHandler,
    UpdateTaskHandler,
    AssignTaskHandler,
    ChangeTaskStatusHandler,
    DeleteTaskHandler,
    AddTaskCommentHandler
)
from app.shared.security.authorization import (
    check_permission,
    check_role,
    check_resource_access,
    Role,
    Permission
)


@pytest.mark.asyncio
async def test_create_task_success(db_session, test_tenant_id, test_user_id):
    """Test successful task creation."""
    repository = TaskRepository(db_session)
    handler = CreateTaskHandler(repository)

    project_id = uuid4()

    command = CreateTaskCommand(
        tenant_id=test_tenant_id,
        project_id=project_id,
        title="Test Task",
        description="Test Description",
        priority=Priority.HIGH,
        assigned_to_user_id=test_user_id,
        created_by_user_id=test_user_id,
        due_date=None,
        tags=["test", "urgent"],
        estimated_hours=8.0
    )

    task_response = await handler.handle(command)

    assert task_response.title == "Test Task"
    assert task_response.description == "Test Description"
    assert task_response.priority == Priority.HIGH
    assert task_response.status == TaskStatus.TODO
    assert task_response.tenant_id == test_tenant_id
    assert task_response.assigned_to_user_id == test_user_id
    assert task_response.estimated_hours == 8.0
    assert "test" in task_response.tags


@pytest.mark.asyncio
async def test_update_task_success(db_session, test_tenant_id, test_user_id):
    """Test successful task update."""
    repository = TaskRepository(db_session)

    # Create task
    project_id = uuid4()
    task = Task(
        tenant_id=test_tenant_id,
        project_id=project_id,
        title="Original Title",
        description="Original Description",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=test_user_id
    )
    task = await repository.create_task(task)

    # Update task
    handler = UpdateTaskHandler(repository)
    command = UpdateTaskCommand(
        task_id=task.id,
        tenant_id=test_tenant_id,
        title="Updated Title",
        description="Updated Description",
        priority=Priority.HIGH,
        estimated_hours=10.0
    )

    updated_task = await handler.handle(command)

    assert updated_task.title == "Updated Title"
    assert updated_task.description == "Updated Description"
    assert updated_task.priority == Priority.HIGH
    assert updated_task.estimated_hours == 10.0
    assert updated_task.version == 2  # Version incremented


@pytest.mark.asyncio
async def test_update_task_not_found(db_session, test_tenant_id):
    """Test update task with non-existent task ID."""
    repository = TaskRepository(db_session)
    handler = UpdateTaskHandler(repository)

    command = UpdateTaskCommand(
        task_id=uuid4(),
        tenant_id=test_tenant_id,
        title="Updated Title"
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_assign_task_success(db_session, test_tenant_id, test_user_id):
    """Test successful task assignment."""
    repository = TaskRepository(db_session)

    # Create task
    project_id = uuid4()
    task = Task(
        tenant_id=test_tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=test_user_id
    )
    task = await repository.create_task(task)

    # Assign task
    assigned_user_id = uuid4()
    handler = AssignTaskHandler(repository)
    command = AssignTaskCommand(
        task_id=task.id,
        tenant_id=test_tenant_id,
        assigned_to_user_id=assigned_user_id,
        assigned_by_user_id=test_user_id
    )

    assigned_task = await handler.handle(command)

    assert assigned_task.assigned_to_user_id == assigned_user_id
    assert assigned_task.version == 2


@pytest.mark.asyncio
async def test_task_status_transition_todo_to_in_progress():
    """Test valid transition: TODO -> IN_PROGRESS."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id
    )

    aggregate = TaskAggregate(task)

    # Valid transition
    is_valid, error = aggregate.can_transition_to(TaskStatus.IN_PROGRESS)
    assert is_valid is True
    assert error is None

    aggregate.change_status(TaskStatus.IN_PROGRESS)
    assert task.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_task_status_transition_todo_to_blocked():
    """Test valid transition: TODO -> BLOCKED with reason."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id,
        blocked_reason="Waiting for dependencies"  # Set reason before transition
    )

    aggregate = TaskAggregate(task)

    # Transition to BLOCKED with reason
    aggregate.change_status(TaskStatus.BLOCKED, blocked_reason="Waiting for dependencies")
    assert task.status == TaskStatus.BLOCKED
    assert task.blocked_reason == "Waiting for dependencies"


@pytest.mark.asyncio
async def test_task_status_transition_in_progress_to_in_review():
    """Test valid transition: IN_PROGRESS -> IN_REVIEW."""
    project_id = uuid4()
    user_id = uuid4()
    assigned_user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id,
        assigned_to_user_id=assigned_user_id
    )

    aggregate = TaskAggregate(task)

    # Valid transition
    is_valid, error = aggregate.can_transition_to(TaskStatus.IN_REVIEW)
    assert is_valid is True

    aggregate.change_status(TaskStatus.IN_REVIEW)
    assert task.status == TaskStatus.IN_REVIEW


@pytest.mark.asyncio
async def test_task_status_transition_in_review_to_done():
    """Test valid transition: IN_REVIEW -> DONE."""
    project_id = uuid4()
    user_id = uuid4()
    assigned_user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.IN_REVIEW,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id,
        assigned_to_user_id=assigned_user_id
    )

    aggregate = TaskAggregate(task)

    # Valid transition
    is_valid, error = aggregate.can_transition_to(TaskStatus.DONE)
    assert is_valid is True

    aggregate.change_status(TaskStatus.DONE)
    assert task.status == TaskStatus.DONE


@pytest.mark.asyncio
async def test_task_status_transition_blocked_to_in_progress():
    """Test valid transition: BLOCKED -> IN_PROGRESS."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.BLOCKED,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id,
        blocked_reason="Was waiting"
    )

    aggregate = TaskAggregate(task)

    is_valid, error = aggregate.can_transition_to(TaskStatus.IN_PROGRESS)
    assert is_valid is True

    aggregate.change_status(TaskStatus.IN_PROGRESS)
    assert task.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_task_status_invalid_transition_todo_to_done():
    """Test invalid transition: TODO -> DONE."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id
    )

    aggregate = TaskAggregate(task)

    # Invalid transition
    is_valid, error = aggregate.can_transition_to(TaskStatus.DONE)
    assert is_valid is False
    assert "Invalid transition" in error

    # Should raise ValueError
    with pytest.raises(ValueError):
        aggregate.change_status(TaskStatus.DONE)


@pytest.mark.asyncio
async def test_task_status_cannot_transition_from_done():
    """Test that once a task is DONE, it cannot transition to other statuses."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.DONE,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id
    )

    aggregate = TaskAggregate(task)

    # Cannot go back to TODO
    is_valid, error = aggregate.can_transition_to(TaskStatus.TODO)
    assert is_valid is False
    assert "Cannot transition from DONE" in error

    # Cannot go back to IN_PROGRESS
    is_valid, error = aggregate.can_transition_to(TaskStatus.IN_PROGRESS)
    assert is_valid is False


@pytest.mark.asyncio
async def test_task_status_blocked_requires_reason():
    """Test that transitioning to BLOCKED requires a reason."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id
    )

    aggregate = TaskAggregate(task)

    # Transition without reason should be invalid
    is_valid, error = aggregate.can_transition_to(TaskStatus.BLOCKED)
    assert is_valid is False
    assert "Blocked reason is required" in error


@pytest.mark.asyncio
async def test_task_status_in_review_requires_assignment():
    """Test that transitioning to IN_REVIEW requires task to be assigned."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id,
        assigned_to_user_id=None  # Not assigned
    )

    aggregate = TaskAggregate(task)

    # Should be invalid
    is_valid, error = aggregate.can_transition_to(TaskStatus.IN_REVIEW)
    assert is_valid is False
    assert "must be assigned" in error.lower()


@pytest.mark.asyncio
async def test_change_task_status_handler(db_session, test_tenant_id, test_user_id):
    """Test change task status through handler."""
    repository = TaskRepository(db_session)

    # Create task
    project_id = uuid4()
    task = Task(
        tenant_id=test_tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=test_user_id
    )
    task = await repository.create_task(task)

    # Change status
    handler = ChangeTaskStatusHandler(repository)
    command = ChangeTaskStatusCommand(
        task_id=task.id,
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        new_status=TaskStatus.IN_PROGRESS
    )

    updated_task = await handler.handle(command)

    assert updated_task.status == TaskStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_delete_task_soft_delete(db_session, test_tenant_id, test_user_id):
    """Test soft delete of task."""
    from sqlalchemy import select
    repository = TaskRepository(db_session)

    # Create task
    project_id = uuid4()
    task = Task(
        tenant_id=test_tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=test_user_id
    )
    task = await repository.create_task(task)
    task_id = task.id

    # Delete task
    handler = DeleteTaskHandler(repository)
    command = DeleteTaskCommand(
        task_id=task.id,
        tenant_id=test_tenant_id,
        user_id=test_user_id
    )

    await handler.handle(command)

    # Verify task is soft deleted (repository filters it out, so returns None)
    deleted_task = await repository.get_task_by_id(task_id, test_tenant_id)
    assert deleted_task is None

    # Verify task still exists in database with is_deleted=True
    result = await db_session.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == test_tenant_id)
    )
    task_in_db = result.scalar_one_or_none()
    assert task_in_db is not None
    assert task_in_db.is_deleted is True


@pytest.mark.asyncio
async def test_add_task_comment(db_session, test_tenant_id, test_user_id):
    """Test adding comment to task."""
    repository = TaskRepository(db_session)

    # Create task
    project_id = uuid4()
    task = Task(
        tenant_id=test_tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=test_user_id
    )
    task = await repository.create_task(task)

    # Add comment
    handler = AddTaskCommentHandler(repository)
    command = AddTaskCommentCommand(
        task_id=task.id,
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        content="This is a test comment"
    )

    comment_response = await handler.handle(command)

    assert comment_response.content == "This is a test comment"
    assert comment_response.user_id == test_user_id
    assert comment_response.task_id == task.id


@pytest.mark.asyncio
async def test_cross_tenant_isolation_tasks(db_session, test_user_id):
    """Test that tasks are isolated by tenant."""
    repository = TaskRepository(db_session)

    tenant_id_1 = uuid4()
    tenant_id_2 = uuid4()
    project_id = uuid4()

    # Create task in tenant 1
    task1 = Task(
        tenant_id=tenant_id_1,
        project_id=project_id,
        title="Tenant 1 Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=test_user_id
    )
    task1 = await repository.create_task(task1)

    # Try to get task from tenant 2 - should fail
    task_from_wrong_tenant = await repository.get_task_by_id(task1.id, tenant_id_2)
    assert task_from_wrong_tenant is None

    # Should work from correct tenant
    task_from_correct_tenant = await repository.get_task_by_id(task1.id, tenant_id_1)
    assert task_from_correct_tenant is not None
    assert task_from_correct_tenant.tenant_id == tenant_id_1


@pytest.mark.asyncio
async def test_permission_check():
    """Test permission checking logic."""
    user_permissions = [Permission.TASKS_READ, Permission.TASKS_CREATE]

    # Has permission
    assert check_permission(user_permissions, Permission.TASKS_READ) is True
    assert check_permission(user_permissions, Permission.TASKS_CREATE) is True

    # Doesn't have permission
    assert check_permission(user_permissions, Permission.TASKS_DELETE) is False
    assert check_permission(user_permissions, Permission.USERS_MANAGE) is False


@pytest.mark.asyncio
async def test_role_check():
    """Test role checking logic."""
    user_roles = [Role.MEMBER, Role.TEAM_LEAD]

    # Has role
    assert check_role(user_roles, Role.MEMBER) is True
    assert check_role(user_roles, Role.TEAM_LEAD) is True

    # Doesn't have role
    assert check_role(user_roles, Role.TENANT_ADMIN) is False
    assert check_role(user_roles, Role.SYSTEM_ADMIN) is False


@pytest.mark.asyncio
async def test_resource_access_tenant_admin():
    """Test that TENANT_ADMIN has access to all resources."""
    user_id = uuid4()
    resource_owner_id = uuid4()  # Different user

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.TENANT_ADMIN],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=resource_owner_id,
        resource_assigned_to_id=None,
        user_department_id=None,
        resource_department_id=None
    )

    assert has_access is True


@pytest.mark.asyncio
async def test_resource_access_owner():
    """Test that resource owner has access."""
    user_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=user_id,  # Owner
        resource_assigned_to_id=None,
        user_department_id=None,
        resource_department_id=None
    )

    assert has_access is True


@pytest.mark.asyncio
async def test_resource_access_assigned_user():
    """Test that assigned user has access."""
    user_id = uuid4()
    resource_owner_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=resource_owner_id,
        resource_assigned_to_id=user_id,  # Assigned to user
        user_department_id=None,
        resource_department_id=None
    )

    assert has_access is True


@pytest.mark.asyncio
async def test_resource_access_same_department():
    """Test that users in same department with permission have access."""
    user_id = uuid4()
    resource_owner_id = uuid4()
    department_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=resource_owner_id,
        resource_assigned_to_id=None,
        user_department_id=department_id,
        resource_department_id=department_id  # Same department
    )

    assert has_access is True


@pytest.mark.asyncio
async def test_resource_access_denied():
    """Test that access is denied when no conditions are met."""
    user_id = uuid4()
    resource_owner_id = uuid4()
    user_department_id = uuid4()
    resource_department_id = uuid4()  # Different department

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=resource_owner_id,  # Different owner
        resource_assigned_to_id=None,  # Not assigned
        user_department_id=user_department_id,
        resource_department_id=resource_department_id  # Different department
    )

    assert has_access is False


@pytest.mark.asyncio
async def test_task_version_increments():
    """Test that task version increments on updates."""
    project_id = uuid4()
    user_id = uuid4()
    tenant_id = uuid4()

    task = Task(
        tenant_id=tenant_id,
        project_id=project_id,
        title="Test Task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        created_by_user_id=user_id,
        version=1
    )

    aggregate = TaskAggregate(task)

    # Change status
    aggregate.change_status(TaskStatus.IN_PROGRESS)
    assert task.version == 2

    # Assign
    aggregate.assign_to(uuid4())
    assert task.version == 3

    # Update details
    aggregate.update_details(title="Updated Title")
    assert task.version == 4

