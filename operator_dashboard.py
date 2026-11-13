"""Local-only V3 browser console. Never expose to an external network."""
import argparse,html,secrets,sqlite3,json,uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlparse
import engine,operations,triage,qa,metrics

def esc(value): return html.escape(str(value),quote=True)
def document(content):
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>V3 Operator</title><style>
body{font:15px system-ui,sans-serif;max-width:1050px;margin:25px auto;padding:20px;color:#1d2939;background:#f5f7fb}
section{background:white;border:1px solid #d7deea;padding:20px;margin:16px 0;border-radius:12px}
h1{font-size:25px}h2{font-size:19px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{border-bottom:1px solid #e4e8f0;padding:9px;text-align:left}
input,button{padding:8px;margin:3px;border:1px solid #ccd3de;border-radius:5px}button{background:#1b4888;color:white;cursor:pointer}
small{color:#667085}code{overflow-wrap:anywhere}.warning{color:#9d2b2b}
@media(max-width:700px){table{display:block;overflow-x:auto}}
</style></head><body><h1>V3 Operations Guard</h1><small>LOCAL PROTOTYPE · NOT A CUSTOMER PORTAL</small>"""
    +content+"</body></html>")
def overview(db):
    stats=operations.dashboard(db)
    counts=stats['counts']
    report=metrics.snapshot(db)
    totals=report["totals"]
    badges=' '.join(f'<strong>{esc(k)}: {v}</strong> ' for k,v in sorted(counts.items()))
    status='<h2>Operator attention</h2><p>Operational status: <strong>'+esc(report["operational_status"])+'</strong></p>'
    status+=('<p>Pending decisions: '+str(totals["pending_decisions"])+
             ' · Unresolved holds: '+str(totals["unresolved_holds"])+
             ' · Failed jobs: '+str(totals["failed_jobs"])+'</p>')
    attention=[]
    for item in report["attention"]:
        link=(f'<a href="/job/{esc(item["job_id"])}">Review</a>'
              if item["job_id"] else 'Investigate failure')
        attention.append('<tr><td>'+esc(item["work_id"][:12])+'</td><td>'+esc(item["status"])+
            '</td><td>'+str(item["pending_decisions"])+'</td><td>'+
            str(item["unresolved_holds"])+'</td><td>'+link+'</td></tr>')
    status+='<table><tr><th>Work</th><th>Status</th><th>Pending</th><th>Holds</th><th>Action</th></tr>'+''.join(attention)+'</table>'

    rows=[]
    for j in stats['jobs']:
        link=f'<a href="/job/{esc(j["engine_job_id"])}">Review changes</a>' if j.get('engine_job_id') else '—'
        rows.append(f'<tr><td><code>{esc(j["id"][:12])}</code></td><td>{esc(j["status"])}</td><td>{esc(j.get("pending_decisions",0))}</td><td>{esc(j.get("holds",0))}</td><td>{esc(j.get("last_error") or "—")}</td><td>{link}</td></tr>')
    return document('<section><h2>Overview</h2>'+badges+'</section><section>'+status+'</section><section><h2>Jobs</h2><table><tr><th>ID</th><th>Status</th><th>Pending</th><th>Holds</th><th>Last error</th><th>Action</th></tr>'+''.join(rows)+'</table></section>')
def output_path(db,job):
    canonical=str(uuid.UUID(job))
    if canonical!=job:raise ValueError("invalid job identifier")
    return Path(db).resolve().parent/"exports"/(canonical+".csv")

def job_page(db,job,csrf,notice=''):
    r=engine.review(db,job)
    holds=''.join(f'<li>{esc(json.dumps(h))}</li>' for h in r['holds'])
    rows=[]
    for c in r['changes']:
        forms=''
        if c['status']=='pending':
            for decision in ('approved','rejected'):
                forms+=f"""<form action="/decide" method="post">
<input type="hidden" name="csrf" value="{esc(csrf)}"><input type="hidden" name="job" value="{esc(job)}">
<input type="hidden" name="change" value="{esc(c['id'])}"><input type="hidden" name="decision" value="{decision}">
<input name="reason" placeholder="Reason (required)" maxlength="300" required><button type="submit">{decision.capitalize()}</button></form>"""
        advice=triage.assess_change(c)
        forms+=('<p><small>Risk: '+esc(advice["risk"])+' | Suggested: '+
                esc(advice["recommendation"])+' — '+esc(advice["explanation"])+'</small></p>')
        rows.append('<tr>'+''.join(f'<td>{esc(c[key])}</td>' for key in ('sku','field','old','new','status','reason'))+f'<td>{forms}</td></tr>')
    can_export=not r["holds"] and not any(c["status"]=="pending" for c in r["changes"])
    export_html=""
    if can_export:
        if output_path(db,job).exists():
            export_html=f'<p><a href="/download/{esc(job)}">Download independently verified CSV</a></p>'
        else:
            export_html=(f'<form method="post" action="/export"><input type="hidden" name="csrf" value="{esc(csrf)}">'
                         f'<input type="hidden" name="job" value="{esc(job)}">'
                         '<button type="submit">Prepare independently verified CSV</button></form>')
    return document(f'<p><a href="/">← All jobs</a></p>{export_html}<section><h2>Job {esc(job[:12])}</h2><p>{esc(notice)}</p><h3>Unresolved holds ({len(r["holds"])})</h3><ul>{holds}</ul><h3>Proposed changes</h3><table><tr><th>SKU</th><th>Field</th><th>Old</th><th>Proposed</th><th>Status</th><th>Reason</th><th>Decision</th></tr>{"".join(rows)}</table></section>')
def make_handler(db,csrf,actor):
    class Handler(BaseHTTPRequestHandler):
        def _trusted_host(self):
            host=self.headers.get('Host','')
            # Reject DNS rebinding and requests routed via non-loopback hostnames.
            return host in ('localhost','127.0.0.1',
                            f'localhost:{self.server.server_port}',
                            f'127.0.0.1:{self.server.server_port}')
        def _trusted_origin(self):
            origin=self.headers.get('Origin')
            return not origin or origin in (
                f'http://localhost:{self.server.server_port}',
                f'http://127.0.0.1:{self.server.server_port}')
        def answer(self,body,status=200):
            b=body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(b)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(b)
        def do_GET(self):
            if not self._trusted_host():return self.send_error(403)
            path=urlparse(self.path).path
            try:
                if path=='/':self.answer(overview(db))
                elif path.startswith('/job/'):self.answer(job_page(db,path[5:],csrf))
                elif path.startswith('/download/'):
                    job=path[len('/download/'):]
                    file=output_path(db,job)
                    if not file.exists():return self.send_error(404)
                    verification=qa.verify(db,job,file)
                    if not verification["passed"]:raise ValueError("export failed independent verification")
                    b=file.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type","text/csv; charset=utf-8")
                    self.send_header("Content-Disposition",f'attachment; filename="{job}.csv"')
                    self.send_header("Content-Length",str(len(b)))
                    self.send_header("Cache-Control","no-store")
                    self.send_header("X-Content-Type-Options","nosniff")
                    self.end_headers()
                    self.wfile.write(b)
                else:self.send_error(404)
            except (ValueError,sqlite3.Error) as ex:self.answer(document(f'<section>{esc(ex)}</section>'),400)
        def do_POST(self):
            if not self._trusted_host() or not self._trusted_origin():return self.send_error(403)
            route=urlparse(self.path).path
            if route not in ('/decide','/export'):return self.send_error(404)
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=16384:return self.send_error(413)
                if self.headers.get('Content-Type','').split(';')[0].strip()!='application/x-www-form-urlencoded':
                    return self.send_error(415)
                form=parse_qs(self.rfile.read(n).decode('utf-8'),strict_parsing=True)
                one=lambda key: form[key][0] if len(form.get(key,[]))==1 else ''
                if not secrets.compare_digest(one('csrf'),csrf):return self.send_error(403)
                if route=="/export":
                    job=one("job")
                    file=output_path(db,job)
                    if file.exists():raise ValueError("export already exists")
                    engine.export(db,job,file)
                    self.answer(job_page(db,job,csrf,"Independent QA passed; CSV ready to download"))
                    return
                job,change,decision,reason=(one(k) for k in ('job','change','decision','reason'))
                if not job or not change or not reason.strip() or decision not in ('approved','rejected'):
                    raise ValueError('incomplete decision')
                if change not in {r['id'] for r in engine.review(db,job)['changes']}:
                    raise ValueError('change belongs to a different job')
                engine.decide(db,change,decision,actor,reason)
                self.answer(job_page(db,job,csrf,'Decision recorded'))
            except (KeyError,ValueError,UnicodeError,sqlite3.Error) as ex:
                self.answer(document(f'<section>{esc(ex)}</section>'),400)
    return Handler
def start(db,port,actor):
    if not actor.strip():raise ValueError('actor required')
    operations.setup(db)
    token=secrets.token_urlsafe(32)
    server=ThreadingHTTPServer(('127.0.0.1',port),make_handler(db,token,actor))
    print(f'Open http://127.0.0.1:{server.server_port}/ — Ctrl+C to stop',flush=True)
    server.serve_forever()
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--db',default='v3.sqlite3');p.add_argument('--port',type=int,default=8765);p.add_argument('--actor',default='local-operator')
    a=p.parse_args();start(a.db,a.port,a.actor)
