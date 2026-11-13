from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from catalog_portal import views
urlpatterns=[
    path("admin/",admin.site.urls),
    path("login/",auth_views.LoginView.as_view(template_name="login.html"),name="login"),
    path("logout/",auth_views.LogoutView.as_view(),name="logout"),
    path("",views.dashboard,name="dashboard"),
    path("stores/<uuid:store_id>/submit/",views.submit,name="submit"),
    path("jobs/<uuid:job_id>/",views.job_detail,name="job_detail"),
    path("jobs/<uuid:job_id>/decide/",views.decision,name="decision"),
    path("jobs/<uuid:job_id>/export/",views.export_job,name="export_job"),
    path("jobs/<uuid:job_id>/batch-approve/",views.batch_approve,name="batch_approve"),
    path("jobs/<uuid:job_id>/exclude-hold/",views.exclude_hold,name="exclude_hold"),
    path("jobs/<uuid:job_id>/download/",views.download,name="download"),
    path("jobs/<uuid:job_id>/report/",views.download_report,name="download_report"),
]
