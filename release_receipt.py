"""Optional HMAC receipt for *synthetic* reviewed CSV + change report.

Only proves a receipt matches these bytes under a separately held secret.
It does not certify business correctness, live-store state, identity,
independent security review, or production key management.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path

MAX_REPORT_BYTES=10_000_000

def _hash(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk:=stream.read(65536):
            h.update(chunk)
    return h.hexdigest()

def _key(value):
    if isinstance(value,str):
        try:value=bytes.fromhex(value)
        except ValueError:raise ValueError("invalid key format")
    if not isinstance(value,bytes) or len(value)<32:
        raise ValueError("signing key must contain at least 32 random bytes")
    return value

def _report(path,csv_sha):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>MAX_REPORT_BYTES:
        raise ValueError("missing or oversized change report")
    try:body=json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError,json.JSONDecodeError):raise ValueError("invalid report JSON")
    if (not isinstance(body,dict) or not isinstance(body.get("job_id"),str)
            or body.get("verification",{}).get("passed") is not True
            or body["verification"].get("sha256")!=csv_sha):
        raise ValueError("change report lacks matching verified-export evidence")
    return body

def _serialize(core):
    return json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()

def issue(csv_file,report_file,receipt_file,key):
    key=_key(key)
    receipt=Path(receipt_file)
    if receipt.exists():raise ValueError("receipt already exists")
    csv_sha=_hash(csv_file)
    report=_report(report_file,csv_sha)
    core={
        "schema_version":1,
        "scope":"synthetic_local_release",
        "job_id":report["job_id"],
        "csv_sha256":csv_sha,
        "report_sha256":_hash(report_file),
        "caveat":"Byte integrity only; not proof of import or business correctness.",
    }
    signature=hmac.new(key,_serialize(core),hashlib.sha256).hexdigest()
    payload={**core,"hmac_sha256":signature}
    receipt.parent.mkdir(parents=True,exist_ok=True)
    with receipt.open("x",encoding="utf-8") as stream:
        json.dump(payload,stream,sort_keys=True,indent=2)
        stream.write("\n")
    return {"path":str(receipt),"job_id":core["job_id"],
            "csv_sha256":csv_sha,"signed":True}

def verify(csv_file,report_file,receipt_file,key):
    key=_key(key)
    path=Path(receipt_file)
    if path.stat().st_size>16384:
        raise ValueError("receipt too large")
    try:payload=json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError,json.JSONDecodeError):
        raise ValueError("invalid receipt JSON")
    if not isinstance(payload,dict) or set(payload)!={
        "schema_version","scope","job_id","csv_sha256","report_sha256",
        "caveat","hmac_sha256"}:
        raise ValueError("unexpected receipt structure")
    signature=payload["hmac_sha256"]
    if not isinstance(signature,str) or len(signature)!=64:
        raise ValueError("invalid signature")
    core={key_:value for key_,value in payload.items() if key_!="hmac_sha256"}
    expected=hmac.new(key,_serialize(core),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature,expected):
        raise ValueError("receipt authentication failed")
    if payload["schema_version"]!=1 or payload["scope"]!="synthetic_local_release":
        raise ValueError("unsupported receipt")
    csv_sha=_hash(csv_file)
    report=_report(report_file,csv_sha)
    if (payload["csv_sha256"]!=csv_sha or
            payload["report_sha256"]!=_hash(report_file) or
            payload["job_id"]!=report["job_id"]):
        raise ValueError("receipt does not match supplied files")
    return {"passed":True,"job_id":payload["job_id"],"bytes_authenticated":True,
            "live_store_verified":False}

def main():
    p=argparse.ArgumentParser(description="Optional local synthetic release receipt")
    p.add_argument("operation",choices=("issue","verify"))
    p.add_argument("csv")
    p.add_argument("report")
    p.add_argument("receipt")
    args=p.parse_args()
    secret=os.environ.get("V3_LOCAL_RECEIPT_KEY_HEX","")
    if not secret:raise SystemExit("V3_LOCAL_RECEIPT_KEY_HEX must be supplied privately")
    result=issue(args.csv,args.report,args.receipt,secret) if args.operation=="issue" else (
        verify(args.csv,args.report,args.receipt,secret))
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
