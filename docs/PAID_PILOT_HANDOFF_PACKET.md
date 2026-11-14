# V3 commercial pilot handoff and acceptance packet

**State: preproduction / authorization outstanding.** This packet records decisions and evidence; it does not create legal permission.

## Pilot scope — proposed
- One retailer and one store; one supplier CSV format; explicit SKU mapping.
- Capped number of records and updates per month (define after interview and cost test).
- V3 handles input validation, holds ambiguity, internal review, independent output QA and verified delivery.
- The store retains responsibility for *actual on-hand* stock facts and externally importing approved files.
- No automated reorder, purchase, direct storefront write, external AI analysis of customer files, or live stock guarantee.
- Customer authorizes exactly defined corrections; disputed/ambiguous updates remain held.
- No real data until signed terms, security review, secure infrastructure, and written authorization.

## Required adult/signatory decisions (complete before any charge)
| Decision | Authorized answer / evidence | Status |
|---|---|---|
| Legal entity and actual owner | | PENDING |
| Who signs customer agreements | | PENDING |
| Who may open/pay for providers | | PENDING |
| Hosting monthly cap | | PENDING |
| Contractor/employee/insurance approach | | PENDING |
| Billing processor and invoice method | | PENDING |
| Tax/accounting advisor | | PENDING |
| Customer jurisdiction and privacy counsel | | PENDING |

## Security reviewer sign-off record
Reviewer and qualifications:
System/revision reviewed:
Hosting region/provider:
Authentication/MFA/session recovery:
Tenant isolation & IDOR tests:
Original/normalized file storage and encryption:
Upload validation/malware/quotas:
Queue durability and replay protection:
Audit evidence / independent QA:
Encrypted backups and restore drill:
Deletion/retention:
Incident response and alerts:
Penetration testing findings:
Unresolved risks:
Disposition: NOT REVIEWED / FIX / APPROVED WITH SCOPE
Signed/dated:

**No entries may be assumed complete simply because local tests pass.**

## Synthetic staging evidence log
- Git commit SHA:
- Environment configuration description (never paste secrets):
- Python unit suite result:
- Django suite result:
- Migration check:
- Strict synthetic preflight:
- Multi-tenant isolation/fuzz/concurrency outcomes:
- Backups and independent restoration:
- Failure injection and stop switch:
- Delivery/export QA:
- Staging HTTPS/MFA/object storage/queue evidence:
- Review/approval of operational readiness:

## Paid pilot acceptance — customer-specific
Customer identifier (internal):
Authorized signatory:
Service start / duration:
Agreed file and SKU limits:
Frequency and response times:
Permitted operations and excluded operations:
Who confirms actual store inventory:
Who imports the verified output:
Error/rework process:
Data-processing/privacy agreement:
Data retention/deletion:
Cancellation/refund terms:
Service price and billing authorization:
Customer approvals / signed dates:
Security review reference:
Final release decision: **NO-GO until each relevant field is validated**.

## Operator test sheet — record actual time
| Action | Start/end or minutes | Result | Exception category |
|---|---|---|---|
| Intake and validation | | | |
| Exception review | | | |
| Evidence/clarification | | | |
| Independent export QA | | | |
| Customer delivery/support | | | |
| Rework and incident handling | | | |

Track monthly contribution margin from *actual* subscriptions minus operator time, cloud/provider fees, payment charges, support and rework. Do not equate subscription receipts with profit.

## Explicit stop conditions
Any cross-tenant access, unauthorized change, unverifiable export, leaked credentials, breached data agreement, failed backup restore, unsupported order/write action, or undocumented approval blocks customer delivery and commercial escalation until fixed and revalidated.
