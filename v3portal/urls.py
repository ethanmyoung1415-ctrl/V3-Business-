from django.contrib.auth import views as auth_views
from django.urls import path
from catalog_portal import views
urlpatterns=[
    path("login/",auth_views.LoginView.as_view(template_name="login.html"),name="login"),
    path("join-local-demo/",views.join_local_demo,name="join_local_demo"),
    path("logout/",auth_views.LogoutView.as_view(),name="logout"),
    path("",views.dashboard,name="dashboard"),
    path("notices/<uuid:notice_id>/read/",views.mark_notice_read,name="mark_notice_read"),
    path("stores/<uuid:store_id>/submit/",views.submit,name="submit"),
    path("stores/<uuid:store_id>/supplier-profiles/",views.configure_supplier,name="configure_supplier"),
    path("jobs/<uuid:job_id>/",views.job_detail,name="job_detail"),
    path("jobs/<uuid:job_id>/automation-preview/",views.automation_preview,name="automation_preview"),
    path("jobs/<uuid:job_id>/decide/",views.decision,name="decision"),
    path("jobs/<uuid:job_id>/export/",views.export_job,name="export_job"),
    path("jobs/<uuid:job_id>/batch-approve/",views.batch_approve,name="batch_approve"),
    path("jobs/<uuid:job_id>/exclude-hold/",views.exclude_hold,name="exclude_hold"),
    path("jobs/<uuid:job_id>/retry/",views.retry_failed,name="retry_failed"),
    path("jobs/<uuid:job_id>/confirm-import/",views.confirm_store_import,name="confirm_import"),
    path("jobs/<uuid:job_id>/issue/",views.open_quality_issue,name="open_quality_issue"),
    path("issues/<uuid:issue_id>/resolve/",views.resolve_quality_issue,name="resolve_quality_issue"),
    path("jobs/<uuid:job_id>/download/",views.download,name="download"),
    path("jobs/<uuid:job_id>/report/",views.download_report,name="download_report"),
]
