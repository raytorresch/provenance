# Unified Identity and Social Auth

## Status: Approved

## Context:
The V1 system had insecure "hacks" for social login (empty passwords) and lacked multi-device support. We need a professional way to handle native (email/pass) and social (Google/Apple) identities while maintaining high security and supporting our Multitenancy architecture.

## Decision:
1. Firebase as Identity Proxy: Use Firebase Admin SDK to verify idTokens sent by the frontend. This offloads the complexity of rotating public keys from Google/Apple to a trusted provider.

2. Dependency Injection: Register the Firebase SDK as a Singleton in the Laravel Service Container via AppServiceProvider for clean, testable code.

3. Password Safety: Users registered via social providers will have a null password in the database. Native login attempts on these accounts will be blocked to prevent unauthorized access.

4. Device Tracking: Introduce a user_devices table to support multiple active sessions and unique FCM tokens per hardware ID (device_id).

5. Contextual Resource: All successful auth attempts must return a UserContextResource containing the active organization, roles, and injected permissions.

## Consequences:

- Positive: High security (no more empty passwords), reliable identity verification, and a "ready-to-use" context for the Frontend.

- Negative: Dependency on Firebase Admin SDK; requires a secure Service Account JSON file managed outside of Version Control.
