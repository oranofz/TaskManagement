"""Unit tests for authentication."""
import pytest
import pyotp
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from fastapi import HTTPException
from app.auth.domain.models import User
from app.auth.repository import AuthRepository
from app.auth.commands import RegisterUserCommand, LoginCommand, RefreshTokenCommand, LogoutCommand
from app.auth.handlers import (
    RegisterUserHandler,
    LoginHandler,
    RefreshTokenHandler,
    LogoutHandler
)
from app.shared.security.password import password_handler


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_register_user_success(mock_check_compromised, db_session, test_tenant_id):
    """Test successful user registration."""
    repository = AuthRepository(db_session)
    handler = RegisterUserHandler(repository)

    command = RegisterUserCommand(
        email="test@example.com",
        username="testuser",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )

    user_response = await handler.handle(command)

    assert user_response.email == "test@example.com"
    assert user_response.username == "testuser"
    assert user_response.tenant_id == test_tenant_id
    assert user_response.is_active is True
    mock_check_compromised.assert_called_once_with("SecurePass123!@#")


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=True)
async def test_register_user_compromised_password(mock_check_compromised, db_session, test_tenant_id):
    """Test registration fails with compromised password."""
    repository = AuthRepository(db_session)
    handler = RegisterUserHandler(repository)

    command = RegisterUserCommand(
        email="test@example.com",
        username="testuser",
        password="Password123!",
        tenant_id=test_tenant_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command)

    assert exc_info.value.status_code == 400
    assert "compromised" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_register_user_duplicate_email(mock_check_compromised, db_session, test_tenant_id):
    """Test registration fails with duplicate email."""
    repository = AuthRepository(db_session)
    handler = RegisterUserHandler(repository)

    # Create first user
    command1 = RegisterUserCommand(
        email="test@example.com",
        username="testuser1",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )
    await handler.handle(command1)

    # Try to create second user with same email
    command2 = RegisterUserCommand(
        email="test@example.com",
        username="testuser2",
        password="SecurePass456!@#",
        tenant_id=test_tenant_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command2)

    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail


@pytest.mark.asyncio
async def test_password_strength_validation():
    """Test password strength validation rules."""
    # Valid password
    is_valid, error = password_handler.validate_password_strength("SecurePass123!@#")
    assert is_valid is True
    assert error is None

    # Too short
    is_valid, error = password_handler.validate_password_strength("Short1!")
    assert is_valid is False
    assert "12 characters" in error

    # No uppercase
    is_valid, error = password_handler.validate_password_strength("securepass123!@#")
    assert is_valid is False
    assert "uppercase" in error

    # No lowercase
    is_valid, error = password_handler.validate_password_strength("SECUREPASS123!@#")
    assert is_valid is False
    assert "lowercase" in error

    # No number
    is_valid, error = password_handler.validate_password_strength("SecurePass!@#")
    assert is_valid is False
    assert "number" in error

    # No special character
    is_valid, error = password_handler.validate_password_strength("SecurePass123")
    assert is_valid is False
    assert "special character" in error


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_login_success(mock_check_compromised, db_session, test_tenant_id):
    """Test successful login."""
    repository = AuthRepository(db_session)

    # Create user
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True
    )
    await repository.create_user(user)

    # Login
    handler = LoginHandler(repository)
    command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )

    token_response = await handler.handle(command)

    assert token_response.access_token is not None
    assert token_response.refresh_token is not None
    assert token_response.expires_in > 0


@pytest.mark.asyncio
async def test_login_invalid_credentials(db_session, test_tenant_id):
    """Test login with invalid credentials."""
    repository = AuthRepository(db_session)

    # Create user
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True
    )
    await repository.create_user(user)

    # Try login with wrong password
    handler = LoginHandler(repository)
    command = LoginCommand(
        email="test@example.com",
        password="WrongPassword123!",
        tenant_id=test_tenant_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command)

    assert exc_info.value.status_code == 401
    assert "Invalid credentials" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_inactive_user(db_session, test_tenant_id):
    """Test login with inactive user."""
    repository = AuthRepository(db_session)

    # Create inactive user
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=False
    )
    await repository.create_user(user)

    # Try login
    handler = LoginHandler(repository)
    command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_login_with_mfa_success(mock_check_compromised, db_session, test_tenant_id):
    """Test login with MFA enabled."""
    repository = AuthRepository(db_session)

    # Create user with MFA enabled
    mfa_secret = pyotp.random_base32()
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True,
        mfa_enabled=True,
        mfa_secret=mfa_secret
    )
    await repository.create_user(user)

    # Generate valid MFA code
    totp = pyotp.TOTP(mfa_secret)
    mfa_code = totp.now()

    # Login with MFA
    handler = LoginHandler(repository)
    command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id,
        mfa_code=mfa_code
    )

    token_response = await handler.handle(command)

    assert token_response.access_token is not None
    assert token_response.refresh_token is not None


