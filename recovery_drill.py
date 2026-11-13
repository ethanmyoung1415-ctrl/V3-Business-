"""One-command recovery rehearsal with wholly fictional data.

Creates a temporary portal DB, supplier upload and store workspace, snapshots
all of them, restores into a different directory, then verifies their bytes,
database integrity and tenant structure. This makes no use of customer data.
"""
import argparse
import json
import sqlite3
import tempfile
from pathlib import Path
import local_recovery_bundle as bundle

def _sqlite_ok(path):
    with sqlite3.connect(path) as db:
        return db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"

def run():
    with tempfile.TemporaryDirectory(prefix="v3-recovery-drill-") as temp:
        root=Path(temp)
        source=root/"source"
        source.mkdir()
        db=source/"portal.sqlite3"
        with sqlite3.connect(db) as connection:
            connection.execute("CREATE TABLE fictional_jobs(id TEXT,status TEXT)")
            connection.execute("INSERT INTO fictional_jobs VALUES('fictional-job-1','review')")
        uploads=source/"uploads";uploads.mkdir()
        workspaces=source/"workspaces";workspaces.mkdir()
        (uploads/"tenant-a").mkdir()
        (uploads/"tenant-a"/"supplier.csv").write_text(
            "sku,stock\n000001,0\n",encoding="utf-8")
        (workspaces/"tenant-a").mkdir()
        with sqlite3.connect(workspaces/"tenant-a"/"engine.sqlite3") as connection:
            connection.execute("CREATE TABLE examples(id TEXT,approved INTEGER)")
            connection.execute("INSERT INTO examples VALUES('000001',0)")
        (workspaces/"tenant-a"/"out.csv").write_text(
            "sku,title,price,stock\n000001,Demo,10,0\n",encoding="utf-8")
        archive=root/"synthetic-backup.zip"
        created=bundle.create(db,uploads,workspaces,archive,synthetic_only=True)
        backup_check=bundle.inspect(archive)
        target=root/"restored"
        restored=bundle.restore(archive,target,synthetic_only=True)
        files_equal=(
            (uploads/"tenant-a"/"supplier.csv").read_bytes() ==
            (target/"uploads"/"tenant-a"/"supplier.csv").read_bytes()
            and (workspaces/"tenant-a"/"out.csv").read_bytes() ==
            (target/"workspaces"/"tenant-a"/"out.csv").read_bytes()
        )
        portal_ok=_sqlite_ok(target/"portal.sqlite3")
        engine_ok=_sqlite_ok(target/"workspaces"/"tenant-a"/"engine.sqlite3")
        with sqlite3.connect(target/"portal.sqlite3") as connection:
            row=connection.execute("SELECT id,status FROM fictional_jobs").fetchone()
        with sqlite3.connect(target/"workspaces"/"tenant-a"/"engine.sqlite3") as connection:
            row2=connection.execute("SELECT id,approved FROM examples").fetchone()
        passed=(backup_check["verified"] and restored["verified"] and files_equal
                and portal_ok and engine_ok and row==("fictional-job-1","review")
                and row2==("000001",0))
        return {
            "passed":passed,"portal_db_restored":portal_ok,
            "engine_db_restored":engine_ok,
            "supplier_and_export_bytes_preserved":files_equal,
            "files_verified":created["verified_files"],
            "source":"synthetic_data_only",
            "unencrypted_backup":True,
            "production_backups_approved":False,
            "limitations":"No offsite encryption, hosted recovery, key rotation, downtime SLA, or live data.",
        }

def main():
    p=argparse.ArgumentParser(description="Run fictional V3 portal recovery rehearsal")
    p.parse_args()
    result=run()
    print(json.dumps(result,indent=2))
    if not result["passed"]:
        raise SystemExit(1)

if __name__=="__main__":main()
