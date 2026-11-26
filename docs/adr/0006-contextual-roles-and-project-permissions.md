# Contextual Roles and Project Permissions

## Status: Accepted

## Context:
In V1, roles were rigid integers. In V2, a user can have multiple "identities" (e.g., Admin in Org A, but only a Supervisor in Project 1 within Org B). We need to decouple organizational hierarchy from operational project duties without creating database debt or complex migrations.

## Decision:
1. Organizational Roles (Spatie): Use Spatie Roles strictly for Organization-level management (admin, member, collaborator). These are synced dynamically by the Middleware based on the organization_id header.

2. Operational Permissions (Project Level): Project-specific roles (Supervisor, Constructor, Client) found in the project_user table will be treated as Permission Sets.

3. Middleware Injection: The Multitenancy Middleware will not only scope data but also "hydrate" the User object with the correct Spatie roles and a cached list of project-level permissions for the active session.

4. Granular Overrides: Support a CRUD where an Admin can assign specific permissions to a user, overriding their default role capabilities (using Spatie's hasDirectPermission).

## Consequences:
- Positive: Maximum flexibility. Supports "Guest" or "Consultant" scenarios easily. Policies remain clean using @can.
- Negative: Requires a more sophisticated Middleware and a robust UI for the Admin to manage these granular permissions.
