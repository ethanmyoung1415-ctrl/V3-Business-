"""Local-only, single-use synthetic customer enrollment.

No public signup, email delivery or production identity federation.
The bearer invitation is generated randomly and stored only as SHA-256.
"""
import hashlib
import re
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from .models import Membership,StoreInvitation

USER_NAME=re.compile(r"^[a-z0-9._-]{3,50}$")

def _ensure_local():
    if not getattr(settings,"LOCAL_DEV",False):
        raise PermissionError("customer enrollment disabled outside local simulation")

def issue(store,operator,hours=24):
    _ensure_local()
    if type(hours) is not int or not 1<=hours<=72:
        raise ValueError("invalid invitation lifetime")
    if not store.active or not operator.is_authenticated or not Membership.objects.filter(
            user=operator,store=store,role=Membership.ROLE_OPERATOR).exists():
        raise PermissionError("only authorized operators may invite customers")
    raw=secrets.token_urlsafe(32)
    digest=hashlib.sha256(raw.encode("ascii")).hexdigest()
    invitation=StoreInvitation.objects.create(
        store=store,created_by=operator,token_sha256=digest,
        expires_at=timezone.now()+timedelta(hours=hours))
    return {"invitation_id":str(invitation.id),"code":raw,
            "expires_at":invitation.expires_at.isoformat(),
            "note":"One-time synthetic local code; transfer privately and never commit."}

def redeem(code,username,password):
    _ensure_local()
    if not isinstance(code,str) or not 30<=len(code)<=100:
        raise ValueError("invalid or expired invitation")
    if not isinstance(username,str):
        raise ValueError("invalid username")
    name=username.casefold().strip()
    if not USER_NAME.fullmatch(name):
        raise ValueError("username must be 3–50 simple characters")
    User=get_user_model()
    new_user=User(username=name)
    validate_password(password,user=new_user)
    hashed=hashlib.sha256(code.encode("utf-8")).hexdigest()
    now=timezone.now()
    with transaction.atomic():
        invitation=(StoreInvitation.objects.select_related("store")
                    .filter(token_sha256=hashed).first())
        if (not invitation or invitation.redeemed_at is not None
                or invitation.expires_at<=now or not invitation.store.active):
            raise ValueError("invalid or expired invitation")
        # Conditional claim is safe even on SQLite where SELECT FOR UPDATE
        # does not provide row locks.
        claimed=StoreInvitation.objects.filter(
            pk=invitation.pk,redeemed_at__isnull=True,expires_at__gt=now
        ).update(redeemed_at=now)
        if claimed!=1:raise ValueError("invitation already redeemed")
        if User.objects.filter(username__iexact=name).exists():
            raise ValueError("username unavailable")
        new_user.set_password(password)
        new_user.save()
        Membership.objects.create(
            user=new_user,store=invitation.store,role=Membership.ROLE_CUSTOMER)
        invitation.redeemed_by=new_user
        invitation.save(update_fields=["redeemed_by"])
    return {"user_id":new_user.pk,"store_id":str(invitation.store_id),
            "role":"customer"}
