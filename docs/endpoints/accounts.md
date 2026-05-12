# Accounts Endpoints

Back to index: [ENDPOINT_LIST.md](../ENDPOINT_LIST.md)

## Endpoint Inventory

- POST `/api/v1/accounts/login/`
- POST `/api/v1/accounts/logout/`
- POST `/api/v1/accounts/token/refresh/`
- POST `/api/v1/accounts/register/`
- POST `/api/v1/accounts/verify-email/`
- POST `/api/v1/accounts/password-reset/`
- POST `/api/v1/accounts/check-otp/`
- POST `/api/v1/accounts/password-reset-confirm/`
- POST `/api/v1/accounts/change-password/`
- GET  `/api/v1/accounts/profile/`
- PATCH `/api/v1/accounts/profile/update/`

---

## POST /api/v1/accounts/register/

Description: Create a new user account and send a verification OTP to email.

Auth: Not required

Request JSON:

```json
{
  "email": "jane@example.com",
  "password": "strongpassword",
  "full_name": "Jane Example"
}
```

Success response (200):

```json
{ "message": "Otp sent to your email" }
```

Notes: The created user is set `is_active = False` until email verification.

---

## POST /api/v1/accounts/verify-email/

Description: Verify user email using OTP sent during registration.

Auth: Not required

Request JSON:

```json
{
  "email": "jane@example.com",
  "otp": "123456"
}
```

Success response (200):

```json
{ "message": "Email jane@example.com successfully verified" }
```

Error responses:

- 400: Invalid OTP
```json
{ "error": "OTP is expired or already used" }
```
- 404: No user found
```json
{ "error": "User not found" }
```

---

## POST /api/v1/accounts/login/

Description: Obtain JWT `access` and `refresh` tokens.

Auth: Not required

Request JSON:

```json
{
  "email": "jane@example.com",
  "password": "strongpassword"
}
```

Success response (200):

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

Error examples:

- 401 / 400: Invalid credentials
```json
{ "detail": "No active account found with the given credentials" }
```
- 400 when account not active (OTP sent):
```json
{
  "detail": "Account is not active. An OTP has been sent to your email for verification.",
  "code": "EMAIL_NOT_VERIFIED"
}
```

Curl example:

```bash
curl -X POST https://api.example.com/api/v1/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"jane@example.com","password":"strongpassword"}'
```

---

## POST /api/v1/accounts/token/refresh/

Description: Exchange `refresh` token for a new `access` token.

Auth: Not required (uses refresh token body)

Request JSON:

```json
{ "refresh": "<refresh_token>" }
```

Success response (200):

```json
{ "access": "<new_access_token>" }
```

---

## POST /api/v1/accounts/logout/

Description: Logout / revoke session tokens (implementation-specific).

Auth: Required (Bearer access token)

Header:

- `Authorization: Bearer <access_token>`

Success response (205):

```json
{ "message": "Successfully logged out" }
```

---

## POST /api/v1/accounts/password-reset/

Description: Send an OTP to the user's email to start password reset.

Auth: Not required

Request JSON:

```json
{ "email": "jane@example.com" }
```

Success (200):

```json
{ "message": "OTP sent to your email" }
```

Errors:

```json
{ "error": "User with this email does not exist" }
```

---

## POST /api/v1/accounts/check-otp/

Description: Validate an OTP without taking action.

Auth: Not required

Request JSON:

```json
{ "email": "jane@example.com", "otp": "123456" }
```

Success (200):

```json
{ "message": "OTP is valid" }
```

Error (400):

```json
{ "error": "OTP is invalid or expired" }
```

---

## POST /api/v1/accounts/password-reset-confirm/

Description: Confirm password reset using OTP and set a new password.

Auth: Not required

Request JSON:

```json
{
  "email": "jane@example.com",
  "otp": "123456",
  "new_password": "newstrongpassword"
}
```

Success (200):

```json
{ "message": "Password for jane@example.com successfully reset" }
```

---

## POST /api/v1/accounts/change-password/

Description: Change the current authenticated user's password.

Auth: Required

Header:

- `Authorization: Bearer <access_token>`

Request JSON:

```json
{
  "old_password": "currentpass",
  "new_password": "newpass",
  "confirm_password": "newpass"
}
```

Success (200):

```json
{ "message": "Password changed successfully" }
```

---

## GET /api/v1/accounts/profile/

Description: Return the authenticated user's profile.

Auth: Required

Header:

- `Authorization: Bearer <access_token>`

Success (200) example:

```json
{
  "id": 12,
  "full_name": "Jane Example",
  "email": "jane@example.com",
  "is_active": true
}
```

---

## PATCH /api/v1/accounts/profile/update/

Description: Partially update the authenticated user's profile fields.

Auth: Required

Request JSON (example):

```json
{ "full_name": "Jane Newname" }
```

Success (200): Returns updated user object (same shape as GET profile).
