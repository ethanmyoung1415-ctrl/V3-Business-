"""Start the local V3 operator console and polling worker together.

No external connectivity, hosted service, or live store write is enabled.
"""
import argparse
import multiprocessing
import operator_dashboard
import worker

def start(db,port,actor,interval):
    process=multiprocessing.Process(target=worker.run,args=(db,interval),daemon=True)
    process.start()
    try:
        operator_dashboard.start(db,port,actor)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill();process.join(timeout=2)
def main():
    p=argparse.ArgumentParser(description="V3 local operator app, sample data only")
    p.add_argument("--db",default="v3.sqlite3")
    p.add_argument("--port",type=int,default=8765)
    p.add_argument("--actor",default="local-operator")
    p.add_argument("--interval",type=float,default=3.0)
    a=p.parse_args()
    if a.interval<0.1 or a.interval>3600:p.error("interval must be 0.1–3600 seconds")
    start(a.db,a.port,a.actor,a.interval)
if __name__=="__main__":main()
