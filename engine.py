"""V3 offline catalog change control. Prototype only; do not use with live customer data."""
import argparse,csv,hashlib,json,sqlite3,sys,uuid
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path

FIELDS=("sku","title","price","stock")
def timestamp(): return datetime.now(timezone.utc).isoformat()
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def price(value):
    try:
        v=Decimal(str(value).strip())
        if not v.is_finite() or v<0: raise ValueError()
        return str(v)
    except (InvalidOperation,ValueError): raise ValueError("invalid price")
def stock(value):
    s=str(value).strip()
    if not s.isascii() or not s.isdigit(): raise ValueError("invalid stock")
    return str(int(s))
def load(path):
    path=Path(path)
    if path.stat().st_size>15_000_000: raise ValueError("file too large")
    with path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: raise ValueError("missing header")
        fields=[x.strip().lower() for x in reader.fieldnames]
        if len(fields)!=len(set(fields)) or any(x not in FIELDS for x in fields) or "sku" not in fields:
            raise ValueError("invalid or duplicate headers")
        rows=[]
        for lineno,r in enumerate(reader,2):
            if None in r or any(v is None for v in r.values()): raise ValueError(f"malformed row {lineno}")
            cleaned={k.strip().lower():v for k,v in r.items()}
            for field in ("sku","title"):
                value=cleaned.get(field,"")
                if value.lstrip().startswith(("=","+","-","@")) or any(ch in value for ch in ("\\x00","\\t","\\r","\\n")):
                    raise ValueError(f"unsafe spreadsheet text in {field} at row {lineno}")
            rows.append((lineno,cleaned))
            if len(rows)>100000: raise ValueError("too many rows")
    return rows,fields
