# Offline-First Sequencing and Immutability

## Status: Accepted

## Context:
Users in construction sites often lack stable internet. Reports are often uploaded in batches with past timestamps, which could break the logical sequence of an audit if relying on auto-incrementing IDs.

## Decision:
- Client-Side UUIDs: The frontend generates UUIDs to prevent duplicates (idempotency) during retry attempts.
- Logical Sequencing: Allow insertions with backdated timestamps but assign a correlativo (sequence number) based on the organization's report history to maintain an immutable order.
- Dynamic Classification: Introduce clasificacion_id to allow organizations to categorize reports dynamically without altering the core database structure.

## Consequences:
- Positive: Reliable offline synchronization and forensic-grade audit logs.
- Negative: Logic for calculating sequences must be robust against race conditions.
