# Optional synthetic release HMAC receipts

V3 can create a local authenticity receipt for a verified CSV and its JSON change report. It uses HMAC-SHA256 with a secret key **held outside GitHub and outside the AI conversation**.

This is an optional experimental tool, not a production signing infrastructure.

## What it proves
If the key remains secret, a receipt can detect changes to a CSV or JSON report after issuance. It does not prove live-store import, financial savings, customer identity, legal authorization, or that the files were correct to begin with.

## Requirements
1. A separately generated, high-entropy key of at least 32 bytes, provided as a hexadecimal value in the local environment variable `V3_LOCAL_RECEIPT_KEY_HEX`.
2. A *verified* change report produced from a committed, independently reconciled output.
3. A destination receipt path that does not already exist.

```bash
python release_receipt.py issue approved.csv change-report.json receipt.json
python release_receipt.py verify approved.csv change-report.json receipt.json
```

The command does not print or store the key. Do not commit keys, put them into shell history as literal arguments, or paste them into chat.

This project **does not** have secure multi-tenant key storage, key rotation, key revocation, verified identities, hardware keys, or a public trust infrastructure. It must not be marketed as a digital-signature service.