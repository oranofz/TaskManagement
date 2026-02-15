# Authentication Guide

## Overview
Enterprise-grade JWT authentication with RS256 algorithm, refresh token rotation, and multi-factor authentication support.

## Authentication Flow

### 1. User Registration
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "John Doe",
  "password": "SecurePass123!@#",
  "tenant_id": "tenant-uuid"
}
```

**Password Requirements:**
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 number
- At least 1 special character
- Not in HaveIBeenPwned database

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "username": "John Doe",
    "tenant_id": "tenant-uuid"
  }
}
```

---

### 2. Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!@#"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Token Details:**
- **Access Token**: Valid for 15 minutes
- **Refresh Token**: Valid for 7 days
- **Algorithm**: RS256 (RSA asymmetric)

---

### 3. Using Access Token
Include in Authorization header for all authenticated requests:

```http
GET /api/v1/tasks
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

### 4. Refresh Token Rotation
When access token expires, use refresh token to get new tokens:

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** Same as login (new access + refresh token pair)

**Security Features:**
- ✅ Old refresh token immediately revoked
- ✅ Token family tracking for reuse detection
- ✅ If revoked token reused → entire family revoked
- ✅ Device fingerprinting (optional)

---

### 5. Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

Revokes the current refresh token and invalidates the session.

---

## JWT Token Structure

### Access Token Claims
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "tenant_id": "tenant-uuid",
  "roles": ["MEMBER", "PROJECT_MANAGER"],
  "permissions": ["tasks.read", "tasks.create", "tasks.update"],
  "department_id": "dept-uuid",
  "jti": "token-uuid",
  "iat": 1708000000,
  "exp": 1708000900
}
```

### Refresh Token Claims
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "jti": "refresh-token-uuid",
  "family_id": "token-family-uuid",
  "iat": 1708000000,
  "exp": 1708604800
}
```

---

## Multi-Factor Authentication (MFA)

### Enable MFA
```http
POST /api/v1/auth/mfa/enable
Authorization: Bearer <token>
```

Returns TOTP secret and QR code URL for authenticator apps.

### Login with MFA
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!@#",
  "mfa_code": "123456"
}
```

---

## Authorization

### Role-Based Access Control (RBAC)
- **SYSTEM_ADMIN**: Full system access
- **TENANT_ADMIN**: Tenant-wide management
- **PROJECT_MANAGER**: Project management, task assignment
- **MEMBER**: Create/update own tasks, view assigned
- **GUEST**: Read-only access

### Permission Checks
Permissions extracted from JWT claims:
- `tasks.read`, `tasks.create`, `tasks.update`, `tasks.delete`
- `tasks.assign`, `reports.view`, `users.manage`

### Resource-Based Authorization
Users can access tasks if:
- They created the task
- Task is assigned to them
- They're in the same department (with read permission)
- They're admin/manager

---

## Security Best Practices

1. **Store tokens securely** (HttpOnly cookies recommended for web)
2. **Never log tokens** in application logs
3. **Implement token refresh** before access token expires
4. **Handle 401 responses** by refreshing or redirecting to login
5. **Clear tokens on logout** from client storage
6. **Use HTTPS** in production (required for security headers)

---

## Testing Authentication

See [QUICKSTART.md](QUICKSTART.md) for curl examples or import [postman_collection.json](postman_collection.json) into Postman.

