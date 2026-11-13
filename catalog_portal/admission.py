"""Local synthetic-data submission admission policy.

Bound request creation before file validation/storage. This is useful defense
in depth, not a distributed production rate limiter: parallel workers can
race without a shared atomic quota backend.
"""
from datetime import timedelta
from django.utils import timezone
from .models import CatalogJob

MAX_ACTIVE_PER_STORE=25
MAX_STORE_SUBMISSIONS_PER_HOUR=40
MAX_USER_SUBMISSIONS_PER_HOUR=20

ACTIVE_STATUSES=(
    CatalogJob.STATUS_RECEIVED,
    CatalogJob.STATUS_PROCESSING,
    CatalogJob.STATUS_REVIEW,
)

def check(store,user,*,now=None):
    clock=now or timezone.now()
    hourly=clock-timedelta(hours=1)
    active=CatalogJob.objects.filter(
        store=store,status__in=ACTIVE_STATUSES).count()
    store_recent=CatalogJob.objects.filter(
        store=store,created_at__gte=hourly).count()
    user_recent=CatalogJob.objects.filter(
        store=store,submitted_by=user,created_at__gte=hourly).count()
    checks={
        "active_jobs":active,
        "store_recent_jobs":store_recent,
        "user_recent_jobs":user_recent,
    }
    reason=None
    if active>=MAX_ACTIVE_PER_STORE:
        reason="active_store_queue_limit"
    elif store_recent>=MAX_STORE_SUBMISSIONS_PER_HOUR:
        reason="store_hourly_submission_limit"
    elif user_recent>=MAX_USER_SUBMISSIONS_PER_HOUR:
        reason="user_hourly_submission_limit"
    return {"allowed":reason is None,"reason":reason,
            "counts":checks,"retry_after_seconds":3600 if reason else 0}

def assert_allowed(store,user,*,now=None):
    result=check(store,user,now=now)
    if not result["allowed"]:
        raise PermissionError("submission quota reached")
    return result
