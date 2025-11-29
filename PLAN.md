# Objectives
- Build a Django app with email-verified registration, login, and password reset; admins can disable accounts.
- Support user types `basic` and `pro` with differing purchase pricing (pro gets 20% discount).
- Add Stripe-powered subscriptions and one-off product purchases.
- Import categories/products from `https://ousa-food.vercel.app/api/products` into SQLite.

# Architecture & Approach
- Apps: `accounts` (custom user + auth flows), `catalog` (products/categories + importer), `billing` (Stripe integration), `core` (common utilities/settings).
- Data models:
  - User: extends Django user with `user_type` (`basic`/`pro`) and `is_disabled` flag; track email verification status.
  - Category/Product: fields mapped to the upstream API; keep source IDs to support idempotent imports.
  - Subscription: `user`, `stripe_customer_id`, `stripe_subscription_id`, status, current period, plan metadata.
  - Purchase/Order: records Stripe payment intent/checkout session, amount charged, discount applied.
- Auth flows:
  - Registration issues a signed verification link emailed to the user; account activates upon confirmation.
  - Login blocked if `is_disabled` or unverified (configurable grace period).
  - Forgot-password uses Django’s reset flow with email templates.
- Product import: management command fetches the API, upserts categories/products, and logs changes; validate schema and handle failures with retries.
- Billing:
  - Use Stripe Checkout Sessions for subscriptions and product purchases; determine final amount client-side or server-side based on user type (apply 20% discount for `pro`).
  - Webhooks update subscription status and record completed purchases; verify signatures and queue async processing if needed.
- Settings/ops: load Stripe keys and email settings from env vars; use console email backend for local dev; isolate secrets via `.env`.

# User Journeys
- Register → receive verification email → confirm → login.
- Forgot password → email link → reset.
- Admin disables user → logins blocked until re-enabled.
- Subscribe via Stripe → webhook activates subscription on success.
- Browse products → purchase; pro pricing applies automatically.

# Testing & QA
- Unit tests for auth (verification, disabled users), discount calculations, and importer idempotency.
- Integration tests for Stripe webhook handling (mocked) and product import flow.
