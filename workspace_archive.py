"""Offline synthetic workspace archive and verified restore.

Archive includes the per-store engine DB, staged inputs and export files.
It excludes the separate portal authentication database and uploaded originals.
UNENCRYPTED: NOT suitable for real customer files or production backups.
"""
import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

MAX_TOTAL=250_000_000
MAX_FILES=2500
CHUNK_SIZE=65536
MANIFEST="manifest.json"

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk:=stream.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()

def collect(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("workspace must be a real directory")
    files=[]
    total=0
    for path in sorted(root.rglob("*")):
        info=path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("linked workspace file not permitted")
        if path.is_dir():continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("non-regular workspace file")
        relative=path.relative_to(root).as_posix()
        if relative==MANIFEST:
            raise ValueError("workspace cannot contain a reserved manifest file")
        total+=info.st_size
        if total>MAX_TOTAL or len(files)+1>MAX_FILES:
            raise ValueError("workspace archive limits exceeded")
        files.append((path,relative,info.st_size,sha256(path)))
    if not files:
        raise ValueError("cannot back up an empty workspace")
    return files

def create(root,archive):
    """Build manifest + archive before atomic publication; never overwrite."""
    root=Path(root)
    destination=Path(archive)
    if destination.exists():raise ValueError("archive already exists")
    if root.resolve() in destination.resolve().parents:
        raise ValueError("archive cannot be located inside source workspace")
    files=collect(root)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(prefix=".backup-",suffix=".zip",
                                         dir=destination.parent,delete=False) as f:
            temp=Path(f.name)
        with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED,
                             compresslevel=5,allowZip64=False) as bundle:
            for path,relative,size,digest in files:
                if path.stat().st_size!=size or sha256(path)!=digest:
                    raise ValueError("file changed during archive creation")
                bundle.write(path,arcname=relative)
            manifest={
                "schema_version":1,
                "scope":"synthetic_workspace_only",
                "files":[{"path":rel,"size":size,"sha256":digest}
                         for _,rel,size,digest in files],
            }
            bundle.writestr(MANIFEST,json.dumps(manifest,sort_keys=True))
        # Verifies the actual compressed bytes rather than trusting the source.
        verify_archive(temp)
        os.link(temp,destination)
        return {"archive":str(destination),"sha256":sha256(destination),
                "file_count":len(files)}
    finally:
        if temp is not None:temp.unlink(missing_ok=True)

def _safe_path(value):
    if not isinstance(value,str) or not value or "\\" in value:
        raise ValueError("invalid archive path")
    path=Path(value)
    if path.is_absolute() or any(part in ("","..",".") for part in value.split("/")):
        raise ValueError("unsafe archive path")
    if value==MANIFEST:
        raise ValueError("reserved archive path")
    return path

def verify_archive(archive):
    with zipfile.ZipFile(archive,"r") as bundle:
        names=bundle.namelist()
        if len(names)!=len(set(names)) or MANIFEST not in names:
            raise ValueError("invalid or duplicate archive names")
        if len(names)>MAX_FILES+1:
            raise ValueError("too many archive entries")
        manifest=json.loads(bundle.read(MANIFEST))
        if manifest.get("schema_version")!=1 or manifest.get("scope")!="synthetic_workspace_only":
            raise ValueError("unsupported workspace manifest")
        records=manifest.get("files")
        if not isinstance(records,list) or not records:
            raise ValueError("missing workspace file list")
        listed={}
        total=0
        for record in records:
            relative=_safe_path(record.get("path"))
            name=relative.as_posix()
            if name in listed or name not in names:
                raise ValueError("missing or duplicate listed file")
            size=record.get("size")
            digest=record.get("sha256")
            if not isinstance(size,int) or size<0 or not isinstance(digest,str) or len(digest)!=64:
                raise ValueError("invalid file metadata")
            info=bundle.getinfo(name)
            if info.is_dir() or info.file_size!=size:
                raise ValueError("archive file-size mismatch")
            total+=size
            if total>MAX_TOTAL:
                raise ValueError("archive exceeds size limit")
            listed[name]=(size,digest)
        if set(names)-{MANIFEST}!=set(listed):
            raise ValueError("archive includes unexpected entries")
        for name,(size,digest) in listed.items():
            h=hashlib.sha256()
            actual=0
            with bundle.open(name) as src:
                while chunk:=src.read(CHUNK_SIZE):
                    actual+=len(chunk)
                    if actual>size:raise ValueError("file expands beyond declared size")
                    h.update(chunk)
            if actual!=size or h.hexdigest()!=digest:
                raise ValueError("workspace archive content hash mismatch")
        return {"verified":True,"file_count":len(listed),"bytes":total,
                "files":list(listed)}

def restore(archive,destination):
    output=Path(destination)
    if output.exists():raise ValueError("restore destination already exists")
    verified=verify_archive(archive)
    output.mkdir(parents=True,mode=0o700)
    try:
        with zipfile.ZipFile(archive,"r") as bundle:
            for name in verified["files"]:
                relative=_safe_path(name)
                target=output/relative
                target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with bundle.open(name) as src,target.open("xb") as dst:
                    shutil.copyfileobj(src,dst,length=CHUNK_SIZE)
                target.chmod(0o600)
        if set(relative.as_posix() for relative in
               [p.relative_to(output) for p in output.rglob("*") if p.is_file()]
               )!=set(verified["files"]):
            raise ValueError("restored file set mismatch")
        return {"restored":str(output),"file_count":verified["file_count"],
                "verified":True}
    except BaseException:
        shutil.rmtree(output)
        raise
