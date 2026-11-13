# Local-only customer invitations

**Scope: synthetic demonstration. No public signup, email automation or real customer accounts.**

## Why this exists
V3 should not allow anyone to create an account for an arbitrary retailer. A
store operator must explicitly invite a customer, and the invitation must be
single-use, time limited and limited to that store.

## Local demonstration
Set `V3_LOCAL_DEV=1`, install `requirements-portal.txt`, and run migrations.
First, seed a fictional operator and two stores using the instructions in
[PORTAL_DEMO.md](PORTAL_DEMO.md). Then issue one invitation:

```bash
python manage.py issue_local_invite STORE_UUID --operator v3-demo-operator --hours 24
```

The command shows a randomly generated code **once**. It is never stored in
plaintext; only the SHA-256 digest is stored in the local demonstration DB.

Enter the code manually at
`http://127.0.0.1:8000/join-local-demo/`. Choose a new username and a strong
password (at least 12 characters). The app creates a customer-only membership
to the invited store. It does not grant operator or cross-store permissions.

## Tested safeguards
- An operator cannot issue invitations for a store they don't manage.
- Ordinary customers cannot invite other customers.
- Codes expire in 1–72 hours and become unusable after one redemption.
- Disabled/inactive stores cannot enroll users.
- Duplicate usernames do not consume valid codes.
- Neither public registration nor email delivery is implemented.
- Invitation creation and redemption are disabled outside the local demo.

## Missing before production
Real hosting, rate-limited distributed invitation redemption, email identity
verification, verified account recovery, MFA, monitoring, CSRF/origin assurance,
professional threat-model review, and legal permission to offer an account
service are still required. The token is a bearer secret; anyone obtaining it
before redemption could enroll, so keep it private. **Do not use with real
customer accounts or information.**
