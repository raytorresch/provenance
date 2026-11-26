# Organization Based Multitenancy

## Status: Accepted

## Context:
The V1 system utilized direct relationships between users and resources (projects, lists), which prevented centralized billing, subscription management, and group-level permissioning. Roles were hardcoded as an id_tipo integer.

## Decision
- Organization Entity: Introduce an Organization model as the primary owner of all operational data.
- N:N Relationship: Users can belong to multiple organizations via an organization_user pivot table.
- Contextual Roles: Implement Spatie Roles & Permissions where a user's role is scoped to their active organization context.
- Data Isolation: Enforce isolation using Laravel Global Scopes (organization_id) to ensure users only access data from their active session context.

## Consequences:
- Positive: High scalability for SaaS, easy volume-based subscription management, and robust data privacy.
- Negative: Increased query complexity; administrative tasks require explicit use of withoutGlobalScope().
