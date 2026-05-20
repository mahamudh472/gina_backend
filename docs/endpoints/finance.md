# Finance Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- `GET /api/v1/plans/`
- `GET /api/v1/wallet/`
- `GET /api/v1/subscription/`
- `POST /api/v1/subscription/checkout/`
- `POST /api/v1/subscription/change/`
- `POST /api/v1/subscription/cancel/`
- `POST /api/v1/webhooks/stripe/`

---

## `GET /api/v1/plans/`

### Description

List all active subscription plans including price, currency, credit allowance, badges, and feature checklists.

### Auth

- `Not required`

### Request Payload Reference

None.

### Response Payload Reference

Success example:

```json
[
  {
    "id": 1,
    "name": "Basic",
    "slug": "basic",
    "price": "9.90",
    "currency": "eur",
    "credit_amount": 1,
    "interval": "month",
    "badge": "EINSTEIGER",
    "top_badge": null,
    "features": [
      "Individualisierte Deep Meditation",
      "Stimme frei wählbar (w / m)",
      "Themenspezifische binaurale Musik",
      "Dauerhafte Portalnutzung",
      "Volle Mixersteuerung",
      "Automatische Archiv- Speicherung"
    ],
    "is_active": true
  },
  {
    "id": 2,
    "name": "Core",
    "slug": "core",
    "price": "29.90",
    "currency": "eur",
    "credit_amount": 3,
    "interval": "month",
    "badge": "EMPFEHLUNG",
    "top_badge": "MEISTGEWÄHLT",
    "features": [
      "Individualisierte Deep Meditation",
      "Stimme frei wählbar (w / m)",
      "Themenspezifische binaurale Musik",
      "Dauerhafte Portalnutzung",
      "Volle Mixersteuerung",
      "Automatische Archiv- Speicherung"
    ],
    "is_active": true
  },
  {
    "id": 3,
    "name": "Pro",
    "slug": "pro",
    "price": "89.90",
    "currency": "eur",
    "credit_amount": 10,
    "interval": "month",
    "badge": "BUSINESS",
    "top_badge": null,
    "features": [
      "Individualisierte Deep Meditation",
      "Stimme frei wählbar (w / m)",
      "Themenspezifische binaurale Musik",
      "Dauerhafte Portalnutzung",
      "Volle Mixersteuerung",
      "Automatische Archiv- Speicherung"
    ],
    "is_active": true
  }
]
```

### Related Tests

- `apps/finance/tests.py`

---

## `GET /api/v1/wallet/`

### Description

Retrieve the current authenticated user's credit wallet balance.

### Auth

- `Required`

### Request Payload Reference

None.

### Response Payload Reference

Success example:

```json
{
  "balance": 3,
  "last_reset_at": "2026-05-20T03:16:12Z",
  "updated_at": "2026-05-20T03:16:12Z"
}
```

### Related Tests

- `apps/finance/tests.py`

---

## `GET /api/v1/subscription/`

### Description

Retrieve the active subscription details for the authenticated user.

### Auth

- `Required`

### Request Payload Reference

None.

### Response Payload Reference

Success example (Active subscription):

```json
{
  "id": 1,
  "plan": {
    "id": 2,
    "name": "Core",
    "slug": "core",
    "price": "29.90",
    "currency": "eur",
    "credit_amount": 3,
    "interval": "month",
    "badge": "EMPFEHLUNG",
    "top_badge": "MEISTGEWÄHLT",
    "features": [
      "Individualisierte Deep Meditation",
      "Stimme frei wählbar (w / m)",
      "Themenspezifische binaurale Musik",
      "Dauerhafte Portalnutzung",
      "Volle Mixersteuerung",
      "Automatische Archiv- Speicherung"
    ],
    "is_active": true
  },
  "status": "active",
  "current_period_start": "2026-05-20T03:00:00Z",
  "current_period_end": "2026-06-20T03:00:00Z",
  "cancel_at_period_end": false,
  "pending_plan": null
}
```

Error example (No active subscription):

```json
{
  "detail": "No subscription found for this user."
}
```

### Related Tests

- `apps/finance/tests.py`

---

## `POST /api/v1/subscription/checkout/`

### Description

Create a Stripe Checkout Session to initiate subscription setup.

### Auth

- `Required`

### Request Payload Reference

Only `plan_slug` is required. The redirect URLs (`success_url` and `cancel_url`) are automatically configured on the backend using the `FRONTEND_URL` setting.

```json
{
  "plan_slug": "core"
}
```

### Response Payload Reference

Success example:

```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_test_a1b2c3d4..."
}
```

Error example:

```json
{
  "plan_slug": [
    "This field is required."
  ]
}
```

