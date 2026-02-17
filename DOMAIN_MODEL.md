# Event Flow & Domain Model

## Event-Driven Architecture Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Mediator
    participant Handler
    participant Domain
    participant Repository
    participant Events
    participant Cache

    Client->>API: POST /tasks
    API->>Mediator: send(CreateTaskCommand)
    Mediator->>Handler: CreateTaskHandler.handle()
    Handler->>Domain: TaskAggregate.create()
    Domain->>Events: emit(TaskCreated)
    Handler->>Repository: save(task)
    Repository->>Database: INSERT
    Events->>Cache: invalidate(tenant:tasks)
    Events->>AuditLog: log(TASK_CREATED)
    Handler->>API: TaskResponse
    API->>Client: 201 Created
```

## CQRS Pattern

```mermaid
graph LR
    Client[Client Request]
    Router[FastAPI Router]
    Mediator[Mediator]
    
    CmdHandler[Command Handler]
    QueryHandler[Query Handler]
    
    Domain[Domain Model]
    Repo[Write Repository]
    QueryRepo[Read Repository]
    
    Cache[Redis Cache]
    DB[(PostgreSQL)]
    
    Client --> Router
    Router --> Mediator
    
    Mediator --> CmdHandler
    Mediator --> QueryHandler
    
    CmdHandler --> Domain
    Domain --> Repo
    Repo --> DB
    
    QueryHandler --> Cache
    Cache -->|miss| QueryRepo
    QueryRepo --> DB
    DB --> Cache
```

## Multi-Tenant Request Flow

```mermaid
flowchart TD
    A[HTTP Request] --> B{Tenant Resolver}
    B -->|Subdomain| C[Extract from subdomain]
    B -->|Header| D[Extract X-Tenant-Id]
    B -->|JWT| E[Extract from token]
    
    C --> F[Set Context]
    D --> F
    E --> F
    
    F --> G{Valid Tenant?}
    G -->|No| H[401 Unauthorized]
    G -->|Yes| I[Auth Middleware]
    
    I --> J{Valid Token?}
    J -->|No| K[401 Unauthorized]
    J -->|Yes| L[Rate Limiter]
    
    L --> M{Within Limits?}
    M -->|No| N[429 Too Many Requests]
    M -->|Yes| O[Route Handler]
    
    O --> P[Apply tenant_id filter]
    P --> Q[Execute Query]
    Q --> R[Return Response]
```

## Domain Model Structure

```mermaid
classDiagram
    class TaskAggregate {
        +UUID id
        +UUID tenant_id
        +String title
        +TaskStatus status
        +create() Task
        +updateStatus(status) void
        +assign(user_id) void
        +addComment(content) void
        +emit_event(event) void
    }
    
    class Task {
        +UUID id
        +UUID project_id
        +String title
        +TaskStatus status
        +Priority priority
        +UUID assigned_to
    }
    
    class Comment {
        +UUID id
        +UUID task_id
        +UUID user_id
        +String content
    }
    
    class UserAggregate {
        +UUID id
        +UUID tenant_id
        +String email
        +Array roles
        +Array permissions
        +register() User
        +login() TokenPair
        +enableMFA() void
    }
    
    class TenantAggregate {
        +UUID id
        +String subdomain
        +SubscriptionPlan plan
        +create() Tenant
        +updateSettings(settings) void
    }
    
    TaskAggregate "1" --> "*" Task
    TaskAggregate "1" --> "*" Comment
    TenantAggregate "1" --> "*" Task
    TenantAggregate "1" --> "*" UserAggregate
    UserAggregate "1" --> "*" Task : creates
    UserAggregate "1" --> "*" Task : assigned_to
```

## Event Publishing Pattern

```mermaid
graph TD
    A[Command Execution] --> B[Domain Logic]
    B --> C[Emit Domain Event]
    C --> D[Store in Outbox]
    
    D --> E[Transaction Commit]
    E --> F[Background Worker]
    
    F --> G[Poll Outbox]
    G --> H[Publish Events]
    
    H --> I[Cache Invalidation Handler]
    H --> J[Audit Log Handler]
    H --> K[Notification Handler]
    
    I --> L[Redis]
    J --> M[(Database)]
    K --> N[Email/Webhook]
```

## Authorization Flow

```mermaid
flowchart TD
    A[Request with JWT] --> B{Extract Claims}
    B --> C[user_id]
    B --> D[tenant_id]
    B --> E[roles]
    B --> F[permissions]
    
    C --> G{Check Permission}
    D --> G
    E --> G
    F --> G
    
    G -->|Has Permission| H{Resource Access Check}
    G -->|No Permission| I[403 Forbidden]
    
    H -->|Is Owner| J[Allow]
    H -->|Same Department| K{Check Role}
    H -->|Other| L[Deny]
    
    K -->|Manager+| J
    K -->|Member| L
```

## Key Patterns Summary

### Aggregates
- **TenantAggregate**: Manages tenant lifecycle, settings, subscription
- **UserAggregate**: Handles authentication, authorization, profile
- **TaskAggregate**: Controls task lifecycle, status transitions, assignments

### Domain Events
- `TaskCreated`, `TaskUpdated`, `TaskStatusChanged`, `TaskAssigned`
- `UserRegistered`, `UserLoggedIn`, `PasswordChanged`, `MFAEnabled`
- `TenantCreated`, `TenantSettingsUpdated`

### Event Handlers
- **CacheInvalidationHandler**: Clears related cache entries
- **AuditLogHandler**: Records all changes for compliance
- **NotificationHandler**: Sends alerts (future feature)

### Repository Pattern
- Write operations through aggregate roots
- Read operations use optimized queries with caching
- Automatic tenant_id filtering at session level


**Notes / current repo status:**
- The architecture describes using an outbox pattern for reliable event delivery; the repo includes an event dispatcher and handlers but does not include a dedicated outbox table or background polling worker. Implementing the outbox table and worker is left as a TODO for cross-process delivery in production.
- Tenant domain models and repository code are implemented, but a tenant HTTP router (`app/tenant/router.py`) exposing tenant management endpoints is not present in the repository and can be added if needed.
