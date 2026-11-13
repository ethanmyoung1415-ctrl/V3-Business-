"""Fail-closed recovery of portal jobs stranded by an interrupted worker."""
from datetime import timedelta
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone
from catalog_portal.models import CatalogJob,CatalogEvent

class Command(BaseCommand):
    help="Mark stale processing jobs failed for manual investigation (never auto-retry)"
    def add_arguments(self,parser):
        parser.add_argument("--minutes",type=int,default=30)
        parser.add_argument("--dry-run",action="store_true")
    def handle(self,*args,**options):
        minutes=options["minutes"]
        if not 5<=minutes<=10080:
            raise CommandError("minutes must be between 5 and 10080")
        cutoff=timezone.now()-timedelta(minutes=minutes)
        candidates=list(CatalogJob.objects.filter(
            status=CatalogJob.STATUS_PROCESSING,
            updated_at__lt=cutoff).values_list("id",flat=True))
        if options["dry_run"]:
            self.stdout.write(f"Stale processing jobs: {len(candidates)}; no changes made")
            return
        changed=0
        for pk in candidates:
            with transaction.atomic():
                count=CatalogJob.objects.filter(
                    pk=pk,status=CatalogJob.STATUS_PROCESSING,
                    updated_at__lt=cutoff).update(
                        status=CatalogJob.STATUS_FAILED,
                        error_code="worker_stalled")
                if count:
                    CatalogEvent.objects.create(job_id=pk,kind="failed",
                                                detail="worker_stalled_requires_review")
                    changed+=1
        self.stdout.write(f"Flagged {changed} stale jobs for human investigation.")
