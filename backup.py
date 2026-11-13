"""Verified backup and restore for a LOCAL V3 SQLite database.

This backs up the database only, not input snapshots or exports. It is not a
disaster recovery service and must not be used with real customer data.
"""
import argparse,hashlib,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        while chunk:=f.read(65536):h.update(chunk)
    return h.hexdigest()

def integrity(path):
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro",uri=True) as db:
        result=db.execute("PRAGMA integrity_check").fetchone()[0]
        return result=="ok"

def create(db,destination):
    source=Path(db).resolve(strict=True)
    target=Path(destination)
    manifest=Path(str(target)+".json")
    if target.exists() or manifest.exists():raise ValueError("backup destination already exists")
    if not source.is_file():raise ValueError("not a database file")
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with sqlite3.connect(f"file:{source}?mode=ro",uri=True) as src:
            with sqlite3.connect(target) as out:
                src.backup(out)
        if not integrity(target):raise ValueError("backup failed integrity check")
        summary={"sha256":sha256(target),"created":datetime.now(timezone.utc).isoformat(),
                 "format":"sqlite3","scope":"database_only"}
        with manifest.open("x",encoding="utf-8") as f:
            json.dump(summary,f,indent=2)
        return {"backup":str(target),"manifest":str(manifest),**summary}
    except BaseException:
        target.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise

def restore(source,destination):
    backup=Path(source)
    dest=Path(destination)
    manifest=Path(str(backup)+".json")
    if dest.exists():raise ValueError("restore destination already exists")
    record=json.loads(manifest.read_text(encoding="utf-8"))
    if record.get("format")!="sqlite3" or record.get("sha256")!=sha256(backup):
        raise ValueError("backup manifest/hash mismatch")
    if not integrity(backup):raise ValueError("backup integrity check failed")
    dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        with sqlite3.connect(f"file:{backup.resolve()}?mode=ro",uri=True) as inp:
            with sqlite3.connect(dest) as out:inp.backup(out)
        if not integrity(dest):raise ValueError("restored database failed integrity check")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return {"restored":str(dest),"sha256":sha256(dest),"verified":True}

def main():
    p=argparse.ArgumentParser(description="Local SQLite backup/restore with SHA-256 integrity")
    sub=p.add_subparsers(dest="command",required=True)
    for command in ("create","restore"):
        s=sub.add_parser(command)
        s.add_argument("source")
        s.add_argument("destination")
    args=p.parse_args()
    result=create(args.source,args.destination) if args.command=="create" else restore(args.source,args.destination)
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
