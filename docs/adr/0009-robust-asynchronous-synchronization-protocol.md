# ADR 0009: Robust Asynchronous Synchronization Protocol (V2)

## STATUS: Accepted (Implementation Phase)

## CONTEXT
The legacy synchronization system (V1) relies on a monolithic JSON payload containing Base64-encoded images. This architecture results in payloads exceeding 20MB, leading to frequent timeouts, memory exhaustion, and data corruption in the mobile local database. Furthermore, the lack of a tracking mechanism makes it impossible to verify if a sync was partially successful, forcing the mobile client to either "assume success" or "retry everything," creating duplicates and inconsistencies.

## DECISION
We will implement a Decoupled Asynchronous Sync Protocol based on a "Puzzle of UUIDs" architecture. The core principles are:

1. Separation of Concerns (Binaries vs. Metadata)
    - Binaries (Photos/Docs): Will be uploaded individually or in small batches to specialized endpoints before or during the metadata sync.
    - Metadata (JSON): The sync manifest will only contain UUID references to these files.

2. State-Based Asset Reconciliation
The server will handle assets through a three-state machine to allow non-sequential arrivals:
    - ORPHAN: Binary arrives before the JSON metadata. It is stored and registered with a null parent reference.
    - PENDING_BINARY: JSON arrives before the binary. The record is created with metadata (comments, classification) but marked as "Processing."
    - AVAILABLE: Match is found via photo_uuid. The record is linked and activated.

3. Sync Sessions & Manifests
Every synchronization attempt must be wrapped in a SyncSession.
- The Manifest: The mobile client sends a list of intended UUIDs to be synced.
- Tracking: The server records processed_uuids and failed_uuids.
- Integrity Check: A final "Check-sum" comparison ensures the server received exactly what the manifest promised.

4. Strict Idempotency & Side-Effect Guarding
- Use updateOrCreate for all data persistence.
- Event Guarding: Business logic (notifications, visit counters) must only trigger the first time a UUID is successfully transitioned to a "Completed" state to prevent duplicate alerts during retries.

## CONSEQUENCES
### PROS
- Payload Efficiency: JSON size is reduced by ~95% by removing Base64 strings.
- Resilience: Failures in large binary uploads do not block the synchronization of critical site data (Minutes, Checklists).
- Granular Recovery: Mobile can query the SyncSession to identify exactly which records failed and only retry those in the next rafaga.
- No Local Corruption: Clear "Success" confirmation at the UUID level prevents the mobile DB from getting stuck in an inconsistent state.

### CONS
- Increased Backend Complexity: Requires background workers (Jobs) to periodically clean "Orphan" files and reconcile states.
- UI Placeholders: The web/mobile interfaces must handle "Pending" states (e.g., showing a loading spinner for an image that is still being uploaded).

## IMPLEMENTATION GUIDELINES (FOR MOBILE REFACTOR)
1. UUID Pre-generation: Mobile must generate all UUIDs (Reports, Photos, Minutes) at the moment of creation in offline mode.
2. Background Uploader: Implement a background service to upload binaries (Multipart) as soon as a connection is detected, independent of the main Sync button.
3. Delta Sync: Mobile should only include records marked as needs_sync in the manifest.
4. Session Polling: After sending a sync payload, the mobile app should poll GET /v2/sync/{uuid} to confirm which items to mark as "Synced" in the local SQLite/Room/Hive database.
