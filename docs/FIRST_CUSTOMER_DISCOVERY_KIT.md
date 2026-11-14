# V3 first customer discovery kit (no customer data)

**Stage:** discovery, not a sale or production onboarding. V3 is currently a synthetic/local prototype. Do not suggest live monitoring or an active paid service.

## The narrow opening offer
V3 is developing a **done-for-you supplier catalog-update review service** for retailers whose suppliers periodically send CSV files. The service aims to detect ambiguous or risky changes, have an authorized operator review them, and produce an independently checked correction file plus a concise change report. In the proposed early pilot, **the customer imports the approved output**; V3 does not connect to or change the live store.

This is distinct from physical inventory reconciliation: supplier stock is not store stock. We cannot promise to know actual on-hand stock.

### Who to interview first
An owner/operations manager who:
- imports recurring supplier stock/price/product changes from CSV;
- uses a stable catalog with SKU identifiers;
- has experienced a bad update or spends time checking updates;
- can explain the current workflow without sharing actual files;
- can make or refer the buying decision.

Not a priority: a Shopify POS-only merchant whose main problem is inaccurate physical counts and who has no supplier file workflow. That requires a different product.

## Outreach templates

### Initial email
Subject: Quick question about supplier catalog updates

Hi,

I'm researching a managed service for retailers that receive recurring supplier catalog or price-list files. The goal is to save store teams time by checking updates and handling the review process rather than handing them another dashboard.

Do you receive supplier CSV updates that require someone to check product prices, titles or stock fields before importing them? If so, would you be open to a brief conversation about how you handle that process today?

I'm still validating the service and am not asking for store access or any confidential files.

Thanks,
V3

### Follow-up (one time, if appropriate)
Subject: Re: Supplier catalog updates

Hi,

Just following up on my earlier question. I'm trying to learn whether catalog-file review creates enough recurring work for small retailers to justify an outsourced service. If it isn't relevant, no reply is necessary.

Thanks,
V3

### Short phone introduction
"I'm validating a service that reviews recurring supplier CSV updates for retailers. I'm not selling an operational product today or asking for data. Could I ask a few questions about how you currently handle those updates?"

## Interview script (10–15 minutes)
1. How many suppliers send product updates? In what format and how often?
2. Approximately how many SKUs change per update?
3. Who checks or imports those updates, and how many minutes does a typical update take?
4. What was the most recent error? What did it cost in staff time or customer impact?
5. What rules govern stock, price and title updates? Which changes must be held for a manager?
6. If someone else prepared an evidence-checked file, would you be willing to import it? What would prevent you from trusting it?
7. What would you expect from a fully managed service? Which activities **must** stay with your team?
8. What pricing arrangement would be acceptable, and who decides? Avoid treating a hypothetical price answer as a commitment.
9. Would you want to hear about a limited pilot after independent review and approval are complete?
10. May we contact you again? Store only minimal contact information in an approved system when authorized.

Never ask for credentials, actual supplier files, lists of customers, bank information or live access at discovery stage.

## Fit scoring (internal, not customer-facing)
Score each dimension 0–2:
- Recurring files: none=0, occasional=1, weekly or more=2
- Update volume: <50=0, 50–499=1, >=500 SKUs=2
- Pain: none=0, inconvenience=1, measurable recurring cost=2
- Workflow match: no supplier CSV=0, partial match=1, stable SKU-based CSV=2
- Buying access: no decision-maker=0, referral possible=1, direct buyer=2

8–10: strong discovery prospect; 5–7: learn more; 0–4: unlikely fit for current product. **These thresholds are experimental.**

## Interview notes — one card per prospect
Date:
Business type (no personal details):
Buyer role:
Supplier file cadence:
Typical SKU volume:
Current software:
Minutes of human work/update:
Recent failure and impact:
Willingness to pay (exact words, if volunteered):
Pilot interest / objection:
Next action:
Permission to recontact (yes/no):
Fit score:
No private files received:

## Claims rules
- Say **developing** until a real release is approved.
- Never say a fictional demo used Shopify APIs, detected live errors, or placed orders.
- Do not claim guaranteed savings or error elimination.
- Do not promise premium purchasing workflows; those are future scope needing separate authorizations.
- Price (€99/€249/€499) is a hypothesis, not validated or yet a contractual offer.
