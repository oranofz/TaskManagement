"""Unit tests for authorization and access control."""
import pytest
from uuid import uuid4
from fastapi import HTTPException
from app.shared.security.authorization import (
    check_permission,
    check_role,
    check_resource_access,
    require_permission,
    require_role,
    Role,
    Permission
)


def test_check_permission_with_valid_permission():
    """Test permission check with valid permission."""
    user_permissions = [Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE]

    assert check_permission(user_permissions, Permission.TASKS_READ) is True
    assert check_permission(user_permissions, Permission.TASKS_CREATE) is True
    assert check_permission(user_permissions, Permission.TASKS_UPDATE) is True


def test_check_permission_with_invalid_permission():
    """Test permission check with invalid permission."""
    user_permissions = [Permission.TASKS_READ, Permission.TASKS_CREATE]

    assert check_permission(user_permissions, Permission.TASKS_DELETE) is False
    assert check_permission(user_permissions, Permission.USERS_MANAGE) is False
    assert check_permission(user_permissions, Permission.TENANT_CONFIGURE) is False


def test_check_permission_empty_permissions():
    """Test permission check with empty permissions list."""
    user_permissions = []

    assert check_permission(user_permissions, Permission.TASKS_READ) is False


def test_check_role_with_valid_role():
    """Test role check with valid role."""
    user_roles = [Role.MEMBER, Role.TEAM_LEAD]

    assert check_role(user_roles, Role.MEMBER) is True
    assert check_role(user_roles, Role.TEAM_LEAD) is True


def test_check_role_with_invalid_role():
    """Test role check with invalid role."""
    user_roles = [Role.MEMBER]

    assert check_role(user_roles, Role.TENANT_ADMIN) is False
    assert check_role(user_roles, Role.SYSTEM_ADMIN) is False


def test_require_permission_success():
    """Test require permission succeeds when user has permission."""
    user_permissions = [Permission.TASKS_READ, Permission.TASKS_CREATE]

    # Should not raise exception
    require_permission(Permission.TASKS_READ, user_permissions)
    require_permission(Permission.TASKS_CREATE, user_permissions)


def test_require_permission_raises_exception():
    """Test require permission raises HTTPException when permission missing."""
    user_permissions = [Permission.TASKS_READ]

    with pytest.raises(HTTPException) as exc_info:
        require_permission(Permission.TASKS_DELETE, user_permissions)

    assert exc_info.value.status_code == 403
    assert "Missing required permission" in exc_info.value.detail
    assert "TASKS_DELETE" in exc_info.value.detail


def test_require_role_success():
    """Test require role succeeds when user has role."""
    user_roles = [Role.MEMBER, Role.TEAM_LEAD]

    # Should not raise exception
    require_role(Role.MEMBER, user_roles)
    require_role(Role.TEAM_LEAD, user_roles)


def test_require_role_raises_exception():
    """Test require role raises HTTPException when role missing."""
    user_roles = [Role.MEMBER]

    with pytest.raises(HTTPException) as exc_info:
        require_role(Role.TENANT_ADMIN, user_roles)

    assert exc_info.value.status_code == 403
    assert "Missing required role" in exc_info.value.detail
    assert "TENANT_ADMIN" in exc_info.value.detail


def test_resource_access_tenant_admin_always_granted():
    """Test TENANT_ADMIN role grants access to any resource."""
    user_id = uuid4()
    other_user_id = uuid4()
    dept1 = uuid4()
    dept2 = uuid4()

    # TENANT_ADMIN has access regardless of ownership, assignment, or department
    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.TENANT_ADMIN],
        user_permissions=[],
        resource_owner_id=other_user_id,
        resource_assigned_to_id=other_user_id,
        user_department_id=dept1,
        resource_department_id=dept2
    )

    assert has_access is True


def test_resource_access_owner_granted():
    """Test resource owner always has access."""
    user_id = uuid4()
    other_dept = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[],
        resource_owner_id=user_id,  # User is owner
        resource_assigned_to_id=None,
        user_department_id=None,
        resource_department_id=other_dept
    )

    assert has_access is True


