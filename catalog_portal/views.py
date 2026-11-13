import hashlib
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.http import Http404,FileResponse,HttpResponse
from django.db import IntegrityError
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_http_methods,require_POST
from .forms import JobForm,SupplierProfileCreateForm,CustomerIssueForm,CustomerResolutionForm
from .models import Store,Membership,CatalogJob,CatalogEvent,SupplierProfile,CustomerIssue
from . import services,metrics,notices,issues,emergency
import triage
import engine
import reporting
import advice_jobs

def submitted_hash(upload):
    """Fingerprint an upload before saving it; restore its cursor for Django storage."""
    digest=hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()

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
    inbox=list(notices.visible_to(request.user)[:30])
    return render(request,"dashboard.html",{
        "memberships":memberships,"jobs":jobs,"operator_attention":attention,
        "scorecard":scorecard,"inbox":inbox,
    })

@login_required
@require_POST
def mark_notice_read(request,notice_id):
    try:
        notices.mark_read(request.user,notice_id)
    except PermissionError:
        raise Http404()
    return redirect("dashboard")

@login_required
@require_http_methods(["GET","POST"])
def configure_supplier(request,store_id):
    store=accessible_store(request.user,store_id)
    if not Membership.objects.filter(
        user=request.user,store=store,role=Membership.ROLE_OPERATOR).exists():
        raise Http404()
    form=SupplierProfileCreateForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        name=form.cleaned_data["name"].strip()
        mapping=form.cleaned_data["mapping_json"]
        if SupplierProfile.objects.filter(store=store,name=name).exists():
            form.add_error("name","A profile with this name already exists for this store.")
        else:
            try:
                SupplierProfile.objects.create(store=store,name=name,mapping=mapping)
            except IntegrityError:
                form.add_error("name","Supplier profile already exists.")
            else:
                return redirect("dashboard")
    profiles=SupplierProfile.objects.filter(store=store).order_by("name")
    return render(request,"supplier_profiles.html",
                  {"store":store,"profiles":profiles,"form":form})

@login_required
@require_http_methods(["GET","POST"])
def submit(request,store_id):
    store=accessible_store(request.user,store_id)
    form=JobForm(request.POST or None,request.FILES or None,store=store)
    if request.method=="POST" and form.is_valid():
        job=form.save(commit=False)
        job.store=store
        job.submitted_by=request.user
        job.status=CatalogJob.STATUS_RECEIVED
        profile=form.cleaned_data.get("supplier_profile")
        job.mapping_snapshot=dict(profile.mapping) if profile else {}
        if form.cleaned_data.get("use_confirmed_baseline"):
            confirmed=services.latest_confirmed(store)
            try:
                if confirmed is None:
                    raise ValueError("No confirmed catalog available")
                source_job=confirmed.job
                source=services.verified_download_path(source_job)
                if confirmed.export_sha256!=source_job.export_sha256:
                    raise ValueError("Confirmation fingerprint changed")
                with source.open("rb") as stream:
                    job.baseline.save("confirmed_baseline.csv",File(stream),save=False)
                job.baseline_sha256=engine.digest(job.baseline.path)
                job.baseline_source_job=source_job
            except (ValueError,OSError):
                form.add_error("use_confirmed_baseline",
                               "The confirmed snapshot is unavailable or failed QA; provide a new baseline.")
                return render(request,"submit.html",{"store":store,"form":form})
        else:
            job.baseline_sha256=submitted_hash(form.cleaned_data["baseline"])
        job.supplier_sha256=submitted_hash(form.cleaned_data["supplier_update"])
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
        database=services.backend_db(job.store_id)
        details["holds_with_tokens"]=engine.listed_holds(
            database,str(job.engine_job_id))
        advisories={item["change_id"]:item for item in
                    advice_jobs.read(database,str(job.engine_job_id))}
        for change in details["changes"]:
            change["advice"]=triage.assess_change(change)
            change["advisory_record"]=advisories.get(change["id"])
    events=job.portal_events.select_related("actor").order_by("-created_at")[:30]
    cases=job.catalog_issues.select_related("opened_by","resolved_by").order_by("-created_at")[:30]
    can_confirm=Membership.objects.filter(
        user=request.user,store=job.store,role=Membership.ROLE_CUSTOMER).exists()
    is_confirmed=hasattr(job,"confirmed_import")
    return render(request,"job.html",{"job":job,"details":details,
                  "can_review":can_review,"events":events,
                  "can_confirm":can_confirm,"is_confirmed":is_confirmed,
                  "cases":cases,"issue_form":CustomerIssueForm()})

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
def retry_failed(request,job_id):
    job=accessible_job(request.user,job_id)
    try:
        services.request_retry(job,request.user,request.POST.get("reason",""))
    except (PermissionError,ValueError,OSError):
        raise Http404()
    return redirect("job_detail",job_id=job.pk)

@login_required
@require_POST
def open_quality_issue(request,job_id):
    job=accessible_job(request.user,job_id)
    try:
        emergency.require_running()
    except RuntimeError:
        return HttpResponse("Service paused",status=503)
    form=CustomerIssueForm(request.POST)
    if not form.is_valid():
        raise Http404()
    try:
        issues.open_case(job,request.user,form.cleaned_data["subject"],
                         form.cleaned_data["message"])
    except (PermissionError,ValueError):
        raise Http404()
    return redirect("job_detail",job_id=job.pk)

@login_required
@require_POST
def resolve_quality_issue(request,issue_id):
    case=get_object_or_404(CustomerIssue.objects.select_related("job"),
                            pk=issue_id)
    accessible_store(request.user,case.store_id)
    form=CustomerResolutionForm(request.POST)
    if not form.is_valid():
        raise Http404()
    try:
        emergency.require_running()
        issues.resolve_case(case,request.user,form.cleaned_data["resolution"])
    except (PermissionError,ValueError):
        raise Http404()
    except RuntimeError:
        return HttpResponse("Service paused",status=503)
    return redirect("job_detail",job_id=case.job_id)

@login_required
@require_POST
def confirm_store_import(request,job_id):
    job=accessible_job(request.user,job_id)
    if request.POST.get("import_confirmed")!="yes":
        raise Http404()
    try:
        services.confirm_import(job,request.user)
    except (PermissionError,ValueError,OSError):
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
def download_report(request,job_id):
    job=accessible_job(request.user,job_id)
    try:
        path=services.verified_download_path(job)
        document=reporting.generate(services.backend_db(job.store_id),
                                    str(job.engine_job_id),path)
    except (ValueError,OSError):
        raise Http404()
    response=HttpResponse(reporting.serialize(document),
                          content_type="application/json; charset=utf-8")
    response["Content-Disposition"]=f'attachment; filename="{job.id}-change-report.json"'
    response["Cache-Control"]="no-store"
    response["X-Content-Type-Options"]="nosniff"
    return response

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
