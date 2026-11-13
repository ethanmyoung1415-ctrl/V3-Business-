"""Portal-to-engine bridge for synthetic, locally hosted development only.

Intake remains private and tenant-specific. No billing, live-store write,
customer notification or autonomous approval is implemented.
"""
import sqlite3
import uuid
from pathlib import Path
from django.conf import settings
from django.db import transaction
import engine
import intake
import mapping as mapper
import qa
import advice_jobs
from .models import CatalogJob,Membership,CatalogEvent
from . import notices

def backend_db(store_id):
    identifier=str(uuid.UUID(str(store_id)))
    root=Path(getattr(settings,"V3_WORKSPACE_ROOT",settings.BASE_DIR/".local_workspaces"))
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.is_symlink():raise ValueError("linked workspace root denied")
    directory=root/identifier
    if directory.is_symlink():raise ValueError("linked tenant directory denied")
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    return directory/"engine.sqlite3"

def require_operator(user,job):
    if not user.is_authenticated or not Membership.objects.filter(
            user=user,store_id=job.store_id,role=Membership.ROLE_OPERATOR).exists():
        raise PermissionError("operator permission required")

def process_received(job_id):
    """Claim exactly one pending portal upload; crash remains fail-closed."""
    with transaction.atomic():
        updated=CatalogJob.objects.filter(
            pk=job_id,status=CatalogJob.STATUS_RECEIVED).update(
                status=CatalogJob.STATUS_PROCESSING)
        if updated!=1:return {"processed":False,"reason":"not_received"}
    job=CatalogJob.objects.get(pk=job_id)
    try:
        database=backend_db(job.store_id)
        if not job.baseline_sha256 or not job.supplier_sha256:
            raise ValueError("source submission lacks required hashes")
        if (engine.digest(job.baseline.path)!=job.baseline_sha256 or
                engine.digest(job.supplier_update.path)!=job.supplier_sha256):
            raise ValueError("original upload changed since submission")
        snapshots=intake.stage_pair(job.baseline.path,job.supplier_update.path,database)
        if (snapshots[0][1]!=job.baseline_sha256 or
                snapshots[1][1]!=job.supplier_sha256):
            raise ValueError("staged source differs from submitted upload")
        supplier_input=snapshots[1][0]
        if job.mapping_snapshot:
            mapper.validate_mapping(job.mapping_snapshot)
            converted=supplier_input.parent/(str(uuid.uuid4())+"-normalized.csv")
            mapper.normalize_csv(supplier_input,converted,job.mapping_snapshot)
            supplier_input=converted
        result=engine.ingest(database,snapshots[0][0],supplier_input,
                             job_id=str(job.pk))
        job.engine_job_id=uuid.UUID(result["job_id"])
        job.status=CatalogJob.STATUS_REVIEW
        job.error_code=""
        job.save(update_fields=["engine_job_id","status","error_code","updated_at"])
        CatalogEvent.objects.create(job=job,kind="processed",detail="ready_for_operator_review")
        notices.create(job,"needs_review","operator")
        # Advisory work is optional. It MUST NOT alter a job's result or
        # change its approval state when unavailable.
        try:
            outcome=advice_jobs.prepare(database,result["job_id"],max_items=100)
            CatalogEvent.objects.create(
                job=job,kind="advisory",
                detail="read_only_suggestions:"+str(outcome["prepared"]))
        except Exception:
            CatalogEvent.objects.create(
                job=job,kind="advisory",detail="unavailable_deterministic_review_still_possible")
        return {"processed":True,"status":"review","job_id":str(job.id),
                "engine_job_id":result["job_id"],
                "holds":len(result["holds"]),"changes":result["changes"]}
    except Exception as exc:
        # Public errors use opaque categories: never echo supplier contents.
        job.status=CatalogJob.STATUS_FAILED
        if isinstance(exc,ValueError):
            job.error_code="invalid_input"
        elif isinstance(exc,OSError):
            job.error_code="storage_failure"
        else:
            job.error_code="processing_error"
        job.save(update_fields=["status","error_code","updated_at"])
        CatalogEvent.objects.create(job=job,kind="failed",detail="processing_error")
        # Failure alerts are best-effort; the original processing error stays primary.
        try:
            notices.create(job,"job_failed","operator")
            notices.create(job,"job_failed","customer")
        except Exception:
            pass
        raise

def process_received_batch(max_jobs=10):
    if not 1<=max_jobs<=100:raise ValueError("invalid batch size")
    ids=CatalogJob.objects.filter(status=CatalogJob.STATUS_RECEIVED).order_by(
        "created_at").values_list("id",flat=True)[:max_jobs]
    results=[]
    for job_id in ids:
        try:results.append(process_received(job_id))
        except Exception:results.append({"job_id":str(job_id),"processed":False,"reason":"processing_error"})
    return results

