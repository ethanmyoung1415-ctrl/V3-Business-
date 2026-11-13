"""Run the development portal's received-job processor in a polling loop."""
import signal
import time
from django.core.management.base import BaseCommand,CommandError
from django.core.management import call_command
from catalog_portal.services import process_received_batch

class Command(BaseCommand):
    help="Run local synthetic catalog jobs; no live store writes or external communications"
    def add_arguments(self,parser):
        parser.add_argument("--limit",type=int,default=10)
        parser.add_argument("--interval",type=float,default=5.0)
        parser.add_argument("--once",action="store_true")
    def handle(self,*args,**options):
        interval=options["interval"]
        limit=options["limit"]
        if not 0.1<=interval<=3600 or not 1<=limit<=100:
            raise CommandError("invalid interval or batch size")
        stop=False
        def stop_requested(*_):
            nonlocal stop
            stop=True
        signal.signal(signal.SIGINT,stop_requested)
        signal.signal(signal.SIGTERM,stop_requested)
        while not stop:
            # Crash recovery does not retry or approve anything; stranded jobs
            # become visible as failures for operator investigation.
            call_command("reconcile_stale_jobs", "--minutes", "30", stdout=self.stdout)
            result=process_received_batch(limit)
            call_command("reconcile_notices", "--limit", "500", stdout=self.stdout)
            if result:
                self.stdout.write(f"Processed {len(result)} submission(s)")
            if options["once"]:break
            end=time.monotonic()+interval
            while not stop and time.monotonic()<end:
                time.sleep(min(0.2,max(0,end-time.monotonic())))
