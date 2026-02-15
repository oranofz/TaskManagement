"""Authorization utilities and decorators."""
from enum import Enum
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from app.shared.context import get_user_id, get_tenant_id


class Role(str, Enum):
    """User roles."""
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    TEAM_LEAD = "TEAM_LEAD"
    MEMBER = "MEMBER"
    GUEST = "GUEST"


class Permission(str, Enum):
    """User permissions."""
    TASKS_READ = "tasks.read"
    TASKS_CREATE = "tasks.create"
    TASKS_UPDATE = "tasks.update"
    TASKS_DELETE = "tasks.delete"
    TASKS_ASSIGN = "tasks.assign"
    REPORTS_VIEW = "reports.view"
    USERS_MANAGE = "users.manage"
    TENANT_CONFIGURE = "tenant.configure"


class SubscriptionPlan(str, Enum):
    """Subscription plans."""
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


def check_permission(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if user has required permission.

    Args:
        user_permissions: User's permissions
        required_permission: Required permission

    Returns:
        True if user has permission
    """
    return required_permission in user_permissions


def check_role(user_roles: List[str], required_role: str) -> bool:
    """
    Check if user has required role.

    Args:
        user_roles: User's roles
        required_role: Required role

    Returns:
        True if user has role
    """
    return required_role in user_roles


def check_resource_access(
    user_id: UUID,
    user_roles: List[str],
    user_permissions: List[str],
    resource_owner_id: Optional[UUID],
    resource_assigned_to_id: Optional[UUID],
    user_department_id: Optional[UUID],
    resource_department_id: Optional[UUID]
) -> bool:
    """
    Check if user has access to resource.

    Args:
        user_id: Current user ID
        user_roles: User's roles
        user_permissions: User's permissions
        resource_owner_id: Resource owner ID
        resource_assigned_to_id: Resource assigned to user ID
        user_department_id: User's department ID
        resource_department_id: Resource's department ID

    Returns:
        True if user has access
    """
    # Tenant admin has access to everything
    if Role.TENANT_ADMIN in user_roles:
        return True

    # Owner has access
    if resource_owner_id == user_id:
        return True

    # Assigned user has access
    if resource_assigned_to_id == user_id:
        return True

    # Same department with read permission
    if (
        user_department_id
        and resource_department_id
        and user_department_id == resource_department_id
        and Permission.TASKS_READ in user_permissions
    ):
        return True

    return False


def require_permission(required_permission: str, user_permissions: List[str]) -> None:
    """
    Require specific permission.

    Args:
        required_permission: Required permission
        user_permissions: User's permissions

    Raises:
        HTTPException: If user doesn't have permission
    """
    if not check_permission(user_permissions, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {required_permission}"
        )


def require_role(required_role: str, user_roles: List[str]) -> None:
    """
    Require specific role.

    Args:
        required_role: Required role
        user_roles: User's roles

    Raises:
        HTTPException: If user doesn't have role
    """
    if not check_role(user_roles, required_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required role: {required_role}"
        )

