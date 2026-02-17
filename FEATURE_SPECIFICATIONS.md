# Feature Specifications

## 1. Multi-Tenant Task Management

### Overview
Secure, isolated task management system supporting multiple organizations with data segregation.

### Requirements
- **FR1.1**: Each tenant has unique subdomain identifier
- **FR1.2**: Automatic tenant resolution from subdomain/header/JWT
- **FR1.3**: Complete data isolation at database query level
- **FR1.4**: Tenant-specific subscription plans (BASIC/PRO/ENTERPRISE)
- **FR1.5**: Per-tenant rate limiting and resource quotas

### User Stories
**As a** tenant administrator  
**I want** complete data isolation from other tenants  
**So that** my organization's data remains private and secure

**As a** system administrator  
**I want** to manage tenant quotas and subscriptions  
**So that** I can control resource usage and billing

### Acceptance Criteria
- ✅ Users from Tenant A cannot access Tenant B's data
- ✅ All queries automatically filtered by tenant_id
- ✅ Failed tenant resolution returns 401 Unauthorized
- ✅ Tenant settings stored in JSONB for flexibility
- ✅ Cache keys namespaced with tenant_id

### Technical Implementation
- Middleware: `TenantResolverMiddleware` extracts tenant context
- Repository: All queries include `WHERE tenant_id = :current_tenant`
- Cache: Keys formatted as `tenant:{id}:resource:{type}:{id}`

---

## 2. Advanced Authentication & Authorization

### Overview
Enterprise-grade authentication with JWT RS256, MFA support, and refresh token rotation.

### Requirements
- **FR2.1**: Password requirements: 12+ chars, complexity rules, HaveIBeenPwned check
- **FR2.2**: JWT RS256 with 15-min access tokens, 7-day refresh tokens
- **FR2.3**: Refresh token rotation with reuse detection
- **FR2.4**: Multi-factor authentication (TOTP)
- **FR2.5**: RBAC + permission-based authorization
- **FR2.6**: Resource-based access control

### User Stories
**As a** security-conscious user  
**I want** strong password requirements and MFA  
**So that** my account is protected from unauthorized access

**As a** system administrator  
**I want** automatic token rotation and reuse detection  
**So that** compromised tokens have limited impact

### Acceptance Criteria
- ✅ Passwords validated against HaveIBeenPwned API
- ✅ Argon2id hashing with secure parameters (memory_cost=65536)
- ✅ JWT contains user_id, tenant_id, roles, permissions
- ✅ Old refresh token revoked immediately on rotation
- ✅ Token family revoked if reuse detected
- ✅ MFA required for privileged operations (optional per tenant)

### Security Features
**Token Rotation Flow**:
1. Client sends refresh_token
2. Server validates token, checks revocation
3. Issues new access + refresh token pair
4. Revokes old refresh token
5. Links new token to family via parent_token_id

**Reuse Detection**:
- If revoked token presented → revoke entire token family
- Alert user of potential security breach
- Force re-authentication

### Roles & Permissions
| Role | Permissions |
|------|-------------|
| SYSTEM_ADMIN | Full system access |
| TENANT_ADMIN | Tenant-wide management |
| PROJECT_MANAGER | Project-level management, task assignment |
| MEMBER | Create/update own tasks, view assigned tasks |
| GUEST | Read-only access |

---

## 3. Task Management with CQRS

### Overview
Complete task lifecycle management using Command Query Responsibility Segregation pattern.

### Requirements
- **FR3.1**: Create, read, update, delete tasks
- **FR3.2**: Task assignment to users
- **FR3.3**: Status transitions with state machine validation
- **FR3.4**: Priority levels (LOW/MEDIUM/HIGH/CRITICAL)
- **FR3.5**: Comments and attachments
- **FR3.6**: Audit trail for all changes
- **FR3.7**: Task filtering and pagination
- **FR3.8**: Statistics and reporting

### User Stories
**As a** project manager  
**I want** to create and assign tasks to team members  
**So that** work is distributed and tracked efficiently

**As a** team member  
**I want** to update task status and add comments  
**So that** I can communicate progress and collaborate

**As a** auditor  
**I want** complete audit trail of task changes  
**So that** I can review compliance and accountability

### Acceptance Criteria
- ✅ Tasks have status workflow: TODO → IN_PROGRESS → IN_REVIEW → DONE
- ✅ Invalid status transitions rejected (e.g., DONE → TODO)
- ✅ Only authorized users can assign tasks
- ✅ Comments include author, timestamp, and content
- ✅ Audit log captures all CRUD operations with before/after data
- ✅ Soft delete preserves data for audit purposes

### Status State Machine
```
TODO ───────────> IN_PROGRESS ───────> IN_REVIEW ───────> DONE
  │                    │                    │
  └──> BLOCKED <───────┘                    │
           │                                │
           └────────────────────────────────┘
```

**Transition Rules**:
- TODO → IN_PROGRESS: Requires assignee
- IN_PROGRESS → IN_REVIEW: Requires completion criteria
- IN_REVIEW → DONE: Requires approval
- IN_REVIEW → IN_PROGRESS: Revisions needed
- * → BLOCKED: Requires blocked_reason
- * → CANCELLED: Admin only

### Commands
- `CreateTaskCommand`: Create new task
- `UpdateTaskCommand`: Modify task details
- `AssignTaskCommand`: Assign to user
- `ChangeTaskStatusCommand`: Update status
- `AddTaskCommentCommand`: Add comment
- `DeleteTaskCommand`: Soft delete

### Queries
- `GetTaskByIdQuery`: Fetch single task
- `GetUserTasksQuery`: User's assigned tasks (paginated)
- `GetTaskStatisticsQuery`: Dashboard metrics

### Domain Events
- `TaskCreated`: New task created
- `TaskUpdated`: Task modified
- `TaskAssigned`: Assignment changed
- `TaskStatusChanged`: Status transition
- `TaskDeleted`: Task soft-deleted
- `TaskCommentAdded`: New comment

### Performance Optimization
- Query caching with 1-minute TTL
- Eager loading for task + comments
- Composite indexes on (tenant_id, status, assigned_to)

---

## 4. Event-Driven Architecture

### Overview
Domain events for decoupled, auditable system behavior.

### Requirements
- **FR4.1**: All domain actions emit events
- **FR4.2**: Event handlers process asynchronously
- **FR4.3**: Event versioning for backward compatibility
- **FR4.4**: Outbox pattern for reliable event delivery

### Event Flow
1. Command handler executes business logic
2. Aggregate emits domain event
3. Event stored in outbox table (transactional)
4. Background worker polls outbox
5. Event dispatcher publishes to handlers
6. Handlers execute side effects (cache invalidation, notifications)

---

## Summary

These specifications provide:
- ✅ **Clear requirements** with acceptance criteria
- ✅ **User stories** for business context
- ✅ **Technical details** for implementation
- ✅ **Security considerations** throughout
- ✅ **Performance optimizations** identified


**Notes / current repo status:**
- The implementation uses `python-jose` for JWT handling (see `requirements.txt` and `app/shared/security/jwt.py`).
- The event dispatcher and handlers are implemented, but a dedicated outbox table and background polling worker are not included in the repository and are left as TODO for production cross-process delivery.
- The repository includes tenant models and repository code, but an HTTP router (`app/tenant/router.py`) exposing tenant management endpoints is not present and can be implemented if required.
