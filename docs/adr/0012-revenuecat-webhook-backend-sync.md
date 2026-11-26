# ADR 0012: RevenueCat Webhook Architecture and Subscription Sync

## STATUS: Accepted

## CONTEXT
The backend needs to reliably reflect mobile subscription state in order to authorize feature access and report the active plan. RevenueCat sends webhook events whenever a subscription state changes in the App Store or Play Store.

The repository already has an initial implementation at:
- `app/Http/Controllers/Api/V2/RevenueCatWebhookController.php`
- `app/Services/RevenueCatWebhookService.php`

## DECISION
We implement a robust webhook flow in the backend that captures, validates, logs, and processes RevenueCat events to keep the organization/user subscription state in sync.

1. Security and validation
 - `RevenueCatWebhookController` validates the webhook token against `services.revenuecat.webhook_secret`, accepting both `Bearer <secret>` and plain `<secret>` formats.
 - Only authorized requests are accepted, and the controller always returns `200` to prevent unwanted retries when a payload has already been processed or logged.

2. Event logging
 - Every webhook is persisted in `rc_webhook_logs` before any processing takes place.
 - The minimum fields logged are `event_type`, `app_user_id`, `product_id`, and `raw_payload`.

3. Job dispatching
 - The controller dispatches async jobs based on the event type:
   - `INITIAL_PURCHASE` and `RENEWAL` → `HandleRevenueCatPurchase`
   - `EXPIRATION` → `HandleRevenueCatExpiration`
 - This decouples webhook processing from the HTTP response time.

4. Sync logic
 - `RevenueCatWebhookService` resolves the user by matching `app_user_id` with `User::uuid`.
 - On purchase or renewal, it creates or updates the mobile subscription linked to the user's current organization.
 - The `entitlement` is read from `entitlement_ids[0]` (the first entitlement in the event payload) and mapped to an internal plan slug.
 - The `platform` field is set from the `store` value: `APP_STORE` → `ios`, `PLAY_STORE` → `android`, anything else → `stripe`.
 - Key subscription fields updated: `current_period_end`, `vencimiento`, `prorroga` (set to 3 days after expiration as a grace period), `rc_original_transaction_id`, `store_product_id`, and `rc_entitlement`.
 - On new subscriptions, a confirmation email is sent to the user via `ProSubscriptionConfirmedMail`.

5. Expiration handling
 - On an `EXPIRATION` event, if the organization has no active subscription record the handler returns early with no changes.
 - If a subscription does exist, it is downgraded to the free plan (resolved via `services.revenuecat.free_plan_slug`, defaulting to `plan-basico`) while keeping `estado = 'activa'`.
 - Unhandled event types are logged and marked as processed without blocking the webhook response.

## CONSEQUENCES
### PROS
 - Keeps the backend in sync with RevenueCat changes in real time.
 - Isolates webhook logic in a lightweight controller and a dedicated service.
 - Explicit logging in `RcWebhookLog` makes monitoring and debugging straightforward.
 - Supports multiple stores (App Store, Play Store) through a single integration.
 - The 3-day grace period on `prorroga` gives users a buffer when a renewal is delayed.

### CONS
 - Relies on RevenueCat's `app_user_id` matching `User::uuid` exactly — any mismatch breaks subscription linking.
 - Async processing introduces a small delay before subscription state is reflected in the system.
 - The `platform` default fallback of `stripe` for unknown store values may be confusing since RevenueCat doesn't process Stripe transactions.

## IMPLEMENTATION NOTES
- Ensure the `app_user_id` sent by RevenueCat matches the user's UUID in the system.
- Use separate jobs for purchases/renewals and expirations, as `RevenueCatWebhookController` already does.
- In `RevenueCatWebhookService`, keep the entitlement-to-plan mapping current; add a recovery path if the mapping fails.
- Log webhook errors and store the exception message in `RcWebhookLog` for audit purposes.
- Keep the `platform` column values as `ios`, `android`, and `stripe` to differentiate subscription origins.
- Consider a periodic reconciliation job to catch any state drift if webhooks are missed or fail silently.
