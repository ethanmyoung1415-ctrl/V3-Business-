"""Private in-portal status notices. No email, SMS, or external sending."""
from django.db.models import Q
from .models import Membership,PortalNotice,NoticeRead

NOTICE_TYPES={
    ("needs_review","operator"),
    ("job_failed","operator"),
    ("job_failed","customer"),
    ("export_ready","customer"),
}

def create(job,kind,audience):
    if (kind,audience) not in NOTICE_TYPES:
        raise ValueError("unsupported notice type/audience")
    required_status={"needs_review":"review","job_failed":"failed",
                     "export_ready":"ready"}[kind]
    if job.status!=required_status:
        raise ValueError("notice must match a confirmed job state")
    key=f"{job.pk}:{kind}:{audience}"
    notice,_=PortalNotice.objects.get_or_create(
        dedupe_key=key,defaults={
            "store":job.store,"job":job,"kind":kind,"audience":audience,
        })
    if notice.store_id!=job.store_id or notice.job_id!=job.pk:
        raise ValueError("notification tenant mismatch")
    return notice

def visible_to(user):
    if not getattr(user,"is_authenticated",False):
        raise PermissionError("authentication required")
    memberships=Membership.objects.filter(user=user,store__active=True)
    member_ids=memberships.values_list("store_id",flat=True)
    operator_ids=memberships.filter(role=Membership.ROLE_OPERATOR).values_list(
        "store_id",flat=True)
    return PortalNotice.objects.filter(
        Q(store_id__in=member_ids,audience="customer") |
        Q(store_id__in=operator_ids,audience="operator")
    ).exclude(read_receipts__user=user).select_related("store","job").order_by("-created_at")

def mark_read(user,notice_id):
    notice=visible_to(user).filter(pk=notice_id).first()
    if notice is None:
        raise PermissionError("notice unavailable or already read")
    NoticeRead.objects.get_or_create(notice=notice,user=user)
    return {"notice_id":str(notice.pk),"read":True}
