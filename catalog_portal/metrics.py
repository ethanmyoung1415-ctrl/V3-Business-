"""Tenant-authorized local operator management scorecard."""
from django.db.models import Count
from .models import Membership,CatalogJob,CatalogEvent

def operator_scorecard(user):
    if not user.is_authenticated:
        raise PermissionError("authentication required")
    store_ids=Membership.objects.filter(
        user=user,role=Membership.ROLE_OPERATOR,store__active=True
    ).values_list("store_id",flat=True)
    jobs=CatalogJob.objects.filter(store_id__in=store_ids)
    statuses=dict(jobs.values("status").annotate(total=Count("id")).values_list("status","total"))
    events=CatalogEvent.objects.filter(job__store_id__in=store_ids)
    event_counts=dict(events.values("kind").annotate(total=Count("id")).values_list("kind","total"))
    total=sum(statuses.values())
    failed=statuses.get(CatalogJob.STATUS_FAILED,0)
    review=statuses.get(CatalogJob.STATUS_REVIEW,0)
    ready=statuses.get(CatalogJob.STATUS_READY,0)
    return {
        "scope":"authorized_operator_stores_only",
        "jobs_total":total,
        "jobs_failed":failed,
        "jobs_awaiting_review":review,
        "verified_exports_ready":ready,
        "operator_attention_jobs":failed+review,
        "status_counts":statuses,
        "event_counts":event_counts,
        "monthly_revenue":None,
        "gross_margin":None,
        "note":"Local counts only; no billing, customer-retention, or profit data exists.",
    }
