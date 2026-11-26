# ADR 0011: Paywall Integration Strategy — Stripe for Web, RevenueCat for Mobile

## STATUS: Accepted

## CONTEXT
The platform offers subscription and in-app purchase experiences across web, Android, and iOS. On the web side, Stripe is already the established payment solution and handles direct billing and subscription management well. On mobile, the App Store and Play Store policies require that any in-app purchases for digital content or subscriptions go through each platform's native purchase system.

RevenueCat provides an abstraction layer for mobile in-app subscriptions and purchases, handling receipt validation, renewals, subscription state, and cross-platform consistency between App Store and Play Store. This simplifies mobile paywall integration considerably and removes the need to maintain two separate native subscription systems.

## DECISION
We adopt a split paywall architecture based on the channel:

1. Web
 - Stripe handles all web purchases and subscriptions.
 - The web paywall integrates directly with Stripe Checkout or the Stripe Subscriptions API.
 - Pricing logic, customer management, and recurring billing on the web are all owned by Stripe.

2. Mobile (Android and iOS)
 - RevenueCat handles all in-app subscriptions and purchases.
 - App Store and Play Store products are configured as product sources in RevenueCat.
 - Mobile apps use the RevenueCat SDK to present paywalls, trigger purchases, and check subscription state.

3. Data and sync
 - The central backend continues to own user state, content access, and subscription metadata.
 - RevenueCat syncs with the backend via webhooks or verification endpoints to keep mobile subscription state up to date.
 - Stripe and RevenueCat are treated as separate sources of truth: Stripe for web, RevenueCat for mobile.

## CONSEQUENCES
### PROS
 - Complies with Google and Apple policies for in-app purchases on mobile.
 - Reduces mobile complexity by delegating receipt validation and renewals to RevenueCat.
 - Clear separation: web uses Stripe and mobile uses RevenueCat, with no unnecessary cross-dependencies.
 - A single RevenueCat layer covers both App Store and Play Store, eliminating duplicated native logic.

### CONS
 - Two payment systems running in parallel: Stripe + RevenueCat.
 - May require additional backend mapping to link web and mobile products to the same commercial plans.
 - Pricing and promotional offers need to be coordinated across two independent systems.

## IMPLEMENTATION NOTES
- On mobile, define products in RevenueCat for App Store and Play Store using consistent product identifiers.
- Use the official RevenueCat SDK for iOS and Android, and handle purchase events in onboarding and renewal flows.
- The backend should expose endpoints that mobile apps can call to verify the current subscription state and validate feature access.
- RevenueCat sends webhooks to the backend whenever a subscriber's state changes (purchase, renewal, cancellation, refund).
- On web, continue using Stripe Checkout and the Customer Portal as appropriate, without mixing in mobile purchase flows.
- For analytics and reporting, centralize subscription events in the backend and tag the source: `stripe` vs `revenuecat`.

## NOTES
- This doesn't rule out different promotional offers across web and mobile, but it does establish that mobile technical integration happens exclusively through RevenueCat.
- This approach covers both Play Store and App Store, taking advantage of RevenueCat's ability to support multiple stores under a single product schema.