def test_resource_access_assigned_user_granted():
    """Test assigned user has access."""
    user_id = uuid4()
    owner_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[],
        resource_owner_id=owner_id,
        resource_assigned_to_id=user_id,  # User is assigned
        user_department_id=None,
        resource_department_id=None
    )

    assert has_access is True


def test_resource_access_same_department_with_permission():
    """Test access granted for same department with read permission."""
    user_id = uuid4()
    owner_id = uuid4()
    department_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=owner_id,
        resource_assigned_to_id=None,
        user_department_id=department_id,
        resource_department_id=department_id  # Same department
    )

    assert has_access is True


def test_resource_access_same_department_without_permission():
    """Test access denied for same department without read permission."""
    user_id = uuid4()
    owner_id = uuid4()
    department_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_CREATE],  # Has create but not read
        resource_owner_id=owner_id,
        resource_assigned_to_id=None,
        user_department_id=department_id,
        resource_department_id=department_id
    )

    assert has_access is False


def test_resource_access_different_department_denied():
    """Test access denied for different department."""
    user_id = uuid4()
    owner_id = uuid4()
    user_dept = uuid4()
    resource_dept = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=owner_id,
        resource_assigned_to_id=None,
        user_department_id=user_dept,
        resource_department_id=resource_dept  # Different department
    )

    assert has_access is False


def test_resource_access_no_department_denied():
    """Test access denied when departments are not set."""
    user_id = uuid4()
    owner_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=owner_id,
        resource_assigned_to_id=None,
        user_department_id=None,
        resource_department_id=None
    )

    assert has_access is False


def test_resource_access_multiple_roles():
    """Test access with multiple roles."""
    user_id = uuid4()
    owner_id = uuid4()

    # Has TEAM_LEAD but not owner
    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.MEMBER, Role.TEAM_LEAD, Role.PROJECT_MANAGER],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=owner_id,
        resource_assigned_to_id=None,
        user_department_id=None,
        resource_department_id=None
    )

    # Should be denied (not TENANT_ADMIN, not owner, not assigned, no department match)
    assert has_access is False


def test_resource_access_department_head_same_department():
    """Test DEPARTMENT_HEAD access to resources in their department."""
    user_id = uuid4()
    owner_id = uuid4()
    department_id = uuid4()

    has_access = check_resource_access(
        user_id=user_id,
        user_roles=[Role.DEPARTMENT_HEAD],
        user_permissions=[Permission.TASKS_READ],
        resource_owner_id=owner_id,
        resource_assigned_to_id=None,
        user_department_id=department_id,
        resource_department_id=department_id
    )

    assert has_access is True


def test_all_roles_enum():
    """Test all role enum values are defined."""
    expected_roles = [
        Role.SYSTEM_ADMIN,
        Role.TENANT_ADMIN,
        Role.DEPARTMENT_HEAD,
        Role.PROJECT_MANAGER,
        Role.TEAM_LEAD,
        Role.MEMBER,
        Role.GUEST
    ]

    for role in expected_roles:
        assert isinstance(role, Role)


def test_all_permissions_enum():
    """Test all permission enum values are defined."""
    expected_permissions = [
        Permission.TASKS_READ,
        Permission.TASKS_CREATE,
        Permission.TASKS_UPDATE,
        Permission.TASKS_DELETE,
        Permission.TASKS_ASSIGN,
        Permission.REPORTS_VIEW,
        Permission.USERS_MANAGE,
        Permission.TENANT_CONFIGURE
    ]

    for permission in expected_permissions:
        assert isinstance(permission, Permission)


def test_permission_string_values():
    """Test permission string values follow dot notation."""
    assert Permission.TASKS_READ.value == "tasks.read"
    assert Permission.TASKS_CREATE.value == "tasks.create"
    assert Permission.TASKS_UPDATE.value == "tasks.update"
    assert Permission.TASKS_DELETE.value == "tasks.delete"
    assert Permission.TASKS_ASSIGN.value == "tasks.assign"
    assert Permission.REPORTS_VIEW.value == "reports.view"
    assert Permission.USERS_MANAGE.value == "users.manage"
    assert Permission.TENANT_CONFIGURE.value == "tenant.configure"


