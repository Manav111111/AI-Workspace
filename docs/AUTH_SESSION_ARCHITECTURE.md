# AVTAAR — AUTHENTICATION, TENANT ISOLATION & SESSION ARCHITECTURE

## 1. Authentication Core Invariant
**AI Employees and Company Resources belong to PostgreSQL tenants, NOT browser JWT state.**

When an access token expires or the user refreshes their browser:
- AI Employees are **never deleted or lost**.
- Companies and Knowledge Bases remain safely stored in PostgreSQL.
- Re-authenticating restores full access to the existing company and all associated AI Employees.

---

## 2. Entity Hierarchy & Relationship Model

```
User (id, email, hashed_password)
  │
  └─── Membership (user_id, company_id, role: OWNER | ADMIN | MEMBER)
         │
         └─── Company / Tenant (id, name, plan, monthly_budget)
                │
                ├─── AI Employees (id, company_id, name, role, system_prompt, status)
                │      ├─── Assigned Knowledge Bases
                │      └─── Assigned Agent Tools
                │
                ├─── Knowledge Bases (id, company_id, name, qdrant_collection)
                │      └─── Documents & Chunks
                │
                ├─── Conversations & Messages (id, company_id, ai_employee_id)
                │
                ├─── Playground Sessions (id, company_id, ai_employee_id)
                │
                └─── Evaluation Runs & Usage Ledgers (id, company_id)
```

---

## 3. Authentication & Token Lifecycle

### Signup Flow
1. User provides `email`, `password`, `full_name`, and `company_name`.
2. Backend generates a cryptographically secure `bcrypt` hash with salt.
3. In a single atomic database transaction:
   - Creates `User` record.
   - Creates `Company` tenant record.
   - Creates `Membership` with `OWNER` role.
   - Creates initial default AI Employee (DRAFT status).
4. Issues HS256 JWT access token containing `sub: user_id`, `company_id`, and `role`.

### Login Flow
1. User submits `email` and `password`.
2. Backend queries `User` table and verifies password hash using `pwd_context.verify(password, user.hashed_password)`.
3. Resolves user's active `Company` and `MembershipRole`.
4. Returns JWT token, user profile, and list of associated companies.

### Environment Consistency Verification
To prevent environment mismatches (e.g. signup hitting Local SQLite while login queries Render PostgreSQL):
- `NEXT_PUBLIC_API_URL` on frontend must point to the identical backend deployment.
- `DATABASE_URL` on backend must connect to the same PostgreSQL database cluster for all replicas.

---

## 4. Multi-Tenant Authorization Dependency (`TenantContext`)
All protected API endpoints require the FastAPI dependency `get_tenant_context`:

```python
class TenantContext:
    user_id: uuid.UUID
    company_id: uuid.UUID
    role: MembershipRole
    user: User
    company: Company
```

Every service method takes `company_id` as an explicit parameter and filters SQL/Qdrant queries accordingly. Direct browser manipulation of tenant IDs is rejected because tenant context is derived server-side from the validated JWT claims and database membership checks.
