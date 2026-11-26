# Storage Visibility Public In Cloud Storage Services

## Status: Approved (TECHNICAL DEBT)

## Context:
The system stores plans (DWG), PDFs and construction photographs. Public visibility is currently used in the DigitalOcean Spaces 
driver.

## Decision:
Maintain public visibility for the initial V2 to ensure compatibility with the current mobile and web client, avoiding refactorings in image rendering and file download logic.

## Consequences:
- Risk: Files are accessible if the exact URL is known (although names now use UUIDs to mitigate brute force attacks).
- Security: The Least Privilege principle is not complied with.

## Mitigation:
Name sanitization with UUID and header inspection (MIME sniffing) was implemented to avoid script execution.

## Action Plan (V3):
Migrate to private visibility and use Signed URLs with expiration time of 10-15 minutes.
