# Asynchronous PDF Generation

## Status: Accepted

## Context:
Generating complex PDFs (with high-res photos or long checklists) in real-time causes timeouts and degrades server performance.

## Decision:
- Queue-Based Processing: Use a reports_export table to track requests and dispatch GenerateReportJob to background workers.
- Status Polling: The frontend polls for the status (pending, processing, completed) via a UUID.
- Storage Service: Binary PDF data is moved to cloud storage (StorageService), and the user is provided with a temporary signed URL.

## Consequences:
- Positive: Improved UX; the server remains responsive regardless of report size.
- Negative: Requires a worker process (Redis/Database queue) to be running.
