"""Idempotently backfill synthetic in-app notices after interrupted jobs."""
from django.core.management.base import BaseCommand,CommandError
from catalog_portal.models import CatalogJob
from catalog_portal import notices

class Command(BaseCommand):
    help="Reconcile local private notices from durable job statuses"
    def add_arguments(self,parser):
        parser.add_argument("--limit",type=int,default=500)
    def handle(self,*args,**options):
        limit=options["limit"]
        if not 1<=limit<=5000:
            raise CommandError("limit must be between 1 and 5000")
        jobs=CatalogJob.objects.filter(
            status__in=["review","failed","ready"]
        ).order_by("-updated_at")[:limit]
        count=0
        for job in jobs:
            pairs=(
                [("needs_review","operator")] if job.status=="review" else
                [("job_failed","operator"),("job_failed","customer")]
                if job.status=="failed" else
                [("export_ready","customer")]
            )
            for kind,audience in pairs:
                notices.create(job,kind,audience)
                count+=1
        self.stdout.write(f"Checked {count} private notice states.")
