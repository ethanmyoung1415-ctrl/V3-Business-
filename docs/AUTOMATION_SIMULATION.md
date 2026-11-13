# Dry-run automation eligibility — no automated approvals

This feature exists to measure the possible reduction of operator clicks **without** granting automation authority.

Run the CLI against a synthetic review job:

```bash
python autonomy_simulator.py --db demo.sqlite3 JOB_ID
```

With no policy file, simulation is disabled. To explicitly study a hypothetical policy, create a fictional JSON file matching `autonomy_simulator.DEFAULT` and set `authorized_simulation` to `true`. This flag authorizes only an in-memory calculation; it is **not** customer consent to execute anything.

The Django operator can open the read-only "automation preview" on a review job. It uses a strict hypothetical stock-only example. Customers cannot see that page; viewing it never changes a decision.

## Restrictions
- Only stock values, never price, title, unknown fields or new SKUs
- No zero-stock automation; source holds block the entire simulation
- Previous stock at least 20 units, at most 2 units and 5% change
- Per-job candidate cap; exclusions are respected
- No database decision update, file delivery, AI execution or network operation

These constraints are deliberately more restrictive than human-triggered batch review.

Before any real auto-approval, require written customer-specific policy, independent deterministic enforcement, audit log and rollback validation, staged evaluation of false positives/negatives, and an authorized operator/business signoff. The current simulation is not evidence that hands-off operation is safe.