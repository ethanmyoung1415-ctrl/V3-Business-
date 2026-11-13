from django.contrib.auth.decorators import login_required
from django.http import Http404,FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_http_methods,require_POST
from .forms import JobForm
from .models import Store,Membership,CatalogJob,CatalogEvent
from . import services,metrics
import triage
import engine

def accessible_store(user,store_id):
    store=get_object_or_404(Store,pk=store_id,active=True)
    if not Membership.objects.filter(user=user,store=store).exists():
        raise Http404()
    return store

def accessible_job(user,job_id):
    job=get_object_or_404(CatalogJob.objects.select_related("store"),pk=job_id)
    accessible_store(user,job.store_id)
    return job

@login_required
def dashboard(request):
    memberships=Membership.objects.filter(user=request.user,store__active=True).select_related("store")
    store_ids=memberships.values_list("store_id",flat=True)
    jobs=CatalogJob.objects.filter(store_id__in=store_ids).order_by("-created_at")[:100]
    operator_store_ids=memberships.filter(role=Membership.ROLE_OPERATOR).values_list("store_id",flat=True)
    attention=CatalogJob.objects.filter(
        store_id__in=operator_store_ids,
        status__in=[CatalogJob.STATUS_FAILED,CatalogJob.STATUS_REVIEW]
    ).select_related("store").order_by("created_at")[:50]
    scorecard=metrics.operator_scorecard(request.user)
    return render(request,"dashboard.html",{
        "memberships":memberships,"jobs":jobs,"operator_attention":attention,
        "scorecard":scorecard,
    })

@login_required
@require_http_methods(["GET","POST"])
def submit(request,store_id):
    store=accessible_store(request.user,store_id)
    form=JobForm(request.POST or None,request.FILES or None)
    if request.method=="POST" and form.is_valid():
        job=form.save(commit=False)
        job.store=store
        job.submitted_by=request.user
        job.status=CatalogJob.STATUS_RECEIVED
        job.save()
        CatalogEvent.objects.create(job=job,actor=request.user,kind="submitted",
                                    detail="CSV files accepted")
        return redirect("job_detail",job_id=job.id)
    return render(request,"submit.html",{"store":store,"form":form})

@login_required
def job_detail(request,job_id):
    job=accessible_job(request.user,job_id)
    can_review=Membership.objects.filter(
        user=request.user,store=job.store,role=Membership.ROLE_OPERATOR).exists()
    details=None
    if can_review and job.status==CatalogJob.STATUS_REVIEW:
        details=services.review(job,request.user)
        details["holds_with_tokens"]=engine.listed_holds(
            services.backend_db(job.store_id),str(job.engine_job_id))
        for change in details["changes"]:
            change["advice"]=triage.assess_change(change)
    events=job.portal_events.select_related("actor").order_by("-created_at")[:30]
    return render(request,"job.html",{"job":job,"details":details,
                  "can_review":can_review,"events":events})

@login_required
@require_POST
def decision(request,job_id):
    job=accessible_job(request.user,job_id)
    try:
        services.decide(job,request.user,request.POST.get("change_id",""),
                        request.POST.get("decision",""),
                        request.POST.get("reason",""))
    except (PermissionError,ValueError):
        raise Http404()
    return redirect("job_detail",job_id=job.id)

@login_required
@require_POST
def exclude_hold(request,job_id):
    job=accessible_job(request.user,job_id)
    try:
        services.exclude_held_record(
            job,request.user,request.POST.get("token",""),
            request.POST.get("reason",""))
    except (PermissionError,ValueError):
        raise Http404()
    return redirect("job_detail",job_id=job.pk)

@login_required
@require_POST
def batch_approve(request,job_id):
    job=accessible_job(request.user,job_id)
    try:
        services.approve_safe_stock_batch(job,request.user,
                                          request.POST.get("reason",""))
    except (PermissionError,ValueError):
        raise Http404()
    return redirect("job_detail",job_id=job.id)

@login_required
@require_POST
def export_job(request,job_id):
    job=accessible_job(request.user,job_id)
    try:services.prepare_export(job,request.user)
    except (PermissionError,ValueError):raise Http404()
    return redirect("job_detail",job_id=job.id)

@login_required
def download(request,job_id):
    job=accessible_job(request.user,job_id)
    try:path=services.verified_download_path(job)
    except (ValueError,OSError):raise Http404()
    CatalogEvent.objects.create(job=job,actor=request.user,kind="downloaded",
                                detail="verified_file_access")
    response=FileResponse(path.open("rb"),as_attachment=True,filename=f"{job.id}.csv")
    response["Cache-Control"]="no-store"
    response["X-Content-Type-Options"]="nosniff"
    return response
