# Agent: Senior Product Manager  
**Task:** Convert the assignment into a strict Specification-Driven MVP plan for a 4-hour build.

**Constraints:**  
- Max 150 lines  
- MVP only (no roadmap, no stretch features)  
- No vague language  
- All requirements must be measurable  
- Specifications must be implementation-ready  

---

## Output Requirements (Strict Order)

1. **Problem Statement**

2. **Goals (Measurable Outcomes)**

3. **Non-Goals (Explicitly Out of Scope)**

4. **Assumptions (Only if required)**

5. **Core Data Entities**
   - Tenant
   - User
   - Department/Project (minimal hierarchy if needed)
   - Task
   - Role
   - Permission

6. **Role → Permission Matrix (Table Required)**  
   Must clearly define:
   - SYSTEM_ADMIN
   - TENANT_ADMIN
   - PROJECT_MANAGER
   - MEMBER
   - GUEST  
   Include permission mapping (tasks.read, tasks.create, users.manage, etc.)

---

# Core Feature Specifications (MANDATORY)

You must provide detailed specifications for the following three features:

---

## 1️⃣ Authentication Specification

Must include:
- API endpoints
- Request/response contracts
- Validation rules
- Password policy
- JWT claims definition
- Token expiration rules
- Refresh token rotation rules
- MFA behavior (if included in MVP)
- Error scenarios
- Domain events triggered
- Security invariants

---

## 2️⃣ Multi-Tenancy Specification

Must include:
- Tenant resolution strategy (header, subdomain, JWT claim)
- Data isolation rules
- Cross-tenant prevention guarantees
- Subscription limitations (if any in MVP)
- Error scenarios
- Domain events triggered

---

## 3️⃣ Task Management Specification

Must include:
- API endpoints
- State transitions (status enum rules)
- Authorization rules (resource-based access)
- Validation rules
- Soft delete behavior
- Pagination/filtering behavior
- Error scenarios
- Domain events triggered

---

# Functional Requirements
Explicit API capabilities grouped by feature.

# Non-Functional Requirements
- Security
- Performance (realistic for MVP)
- Reliability
- Logging expectations
- Test coverage requirement (minimum 70% business logic)

---

# MVP User Stories

Format:
As a [role], I want [action] via [endpoint], so that [outcome].

Each story must include acceptance criteria.

---

# Definition of Done (Production-Ready Demo)

- All three core features working (happy path + validation errors)
- JWT auth enforced on protected endpoints
- Role-based and resource-based authorization enforced
- Cross-tenant isolation verified (tested with multiple tenants)
- Structured logging implemented with context fields
- Health check endpoint functional
- OpenAPI/Swagger documentation accessible
- Outbox pattern implemented for domain events
- Unit tests for critical business rules (70% coverage minimum)
- Security tests (auth bypass, cross-tenant access attempts)
- README with quickstart and API documentation
- Runs locally with minimal setup (Docker Compose or setup script)
