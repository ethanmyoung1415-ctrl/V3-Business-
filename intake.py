"""Local snapshot-based intake of synthetic CSV files.

This is a safety improvement for the development prototype, NOT a production
customer-upload facility. Reject symlinks and non-regular files; copy to a
private staging directory and verify source content throughout the copy.
"""
import hashlib
import os
import stat
import tempfile
import uuid
from pathlib import Path

MAX_BYTES=15_000_000

def _source(path,allowed_exts=(".csv",)):
    path=Path(path).absolute()
    entry=os.lstat(path)
    if not stat.S_ISREG(entry.st_mode):
        raise ValueError("only regular CSV files are allowed; links are prohibited")
    if path.suffix.lower() not in allowed_exts:
        raise ValueError("unsupported file format for this intake")
    if entry.st_size>MAX_BYTES:
        raise ValueError("source file exceeds intake size limit")
    return path,entry

def stage_csv(path,store,allowed_exts=(".csv",)):
    source,initial=_source(path,allowed_exts)
    store=Path(store)
    store.mkdir(parents=True,exist_ok=True,mode=0o700)
    # Owner permissions are best effort on Windows; real production access
    # controls must be implemented independently of local file permissions.
    if store.is_symlink():
        raise ValueError("staging directory cannot be a symlink")
    if not store.is_dir():
        raise ValueError("staging directory is invalid")
    file_descriptor,tmp=tempfile.mkstemp(prefix=".incoming-",dir=store)
    target=store/(str(uuid.uuid4())+source.suffix.lower())
    src_fd=None
    try:
        os.fchmod(file_descriptor,0o600) if hasattr(os,"fchmod") else None
        flags=os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)
        src_fd=os.open(source,flags)
        current=os.fstat(src_fd)
        if not stat.S_ISREG(current.st_mode) or current.st_size>MAX_BYTES:
            raise ValueError("source changed or is not a regular file")
        if (current.st_dev,current.st_ino,current.st_size)!=(initial.st_dev,initial.st_ino,initial.st_size):
            raise ValueError("source changed during intake")
        checksum=hashlib.sha256()
        total=0
        with os.fdopen(file_descriptor,"wb") as out:
            file_descriptor=None
            while True:
                chunk=os.read(src_fd,65536)
                if not chunk:break
                total+=len(chunk)
                if total>MAX_BYTES:raise ValueError("source exceeds intake size limit")
                checksum.update(chunk)
                out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        after=os.fstat(src_fd)
        if (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)!=(current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns):
            raise ValueError("source was modified during intake")
        if total!=current.st_size:
            raise ValueError("source length mismatch")
        os.replace(tmp,target)
        return target,checksum.hexdigest()
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    finally:
        if file_descriptor is not None:os.close(file_descriptor)
        if src_fd is not None:os.close(src_fd)

def stage_pair(baseline,update,db,allow_xlsx=False):
    store=Path(db).resolve().parent/".v3_staged"
    outputs=[]
    try:
        allowed=(".csv",".xlsx") if allow_xlsx else (".csv",)
        for item in (baseline,update):
            outputs.append(stage_csv(item,store,allowed_exts=allowed))
        return outputs
    except BaseException:
        for path,_ in outputs:
            path.unlink(missing_ok=True)
        raise

def cleanup_staged(paths):
    for p in paths:
        try:Path(p).unlink(missing_ok=True)
        except OSError:pass
