"""Lightweight pre-commit/CI guard for a public synthetic V3 repository.

This is defense in depth, not a comprehensive secret scanner.
"""
import argparse
import re
import subprocess
from pathlib import Path

FORBIDDEN_NAMES={
    ".env",".env.local",".env.production","id_rsa","id_ed25519",
    "credentials.json","service_account.json",
}
FORBIDDEN_SUFFIXES={".pem",".p12",".pfx",".key",".sqlite3",".db"}
SUSPECT_TOKENS=(
    re.compile(r"sk-[A-Za-z0-9_-]{24,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
)
MAX_SCAN_BYTES=3_000_000

def validate_file(path,data):
    path=Path(path)
    violations=[]
    if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
        violations.append("secret-or-data file type cannot be committed")
    if len(data)>MAX_SCAN_BYTES:
        violations.append("large file requires explicit review")
        return violations
    body=data.decode("utf-8",errors="replace")
    for pattern in SUSPECT_TOKENS:
        if pattern.search(body):
            violations.append("possible credential or private-key material")
    return violations

def tracked_paths(repo="."):
    cwd=Path(repo)
    result=subprocess.run(["git","ls-files","-z"],cwd=cwd,check=True,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return [cwd/name.decode("utf-8") for name in result.stdout.split(b"\0") if name]

def scan_repository(root="."):
    root=Path(root)
    problems=[]
    for path in tracked_paths(root):
        if not path.is_file():
            continue
        for reason in validate_file(path,path.read_bytes()):
            problems.append({"path":str(path.relative_to(root)),"reason":reason})
    return problems

def main():
    p=argparse.ArgumentParser(description="Reject obvious secrets and local business data")
    p.add_argument("--repository",default=".")
    args=p.parse_args()
    problems=scan_repository(args.repository)
    for item in problems:
        print(f"{item['path']}: {item['reason']}")
    print(f"Repository guard: {'FAILED' if problems else 'passed'}")
    if problems:raise SystemExit(2)
if __name__=="__main__":main()
