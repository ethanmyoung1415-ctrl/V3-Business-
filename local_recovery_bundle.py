"""Local synthetic portal disaster-recovery snapshot and restore drill.

NOT encrypted, NOT a production backup, NOT suitable for real customer data.

Captures the Django SQLite database, private uploads, per-store worker
workspaces and pause state. Files must remain quiescent during the snapshot.
All backup archive contents are verified by SHA-256 before restoration.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from pathlib import Path

MAX_FILES=3000
MAX_TOTAL_BYTES=300_000_000
MAX_SINGLE_BYTES=50_000_000
CHUNK=65536
PORTAL_DB="portal.sqlite3"
ROOTS=("uploads","workspaces")
MANIFEST="manifest.json"
SEAL="V3_SYNTHETIC_ONLY_NO_CUSTOMER_DATA"

def _sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk:=stream.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()

def _regular(path):
    node=Path(path)
    st=node.lstat()
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
        raise ValueError("backup accepts regular files only")
    if st.st_size>MAX_SINGLE_BYTES:
        raise ValueError("backup source exceeds individual size limit")
    return st

def _walk(source,category):
    root=Path(source)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("backup source must be a non-symlink directory")
    found=[]
    for path in sorted(root.rglob("*")):
        st=path.lstat()
        if stat.S_ISLNK(st.st_mode):
            raise ValueError("backup refuses symlinks")
        if path.is_dir():
            continue
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("backup refuses special files")
        _regular(path)
        found.append((f"{category}/{path.relative_to(root).as_posix()}",path))
    return found

def _snapshot_sqlite(source,target):
    source=Path(source)
    _regular(source)
    with sqlite3.connect(f"file:{source.resolve()}?mode=ro",uri=True,timeout=15) as src:
        with sqlite3.connect(target,timeout=15) as dst:
            src.backup(dst)
    with sqlite3.connect(target) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
            raise ValueError("SQLite snapshot failed integrity check")

def _validate_name(name):
    if not isinstance(name,str) or not name or "\\" in name or name.startswith("/"):
        raise ValueError("unsafe archive member")
    parts=name.split("/")
    if any(x in ("",".","..") for x in parts):
        raise ValueError("unsafe archive member")
    if name!=PORTAL_DB and not (
        len(parts)>=2 and parts[0] in ROOTS
    ):
        raise ValueError("unexpected archive member")
    return name

def create(portal_db,uploads,workspaces,archive,*,synthetic_only=False):
    if not synthetic_only:
        raise PermissionError("explicit synthetic-only acknowledgment required")
    target=Path(archive)
    if target.exists():
        raise ValueError("backup already exists")
    source_db=Path(portal_db)
    entries=_walk(uploads,"uploads")+_walk(workspaces,"workspaces")
    if source_db.is_symlink():
        raise ValueError("symlinked portal database")
    _regular(source_db)
    if len(entries)+1>MAX_FILES:
        raise ValueError("too many source files")
    # Backups must not be written into source trees.
    resolved=target.resolve()
    if any(resolved==Path(root).resolve() or Path(root).resolve() in resolved.parents
           for root in (uploads,workspaces)):
        raise ValueError("backup must be outside source trees")
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.TemporaryDirectory(prefix="v3-snapshot-") as folder:
            local=Path(folder)
            db_snapshot=local/PORTAL_DB
            _snapshot_sqlite(source_db,db_snapshot)
            all_entries=[(PORTAL_DB,db_snapshot)]+entries
            manifest={"schema":1,"scope":SEAL,"files":[]}
            size=0
            for name,path in all_entries:
                _validate_name(name)
                st=_regular(path)
                size+=st.st_size
                if size>MAX_TOTAL_BYTES:
                    raise ValueError("backup exceeds total size limit")
                manifest["files"].append({
                    "path":name,"bytes":st.st_size,"sha256":_sha(path)})
            with tempfile.NamedTemporaryFile(
                prefix=".v3-backup-",suffix=".zip",
                dir=target.parent,delete=False
            ) as stream:
                temporary=Path(stream.name)
            with zipfile.ZipFile(
                temporary,"w",compression=zipfile.ZIP_DEFLATED,
                compresslevel=5,allowZip64=False
            ) as z:
                for record,(name,path) in zip(manifest["files"],all_entries):
                    if path.stat().st_size!=record["bytes"] or _sha(path)!=record["sha256"]:
                        raise ValueError("file changed while backing up")
                    z.write(path,arcname=name)
                z.writestr(MANIFEST,json.dumps(manifest,sort_keys=True))
            verified=inspect(temporary)
            os.link(temporary,target)
            return {"path":str(target),"sha256":_sha(target),
                    "verified_files":verified["file_count"],
                    "unencrypted":True,"synthetic_only":True}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def inspect(archive):
    bundle=Path(archive)
    with zipfile.ZipFile(bundle) as z:
        members=z.infolist()
        names=[item.filename for item in members]
        if len(names)!=len(set(names)) or MANIFEST not in names:
            raise ValueError("invalid archive members")
        if len(names)>MAX_FILES+2:
            raise ValueError("backup has too many members")
        if z.getinfo(MANIFEST).file_size>500_000:
            raise ValueError("manifest too large")
        try:manifest=json.loads(z.read(MANIFEST))
        except (ValueError,UnicodeError):
            raise ValueError("invalid backup manifest")
        if not isinstance(manifest,dict) or manifest.get("schema")!=1 or manifest.get("scope")!=SEAL:
            raise ValueError("unsupported or unsafe backup")
        records=manifest.get("files")
        if not isinstance(records,list) or not records:
            raise ValueError("backup manifest missing files")
        expected={};total=0
        for rec in records:
            if not isinstance(rec,dict) or set(rec)!={"path","bytes","sha256"}:
                raise ValueError("invalid backup record")
            name=_validate_name(rec["path"])
            amount=rec["bytes"]
            digest=rec["sha256"]
            if (name in expected or type(amount) is not int or amount<0 or
                    amount>MAX_SINGLE_BYTES or not isinstance(digest,str) or
                    len(digest)!=64):
                raise ValueError("invalid or duplicate backup record")
            expected[name]=(amount,digest)
            total+=amount
            if total>MAX_TOTAL_BYTES:
                raise ValueError("backup total size too large")
        if PORTAL_DB not in expected or set(names)!={*expected,MANIFEST}:
            raise ValueError("backup members differ from manifest")
        for info in members:
            if info.filename==MANIFEST:
                continue
            if info.is_dir() or info.file_size!=expected[info.filename][0]:
                raise ValueError("unexpected archived file size")
            if info.file_size>max(info.compress_size,1)*200:
                raise ValueError("unsafe compression expansion")
            checksum=hashlib.sha256()
            read_bytes=0
            with z.open(info) as stream:
                while block:=stream.read(CHUNK):
                    checksum.update(block);read_bytes+=len(block)
                    if read_bytes>expected[info.filename][0]:
                        raise ValueError("expanded file exceeds manifest")
            if (read_bytes,checksum.hexdigest())!=expected[info.filename]:
                raise ValueError("file digest mismatch")
        return {"file_count":len(expected),"bytes":total,
                "files":sorted(expected),"verified":True}

def restore(archive,destination,*,synthetic_only=False):
    if not synthetic_only:
        raise PermissionError("explicit synthetic-only acknowledgment required")
    dest=Path(destination)
    if dest.exists():
        raise ValueError("restore target already exists")
    verified=inspect(archive)
    dest.mkdir(parents=True,mode=0o700)
    try:
        with zipfile.ZipFile(archive) as z:
            for name in verified["files"]:
                target=dest/name
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with z.open(name) as src,target.open("xb") as out:
                    shutil.copyfileobj(src,out,length=CHUNK)
                target.chmod(0o600)
        with sqlite3.connect(dest/PORTAL_DB) as conn:
            if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("restored portal DB is invalid")
        # Reinspection never trusts files blindly after extraction.
        return {"path":str(dest),"verified":True,"files":verified["file_count"],
                "synthetic_only":True,"unencrypted":True}
    except BaseException:
        shutil.rmtree(dest)
        raise