@pytest.mark.asyncio
async def test_login_with_mfa_invalid_code(db_session, test_tenant_id):
    """Test login with MFA fails with invalid code."""
    repository = AuthRepository(db_session)

    # Create user with MFA enabled
    mfa_secret = pyotp.random_base32()
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True,
        mfa_enabled=True,
        mfa_secret=mfa_secret
    )
    await repository.create_user(user)

    # Login with invalid MFA code
    handler = LoginHandler(repository)
    command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id,
        mfa_code="000000"  # Invalid code
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command)

    assert exc_info.value.status_code == 401
    assert "Invalid MFA code" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_with_mfa_missing_code(db_session, test_tenant_id):
    """Test login with MFA fails when code is missing."""
    repository = AuthRepository(db_session)

    # Create user with MFA enabled
    mfa_secret = pyotp.random_base32()
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True,
        mfa_enabled=True,
        mfa_secret=mfa_secret
    )
    await repository.create_user(user)

    # Login without MFA code
    handler = LoginHandler(repository)
    command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle(command)

    assert exc_info.value.status_code == 400
    assert "MFA code required" in exc_info.value.detail


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_refresh_token_rotation(mock_check_compromised, db_session, test_tenant_id):
    """Test refresh token rotation creates new token and revokes old one."""
    repository = AuthRepository(db_session)

    # Create user and login
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True
    )
    await repository.create_user(user)

    login_handler = LoginHandler(repository)
    login_command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )
    login_response = await login_handler.handle(login_command)

    # Refresh token
    refresh_handler = RefreshTokenHandler(repository)
    refresh_command = RefreshTokenCommand(
        refresh_token=login_response.refresh_token
    )
    refresh_response = await refresh_handler.handle(refresh_command)

    # Verify new tokens
    assert refresh_response.access_token is not None
    assert refresh_response.refresh_token is not None
    assert refresh_response.refresh_token != login_response.refresh_token

    # Verify old token is revoked - attempting to use it again should fail
    with pytest.raises(HTTPException) as exc_info:
        await refresh_handler.handle(refresh_command)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_refresh_token_reuse_detection(mock_check_compromised, db_session, test_tenant_id):
    """Test refresh token reuse detection revokes entire token family."""
    repository = AuthRepository(db_session)

    # Create user and login
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True
    )
    await repository.create_user(user)

    login_handler = LoginHandler(repository)
    login_command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )
    login_response = await login_handler.handle(login_command)

    # First refresh
    refresh_handler = RefreshTokenHandler(repository)
    refresh_command_1 = RefreshTokenCommand(
        refresh_token=login_response.refresh_token
    )
    refresh_response_1 = await refresh_handler.handle(refresh_command_1)

    # Second refresh with new token
    refresh_command_2 = RefreshTokenCommand(
        refresh_token=refresh_response_1.refresh_token
    )
    refresh_response_2 = await refresh_handler.handle(refresh_command_2)

    # Try to reuse first refresh token (should detect reuse and revoke family)
    with pytest.raises(HTTPException) as exc_info:
        await refresh_handler.handle(refresh_command_1)

    assert exc_info.value.status_code == 401

    # Verify all tokens in family are now invalid
    with pytest.raises(HTTPException):
        await refresh_handler.handle(refresh_command_2)


@pytest.mark.asyncio
@patch('app.auth.handlers.password_handler.check_compromised_password', new_callable=AsyncMock, return_value=False)
async def test_logout_revokes_token(mock_check_compromised, db_session, test_tenant_id):
    """Test logout revokes refresh token."""
    repository = AuthRepository(db_session)

    # Create user and login
    user = User(
        tenant_id=test_tenant_id,
        email="test@example.com",
        username="testuser",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True
    )
    await repository.create_user(user)

    login_handler = LoginHandler(repository)
    login_command = LoginCommand(
        email="test@example.com",
        password="SecurePass123!@#",
        tenant_id=test_tenant_id
    )
    login_response = await login_handler.handle(login_command)

    # Logout
    logout_handler = LogoutHandler(repository)
    logout_command = LogoutCommand(
        refresh_token=login_response.refresh_token,
        tenant_id=test_tenant_id
    )
    await logout_handler.handle(logout_command)

    # Verify token is revoked - cannot refresh
    refresh_handler = RefreshTokenHandler(repository)
    refresh_command = RefreshTokenCommand(
        refresh_token=login_response.refresh_token
    )

    with pytest.raises(HTTPException) as exc_info:
        await refresh_handler.handle(refresh_command)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_cross_tenant_isolation_user_access(db_session):
    """Test that users cannot access data from different tenants."""
    repository = AuthRepository(db_session)

    tenant_id_1 = uuid4()
    tenant_id_2 = uuid4()

    # Create user in tenant 1
    user1 = User(
        tenant_id=tenant_id_1,
        email="user1@tenant1.com",
        username="user1",
        password_hash=password_handler.hash_password("SecurePass123!@#"),
        roles=["MEMBER"],
        permissions=["tasks.read"],
        is_active=True
    )
    await repository.create_user(user1)

    # Try to get user1 from tenant 2 - should fail
    found_user = await repository.get_user_by_email("user1@tenant1.com", tenant_id_2)
    assert found_user is None

    # Should work from correct tenant
    found_user = await repository.get_user_by_email("user1@tenant1.com", tenant_id_1)
    assert found_user is not None
    assert found_user.tenant_id == tenant_id_1


@pytest.mark.asyncio
async def test_password_hashing_and_verification():
    """Test password hashing and verification."""
    password = "SecurePass123!@#"

    # Hash password
    password_hash = password_handler.hash_password(password)

    # Verify correct password
    assert password_handler.verify_password(password, password_hash) is True

    # Verify incorrect password
    assert password_handler.verify_password("WrongPassword123!", password_hash) is False

    # Verify hash is different each time
    hash2 = password_handler.hash_password(password)
    assert password_hash != hash2

