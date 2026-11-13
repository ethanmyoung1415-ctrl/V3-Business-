# Manually prepared prior-catalog snapshot

A verified export may have been imported into an outside retailer account manually. If the retailer later wants to reverse it, V3 can *prepare the stored prior baseline* — but it cannot know what other changes have been made since.

```bash
python manual_rollback.py --db demo.sqlite3 --actor operator --reason "Confirmed prior state required" JOB_ID released.csv previous.csv
```

This operation requires a committed released job, a valid independent audit and QA proof for the released file, a human name and a meaningful reason. It writes a new CSV without overwriting existing output, independently checks its rows against the preserved baseline, and records a manual-recovery event.

**It does not touch or inspect a live store.** A retailer or authorized operator must first compare the live current catalog, determine whether unrelated changes have occurred, obtain customer approval, and choose an appropriate partial or full remediation. Blindly importing an old snapshot may cause data loss.

The underlying local SQLite audit and any optional receipt are not proof against a privileged person editing all local records. External logging and production recovery procedures are still required.