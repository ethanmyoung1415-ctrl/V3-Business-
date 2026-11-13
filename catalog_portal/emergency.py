"""Local preproduction emergency stop.

A file-backed kill switch is deliberately independent of the database and
worker process. It is not a production incident response system.
"""
from pathlib import Path
from django.conf import settings

def stop_file():
    return Path(getattr(settings,"V3_PAUSE_FILE",settings.BASE_DIR/".v3_paused"))

def is_paused():
    return stop_file().is_file()

def require_running():
    if is_paused():
        raise RuntimeError("V3 operations are paused for incident investigation")

def set_paused(should_pause):
    path=stop_file()
    if should_pause:
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with path.open("x",encoding="utf-8") as stream:
                stream.write("V3 local emergency stop enabled\n")
    else:
        path.unlink(missing_ok=True)
    return {"paused":is_paused()}
