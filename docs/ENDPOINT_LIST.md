# API Endpoints Index

This index lists available API endpoints and links to the per-app reference pages under `docs/endpoints/`.
For setup instructions (products, prices, local webhooks), see the [Stripe Setup Guide](STRIPE_SETUP.md).

### Accounts

- [POST /api/v1/accounts/register/](endpoints/accounts.md) — Register a new user (sends OTP email)
- [POST /api/v1/accounts/verify-email/](endpoints/accounts.md) — Verify email with OTP
- [POST /api/v1/accounts/login/](endpoints/accounts.md) — Obtain JWT access and refresh tokens
- [POST /api/v1/accounts/token/refresh/](endpoints/accounts.md) — Refresh JWT access token
- [POST /api/v1/accounts/logout/](endpoints/accounts.md) — Logout / revoke session (authenticated)
- [POST /api/v1/accounts/password-reset/](endpoints/accounts.md) — Send OTP to reset password
- [POST /api/v1/accounts/check-otp/](endpoints/accounts.md) — Validate an OTP
- [POST /api/v1/accounts/password-reset-confirm/](endpoints/accounts.md) — Confirm password reset with OTP
- [POST /api/v1/accounts/change-password/](endpoints/accounts.md) — Change password (authenticated)
- [GET  /api/v1/accounts/profile/](endpoints/accounts.md) — Get current user's profile (authenticated)
- [PATCH /api/v1/accounts/profile/update/](endpoints/accounts.md) — Partial update profile (authenticated)

---

### Main (Meditation Generation)

- [GET /api/v1/charecter-voice/](endpoints/main.md) — Retrieve active character voices
- [GET /api/v1/nature-sounds/](endpoints/main.md) — Retrieve active nature sounds
- [GET /api/v1/background-image/](endpoints/main.md) — Retrieve active background images
- [POST /api/v1/meditation/generate/](endpoints/main.md) — Generate a personalized meditation sequence
- [GET /api/v1/meditation/archive/](endpoints/main.md) — Retrieve the user's paginated meditation archive
- [GET /api/v1/meditation/\<id\>/](endpoints/main.md) — Retrieve a specific meditation by ID

---

### Finance (Subscriptions & Wallets)

- [GET  /api/v1/plans/](endpoints/finance.md) — List active subscription plans
- [GET  /api/v1/wallet/](endpoints/finance.md) — Get current user's wallet details (authenticated)
- [GET  /api/v1/subscription/](endpoints/finance.md) — Get active subscription details (authenticated)
- [POST /api/v1/subscription/checkout/](endpoints/finance.md) — Create Stripe Checkout Session (authenticated)
- [POST /api/v1/subscription/change/](endpoints/finance.md) — Change plan Upgrade/Downgrade (authenticated)
- [POST /api/v1/subscription/cancel/](endpoints/finance.md) — Cancel subscription at period end (authenticated)
- [POST /api/v1/webhooks/stripe/](endpoints/finance.md) — Stripe webhook listener

---

Add other apps here as their endpoint pages are created under `docs/endpoints/`.