def setup(db):
    with sqlite3.connect(db) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,created TEXT,status TEXT,baseline_hash TEXT,update_hash TEXT,holds TEXT);
        CREATE TABLE IF NOT EXISTS base(job TEXT,sku TEXT,title TEXT,price TEXT,stock TEXT,PRIMARY KEY(job,sku));
        CREATE TABLE IF NOT EXISTS changes(id TEXT PRIMARY KEY,job TEXT,sku TEXT,field TEXT,old TEXT,new TEXT,status TEXT,reason TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,job TEXT,kind TEXT,details TEXT);
        """)
def log(c,job,kind,details):
    c.execute("INSERT INTO events(at,job,kind,details) VALUES(?,?,?,?)",
              (timestamp(),job,kind,json.dumps(details,sort_keys=True)))
def ingest(db,baseline,update):
    setup(db)
    br,bfields=load(baseline);ur,ufields=load(update)
    if set(bfields)!=set(FIELDS): raise ValueError("baseline must include sku,title,price,stock")
    base={}
    for line,row in br:
        sku=row["sku"].strip()
        if not sku or sku in base: raise ValueError(f"baseline missing/duplicate sku at {line}")
        base[sku]={"sku":sku,"title":row["title"],"price":price(row["price"]),"stock":stock(row["stock"])}
    seen={};dupes=set();holds=[];changes=[]
    for line,row in ur:
        sku=row["sku"].strip()
        if not sku:
            holds.append({"line":line,"reason":"blank SKU"});continue
        if sku in seen: dupes.add(sku)
        else: seen[sku]=row
    job=str(uuid.uuid4())
    for sku,row in seen.items():
        if sku in dupes:
            holds.append({"sku":sku,"reason":"duplicate SKU; all rows held"});continue
        if sku not in base:
            holds.append({"sku":sku,"reason":"unknown SKU; cannot create products"});continue
        for field in ("title","price","stock"):
            if field not in ufields: continue
            raw=row[field].strip()
            if not raw:
                holds.append({"sku":sku,"field":field,"reason":"blank update; old value preserved"});continue
            try: new=price(raw) if field=="price" else stock(raw) if field=="stock" else raw
            except ValueError as ex:
                holds.append({"sku":sku,"field":field,"reason":str(ex)});continue
            old=base[sku][field]
            if new==old: continue
            reason="change requires approval"
            if field=="stock" and new=="0": reason="valid zero-stock; approval required"
            elif field=="price" and (Decimal(old)==0 or abs(Decimal(new)-Decimal(old))/Decimal(old)>Decimal("0.25")):
                reason="large price change; manual review"
            elif field=="title": reason="title change; manual review"
            changes.append((str(uuid.uuid4()),job,sku,field,old,new,"pending",reason))
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?)",(job,timestamp(),"review",digest(baseline),digest(update),json.dumps(holds)))
        c.executemany("INSERT INTO base VALUES(?,?,?,?,?)",[(job,r["sku"],r["title"],r["price"],r["stock"]) for r in base.values()])
        c.executemany("INSERT INTO changes VALUES(?,?,?,?,?,?,?,?)",changes)
        log(c,job,"ingest",{"changes":len(changes),"holds":holds})
    return {"job_id":job,"changes":len(changes),"holds":holds}
def review(db,job):
    setup(db)
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        j=c.execute("SELECT * FROM jobs WHERE id=?",(job,)).fetchone()
        if not j: raise ValueError("job not found")
        return {"job":dict(j),"holds":json.loads(j["holds"]),"changes":[dict(r) for r in c.execute("SELECT * FROM changes WHERE job=? ORDER BY sku,field",(job,))]}
def decide(db,change,decision,actor,reason):
    if decision not in ("approved","rejected") or not actor.strip() or not reason.strip():
        raise ValueError("decision, actor and reason required")
    with sqlite3.connect(db) as c:
        c.execute("BEGIN IMMEDIATE")
        row=c.execute("SELECT job,status FROM changes WHERE id=?",(change,)).fetchone()
        if not row or row[1]!="pending": raise ValueError("unknown or already decided change")
        c.execute("UPDATE changes SET status=? WHERE id=?",(decision,change))
        log(c,row[0],"decision",{"change":change,"decision":decision,"actor":actor,"reason":reason})
    return {"change":change,"decision":decision}
def export(db,job,path):
    result=review(db,job)
    if result["holds"] or any(r["status"]=="pending" for r in result["changes"]):
        raise ValueError("holds or pending decisions block export")
    path=Path(path)
    if path.exists(): raise ValueError("refusing to overwrite output")
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        rows={r["sku"]:dict(r) for r in c.execute("SELECT sku,title,price,stock FROM base WHERE job=?",(job,))}
        for change in result["changes"]:
            if change["status"]=="approved": rows[change["sku"]][change["field"]]=change["new"]
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("x",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
            writer.writerows(rows[sku] for sku in sorted(rows))
        c.execute("UPDATE jobs SET status='exported' WHERE id=?",(job,))
        log(c,job,"export",{"sha256":digest(path),"file":str(path)})
    return {"path":str(path),"sha256":digest(path),"rows":len(rows)}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",default="v3.sqlite3")
    commands=parser.add_subparsers(dest="command",required=True)
    p=commands.add_parser("ingest");p.add_argument("baseline");p.add_argument("update")
    p=commands.add_parser("review");p.add_argument("job")
    p=commands.add_parser("decide");p.add_argument("change");p.add_argument("decision",choices=["approved","rejected"]);p.add_argument("--actor",required=True);p.add_argument("--reason",required=True)
    p=commands.add_parser("export");p.add_argument("job");p.add_argument("path")
    args=parser.parse_args()
    try:
        if args.command=="ingest": result=ingest(args.db,args.baseline,args.update)
        elif args.command=="review": result=review(args.db,args.job)
        elif args.command=="decide": result=decide(args.db,args.change,args.decision,args.actor,args.reason)
        else: result=export(args.db,args.job,args.path)
        print(json.dumps(result,indent=2))
    except (ValueError,OSError,sqlite3.Error) as ex:
        print(json.dumps({"error":str(ex)}),file=sys.stderr);sys.exit(1)
if __name__=="__main__": main()
