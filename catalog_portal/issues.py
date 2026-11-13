"""Private local quality-case workflow with explicit store memberships."""
from django.db import transaction
from django.utils import timezone
from .models import CustomerIssue,Membership,CatalogEvent

def open_case(job,user,subject,message):
    if (not getattr(user,"is_authenticated",False) or
            not Membership.objects.filter(user=user,store_id=job.store_id).exists()):
        raise PermissionError("store membership required")
    if (not isinstance(subject,str) or not 5<=len(subject.strip())<=120 or
            not isinstance(message,str) or not 15<=len(message.strip())<=500):
        raise ValueError("subject and message lengths invalid")
    if "\x00" in subject or "\x00" in message:
        raise ValueError("invalid message text")
    with transaction.atomic():
        issue=CustomerIssue.objects.create(
            store=job.store,job=job,opened_by=user,
            subject=subject.strip(),message=message.strip())
        CatalogEvent.objects.create(
            job=job,actor=user,kind="issue_opened",
            detail="local_quality_case:"+str(issue.pk))
    return issue

def resolve_case(issue,user,resolution):
    if not getattr(user,"is_authenticated",False) or not Membership.objects.filter(
            user=user,store_id=issue.store_id,
            role=Membership.ROLE_OPERATOR).exists():
        raise PermissionError("operator role required")
    if not isinstance(resolution,str) or not 12<=len(resolution.strip())<=500:
        raise ValueError("meaningful resolution required")
    if "\x00" in resolution:raise ValueError("invalid resolution")
    with transaction.atomic():
        changed=CustomerIssue.objects.filter(
            pk=issue.pk,status=CustomerIssue.STATUS_OPEN).update(
                status=CustomerIssue.STATUS_RESOLVED,resolution=resolution.strip(),
                resolved_by=user,resolved_at=timezone.now())
        if not changed:raise ValueError("issue already resolved")
        CatalogEvent.objects.create(
            job=issue.job,actor=user,kind="issue_resolved",
            detail="local_quality_case:"+str(issue.pk))
    return {"issue_id":str(issue.pk),"resolved":True}
