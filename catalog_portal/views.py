from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_http_methods
from .forms import JobForm
from .models import Store,Membership,CatalogJob

def accessible_store(user,store_id):
    store=get_object_or_404(Store,pk=store_id,active=True)
    if not Membership.objects.filter(user=user,store=store).exists():
        raise Http404()
    return store

@login_required
def dashboard(request):
    memberships=Membership.objects.filter(user=request.user,store__active=True).select_related("store")
    store_ids=memberships.values_list("store_id",flat=True)
    jobs=CatalogJob.objects.filter(store_id__in=store_ids).order_by("-created_at")[:100]
    return render(request,"dashboard.html",{"memberships":memberships,"jobs":jobs})

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
        return redirect("job_detail",job_id=job.id)
    return render(request,"submit.html",{"store":store,"form":form})

@login_required
def job_detail(request,job_id):
    job=get_object_or_404(CatalogJob.objects.select_related("store"),pk=job_id)
    accessible_store(request.user,job.store_id)
    return render(request,"job.html",{"job":job})