### Related Tests

- `apps/finance/tests.py`

---

## `POST /api/v1/subscription/change/`

### Description

Request an immediate upgrade or scheduled downgrade of the current plan.

### Auth

- `Required`

### Request Payload Reference

```json
{
  "plan_slug": "pro"
}
```

### Response Payload Reference

Success example (Immediate Upgrade):

```json
{
  "message": "Plan change initiated successfully. Action: upgrade",
  "action": "upgrade",
  "subscription": {
    "id": 1,
    "plan": {
      "id": 3,
      "name": "Pro",
      "slug": "pro",
      "price": "89.90",
      "currency": "eur",
      "credit_amount": 10,
      "interval": "month",
      "badge": "BUSINESS",
      "top_badge": null,
      "features": [
        "Individualisierte Deep Meditation",
        "Stimme frei wählbar (w / m)",
        "Themenspezifische binaurale Musik",
        "Dauerhafte Portalnutzung",
        "Volle Mixersteuerung",
        "Automatische Archiv- Speicherung"
      ],
      "is_active": true
    },
    "status": "active",
    "current_period_start": "2026-05-20T03:00:00Z",
    "current_period_end": "2026-06-20T03:00:00Z",
    "cancel_at_period_end": false,
    "pending_plan": null
  }
}
```

Success example (Scheduled Downgrade):

```json
{
  "message": "Plan change initiated successfully. Action: downgrade",
  "action": "downgrade",
  "subscription": {
    "id": 1,
    "plan": {
      "id": 3,
      "name": "Pro",
      "slug": "pro",
      "price": "89.90",
      "currency": "eur",
      "credit_amount": 10,
      "interval": "month",
      "badge": "BUSINESS",
      "top_badge": null,
      "features": [
        "Individualisierte Deep Meditation",
        "Stimme frei wählbar (w / m)",
        "Themenspezifische binaurale Musik",
        "Dauerhafte Portalnutzung",
        "Volle Mixersteuerung",
        "Automatische Archiv- Speicherung"
      ],
      "is_active": true
    },
    "status": "active",
    "current_period_start": "2026-05-20T03:00:00Z",
    "current_period_end": "2026-06-20T03:00:00Z",
    "cancel_at_period_end": false,
    "pending_plan": {
      "id": 2,
      "name": "Core",
      "slug": "core",
      "price": "29.90",
      "currency": "eur",
      "credit_amount": 3,
      "interval": "month",
      "badge": "EMPFEHLUNG",
      "top_badge": "MEISTGEWÄHLT",
      "features": [
        "Individualisierte Deep Meditation",
        "Stimme frei wählbar (w / m)",
        "Themenspezifische binaurale Musik",
        "Dauerhafte Portalnutzung",
        "Volle Mixersteuerung",
        "Automatische Archiv- Speicherung"
      ],
      "is_active": true
    }
  }
}
```

### Related Tests

- `apps/finance/tests.py`

---

## `POST /api/v1/subscription/cancel/`

### Description

Cancel subscription at the end of the billing period.

### Auth

- `Required`

### Request Payload Reference

None.

### Response Payload Reference

Success example:

```json
{
  "message": "Subscription will be canceled at the end of the billing period.",
  "subscription": {
    "id": 1,
    "plan": {
      "id": 2,
      "name": "Core",
      "slug": "core",
      "price": "29.90",
      "currency": "eur",
      "credit_amount": 3,
      "interval": "month",
      "badge": "EMPFEHLUNG",
      "top_badge": "MEISTGEWÄHLT",
      "features": [
        "Individualisierte Deep Meditation",
        "Stimme frei wählbar (w / m)",
        "Themenspezifische binaurale Musik",
        "Dauerhafte Portalnutzung",
        "Volle Mixersteuerung",
        "Automatische Archiv- Speicherung"
      ],
      "is_active": true
    },
    "status": "active",
    "current_period_start": "2026-05-20T03:00:00Z",
    "current_period_end": "2026-06-20T03:00:00Z",
    "cancel_at_period_end": true,
    "pending_plan": null
  }
}
```

### Related Tests

- `apps/finance/tests.py`

---

## `POST /api/v1/webhooks/stripe/`

### Description

Webhook receiver for Stripe billing/subscription updates (`checkout.session.completed`, `invoice.paid`, `customer.subscription.updated`, `customer.subscription.deleted`).

### Auth

- `Not required` (Validated via Stripe signature header `Stripe-Signature`)

### Request Payload Reference

Pass Stripe-generated JSON payloads.

### Response Payload Reference

Success example:

```json
{
  "status": "success"
}
```

### Related Tests

- `apps/finance/tests.py`