def request_retry(job,user,reason):
    """Operator-approved local recovery for a stopped job, never a blind retry."""
    require_operator(user,job)
    if not isinstance(reason,str) or len(reason.strip())<12:
        raise ValueError("retry investigation reason required")
    job.refresh_from_db()
    if job.status!=CatalogJob.STATUS_FAILED or job.error_code not in (
        "storage_failure","processing_error","worker_stalled"):
        raise ValueError("failure requires corrected source files, not a retry")
    if (not job.baseline_sha256 or not job.supplier_sha256 or
            engine.digest(job.baseline.path)!=job.baseline_sha256 or
            engine.digest(job.supplier_update.path)!=job.supplier_sha256):
        raise ValueError("original submission changed; cannot retry")
    with transaction.atomic():
        updated=CatalogJob.objects.filter(
            pk=job.pk,status=CatalogJob.STATUS_FAILED,
            error_code__in=("storage_failure","processing_error","worker_stalled")
        ).update(status=CatalogJob.STATUS_RECEIVED,error_code="")
        if updated!=1:raise ValueError("retry was already requested")
        CatalogEvent.objects.create(
            job=job,actor=user,kind="retry_requested",
            detail="retry_investigated:"+reason.strip()[:140])
    return {"job_id":str(job.pk),"queued":True}

def review(job,user):
    require_operator(user,job)
    if job.status!=CatalogJob.STATUS_REVIEW or not job.engine_job_id:
        raise ValueError("job not reviewable")
    return engine.review(backend_db(job.store_id),str(job.engine_job_id))

def decide(job,user,change_id,decision,reason):
    detail=review(job,user)
    if change_id not in {c["id"] for c in detail["changes"]}:
        raise ValueError("change belongs to another job")
    if decision not in ("approved","rejected") or not reason.strip():
        raise ValueError("invalid decision")
    result=engine.decide(backend_db(job.store_id),change_id,decision,
                         f"web-operator:{user.pk}",reason.strip())
    CatalogEvent.objects.create(job=job,actor=user,kind=decision,
                                detail="change_id:"+str(change_id)[:60])
    return result

def exclude_held_record(job,user,token,reason):
    """Approve skipping one invalid source record; never approve its value."""
    require_operator(user,job)
    if job.status!=CatalogJob.STATUS_REVIEW or not job.engine_job_id:
        raise ValueError("job not reviewable")
    result=engine.exclude_hold(
        backend_db(job.store_id),str(job.engine_job_id),token,
        f"web-operator:{user.pk}",reason)
    CatalogEvent.objects.create(job=job,actor=user,kind="hold_excluded",
                                detail="held_source_row_excluded")
    return result

def approve_safe_stock_batch(job,user,reason):
    """Operator-triggered batch approval; does not affect risky or ambiguous changes."""
    require_operator(user,job)
    if job.status!=CatalogJob.STATUS_REVIEW or not job.engine_job_id:
        raise ValueError("job not reviewable")
    result=engine.approve_low_risk_stock_batch(
        backend_db(job.store_id),str(job.engine_job_id),
        f"web-operator:{user.pk}",reason)
    CatalogEvent.objects.create(
        job=job,actor=user,kind="approved",
        detail=f"explicit_small_stock_batch:{result['approved_count']}")
    return result

def output_path(job):
    identifier=str(uuid.UUID(str(job.id)))
    directory=backend_db(job.store_id).parent/"exports"
    directory.mkdir(exist_ok=True,mode=0o700)
    return directory/(identifier+".csv")

def prepare_export(job,user):
    require_operator(user,job)
    if job.status!=CatalogJob.STATUS_REVIEW or not job.engine_job_id:
        raise ValueError("job cannot be exported")
    path=output_path(job)
    database=backend_db(job.store_id)
    if path.exists():
        # A crash may have occurred after a successful engine export but
        # before the portal status was committed. Recover only if the engine
        # recorded the export AND an independent reconciliation still passes.
        review_state=engine.review(database,str(job.engine_job_id))["job"]["status"]
        if review_state!="exported":
            raise ValueError("existing export without committed engine audit")
        checked=qa.verify(database,str(job.engine_job_id),path)
        if not checked["passed"]:
            raise ValueError("existing export failed independent verification")
        result={"sha256":checked["sha256"],"path":str(path),
                "rows":checked["expected_rows"],"recovered":True}
    else:
        result=engine.export(database,str(job.engine_job_id),path)
    job.export_sha256=result["sha256"]
    job.status=CatalogJob.STATUS_READY
    job.save(update_fields=["export_sha256","status","updated_at"])
    CatalogEvent.objects.create(job=job,actor=user,kind="exported",
                                detail="independent_qa_passed")
    notices.create(job,"export_ready","customer")
    return result

def verified_download_path(job):
    if job.status!=CatalogJob.STATUS_READY or not job.engine_job_id:
        raise ValueError("export not ready")
    path=output_path(job)
    check=qa.verify(backend_db(job.store_id),str(job.engine_job_id),path)
    if not check["passed"] or check["sha256"]!=job.export_sha256:
        raise ValueError("export failed integrity verification")
    return path
