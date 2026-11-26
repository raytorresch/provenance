# Immutable Versioning and Marketplace

## Status: Accepted

## Context:
Checklists are legal compliance documents. In V1, editing a list retroactively changed historical reports, destroying audit integrity. Furthermore, there was no mechanism to sell "Premium" templates.

## Decision:
- Immutability: Rows in listas_chequeo are never updated. Any change triggers the creation of a new row with an incremented version number.
- Lineage: Use root_uuid to group all versions of a single list for history tracking.
- Marketplace (Cloning): Lists marked as is_master serve as prototypes. Upon purchase, the system clones the structure into the buyer's organization_id.
- Temporal Validity: Use valid_from and valid_until to determine the official version at any specific point in time.

## Consequences:
- Positive: Perfect audit trails and protection of intellectual property for sold templates.
- Negative: Database row volume increases; storage/update logic requires strict DB::transaction management.
