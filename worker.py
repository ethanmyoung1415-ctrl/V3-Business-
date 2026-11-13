"""Local polling worker: analyzes queued files, but cannot approve, export or contact customers."""
import argparse
import json
import signal
import time
import operations
import inbox

def run(db,interval=5.0,max_cycles=None,inbox_dir=None):
    if interval<0.1 or interval>3600: raise ValueError("interval must be 0.1 to 3600 seconds")
    stop=False
    def request_stop(*_):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGINT,request_stop)
    signal.signal(signal.SIGTERM,request_stop)
    cycles=0
    while not stop and (max_cycles is None or cycles<max_cycles):
        if inbox_dir is not None:
            intake_result=inbox.scan(db,inbox_dir)
            if intake_result["enqueued"] or intake_result["errors"]:
                print(json.dumps({"inbox":intake_result},sort_keys=True),flush=True)
        result=operations.work_once(db)
        print(json.dumps(result,sort_keys=True),flush=True)
        cycles+=1
        if stop or (max_cycles is not None and cycles>=max_cycles):break
        if result["status"]=="idle":
            # Sleep in small increments to respond quickly to a shutdown signal.
            end=time.monotonic()+interval
            while not stop and time.monotonic()<end:
                time.sleep(min(0.2,end-time.monotonic()))
    return cycles

def main():
    p=argparse.ArgumentParser(description="Local V3 queue worker; NO live customer actions")
    p.add_argument("--db",default="v3.sqlite3")
    p.add_argument("--interval",type=float,default=5.0)
    p.add_argument("--max-cycles",type=int)
    p.add_argument("--inbox",help="local synthetic READY-job inbox")
    a=p.parse_args()
    if a.max_cycles is not None and a.max_cycles<1:p.error("--max-cycles must be positive")
    run(a.db,a.interval,a.max_cycles,a.inbox)
if __name__=="__main__":main()
