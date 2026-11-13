"""Private local V3 health summary for synthetic portal operations.

Does not examine supplier data values or print credentials. Thresholds are
diagnostic heuristics, not promises of commercial SLA performance.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from .models import CatalogJob,Store,PortalNotice

def snapshot(now=None):
    clock=now or timezone.now()
    statuses=dict(CatalogJob.objects.values("status").annotate(
        total=Count("id")).values_list("status","total"))
    stale=CatalogJob.objects.filter(
        status=CatalogJob.STATUS_PROCESSING,
        updated_at__lt=clock-timedelta(minutes=30)).count()
    overdue_queue=CatalogJob.objects.filter(
        status=CatalogJob.STATUS_RECEIVED,
        created_at__lt=clock-timedelta(minutes=15)).count()
    old_review=CatalogJob.objects.filter(
        status=CatalogJob.STATUS_REVIEW,
        updated_at__lt=clock-timedelta(hours=24)).count()
    failed=statuses.get(CatalogJob.STATUS_FAILED,0)
    ready=statuses.get(CatalogJob.STATUS_READY,0)
    reasons=list(
        CatalogJob.objects.filter(status=CatalogJob.STATUS_FAILED)
        .values("error_code").annotate(total=Count("id"))
        .order_by("error_code"))
    # Never include identities, file names, SKU values, customer names or IPs.
    checks={
        "stale_processing":stale,
        "queued_longer_than_15m":overdue_queue,
        "review_older_than_24h":old_review,
        "failed_jobs":failed,
        "ready_outputs":ready,
        "active_stores":Store.objects.filter(active=True).count(),
        "unread_notification_events":PortalNotice.objects.count(),
    }
    severity=("critical" if stale or failed else
              "attention" if overdue_queue or old_review else "healthy")
    return {
        "generated_at":clock.isoformat(),
        "scope":"synthetic_local_only",
        "status":severity,
        "checks":checks,
        "queue_status_counts":statuses,
        "failed_error_categories":reasons,
        "limitations":[
            "No cloud uptime, network, cost or encryption monitoring",
            "Notification count is events, not per-user unread totals",
            "Ready status alone does not certify remote-store import",
        ],
    }
