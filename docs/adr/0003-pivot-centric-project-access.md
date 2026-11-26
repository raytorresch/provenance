# Pivot Centric Project Access

## Status: Accepted

## Context:
In V1, project ownership was limited by columns like id_admin or id_constructor. This prevented multiple supervisors or multiple companies from collaborating on a single project.

## Decision:
- Unified Pivot: Use a project_user pivot table containing the user_id, project_id, and role.
- De-normalization Removal: Deprecate specific user-type columns in the obras table.
- Dynamic Assignment: Access is determined by the presence of a record in the pivot, allowing for flexible team structures.

## Consequences:
- Positive: Supports complex project structures where multiple stakeholders from different roles collaborate.
- Negative: Requires more complex joins to list projects by role.
