"""Purge old *synthetic* uploaded source files after terminal jobs.

This is deliberately disabled outside V3_LOCAL_DEV. It does not purge
the engine workspace or exports and is NOT a complete privacy erasure process.
Dry-run is the default; deletion requires --confirm.
"""
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from catalog_portal.models import CatalogJob,CatalogEvent

class Command(BaseCommand):
    help="List or remove old demo source CSVs (never run against real customer data)"
    def add_arguments(self,parser):
        parser.add_argument("--days",type=int,default=30)
        parser.add_argument("--confirm",action="store_true")
    def handle(self,*args,**options):
        if not getattr(settings,"LOCAL_DEV",False):
            raise CommandError("purging is unavailable outside local demo")
        if options["days"]<1:
            raise CommandError("days must be at least one")
        root=Path(settings.MEDIA_ROOT).resolve()
        cutoff=timezone.now()-timedelta(days=options["days"])
        queryset=CatalogJob.objects.filter(
            status__in=[CatalogJob.STATUS_READY,CatalogJob.STATUS_FAILED],
            updated_at__lt=cutoff).select_related("store").order_by("created_at")
        files=[]
        for job in queryset:
            for field in (job.baseline,job.supplier_update):
                if not field.name:continue
                candidate=Path(field.path).resolve()
                if root not in candidate.parents:
                    raise CommandError("unexpected upload path outside media root")
                if not candidate.is_file():continue
                files.append((job,candidate,field))
        self.stdout.write(f"Eligible demo source files: {len(files)}")
        if not options["confirm"]:
            self.stdout.write("Dry run. Pass --confirm to delete eligible local demo uploads.")
            return
        for job,path,field in files:
            path.unlink()
            # Keep the file name for audit, but mark it inaccessible.
            CatalogEvent.objects.create(job=job,kind="failed",
                                        detail="demo_source_removed")
        self.stdout.write(f"Deleted {len(files)} local demo source files.")
