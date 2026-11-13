"""Local development-only inbox for synthetic supplier file pairs.

A job subdirectory is eligible only when the operator explicitly writes READY.
The watcher never contacts customers, accesses accounts, or approves changes.
"""
import os
import stat
from pathlib import Path
import operations

def scan(db,inbox):
    root=Path(inbox)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("inbox must be a real local directory")
    summary={"enqueued":[],"skipped":[],"errors":[]}
    for entry in sorted(root.iterdir()):
        if entry.is_symlink() or not entry.is_dir():
            continue
        marker=entry/"READY"
        if not marker.exists():continue
        if marker.is_symlink() or not marker.is_file():
            summary["errors"].append({"folder":entry.name,"error":"invalid READY marker"})
            continue
        files=[entry/"baseline.csv",entry/"update.csv"]
        if any(not x.is_file() or x.is_symlink() for x in files):
            summary["errors"].append({"folder":entry.name,"error":"missing or linked CSV"})
            continue
        if (entry/"QUEUED").exists():
            summary["skipped"].append(entry.name)
            continue
        try:
            result=operations.enqueue(db,*files)
            # Replacing the READY marker prevents repeated staging of a job.
            # The queue is idempotent if a crash happens before this rename.
            os.replace(marker,entry/"QUEUED")
            summary["enqueued"].append({"folder":entry.name,**result})
        except (ValueError,OSError) as ex:
            summary["errors"].append({"folder":entry.name,"error":str(ex)[:160]})
    return summary
