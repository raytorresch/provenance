# ADR 0010: Referential Integrity via Late Binding in Asynchronous Batches

## STATUS: Accepted (Implementation Phase)

## CONTEXT
In the V2 Asynchronous Synchronization Protocol, metadata is processed via Laravel Batches where multiple Jobs (Projects, Reports, Meetings) run in parallel. This concurrency introduces a race condition: a "Child" record (e.g., a Photo Report) may be processed by a worker before its "Parent" record (e.g., a Project/Obra) has been persisted in the database.

Since the database enforces Foreign Key constraints (or the business logic requires an id_obra), the Child job would normally fail, leading to an inconsistent state where reports exist on the mobile device but are rejected by the server due to a "missing parent."

## DECISION
We will implement a Late Binding Strategy (Delayed Reconciliation) to handle non-sequential data arrival within a synchronization session.

1. UUID-Based Lookup
 - Jobs will always use the mobile-generated uuid to identify relationships instead of auto-incremental IDs during the synchronization phase.

2. Job Release Mechanism (Backoff)
 - If a Child job starts processing and the Parent record is not yet found in the database, the Job will not be marked as "Failed."
 - Instead, the Job will be released back to the queue using $this->release($seconds).
 - This allows the "Parent" job, which is likely already in the queue or in mid-transaction, time to complete its persistence.

3. Retry Limit & Circuit Breaking
 - A maximum number of retries will be defined (e.g., public $tries = 5).
 - If the Parent record is still missing after all retries, the Job will finally transition to a "Failed" state, and the error will be logged in the SyncSession as a "Missing Dependency Error."

## CONSEQUENCES
### PROS
 - Temporal Decoupling: Jobs can be dispatched in any order, and the system will self-correct over time (Eventual Consistency).
 - Reduced Failures: Eliminates 99% of "Foreign Key Not Found" errors caused by worker latency.
 - No Schema Changes: Avoids making relational columns nullable just to satisfy a temporary synchronization state, preserving long-term data integrity.

### CONS
 - Queue Overhead: Releasing jobs back to the queue increases the number of total executions and adds a slight load to the queue driver (Redis/Database).
 - Processing Latency: Final synchronization status might take a few extra seconds to reach "Completed" while dependencies are resolved.

## IMPLEMENTATION NOTES
- Implementation: Within the handle() method of dependent Jobs:

``` php
$parent = Project::where('uuid', $data['project_uuid'])->first();
if (!$parent) {
    return $this->release(now()->addSeconds(15));
}
```

- Monitoring: The SyncSessionService must be able to report when a record is in a "Retrying/Waiting" state to differentiate from a hard validation failure.
