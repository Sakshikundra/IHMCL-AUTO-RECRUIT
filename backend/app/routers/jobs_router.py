import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.pipeline import stage1_jd_extraction
from app.pipeline.extract_text import pdf_text_with_page_markers

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_public(job: models.Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "status": job.status,
        "createdAt": job.created_at.isoformat(),
        "creator": {
            "firstName": job.creator.first_name if job.creator else "",
            "lastName": job.creator.last_name if job.creator else "",
        },
        "_count": {"applications": len(job.applications)},
        "requirements": job.requirements,
    }


@router.get("")
def list_jobs(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    jobs = db.query(models.Job).order_by(models.Job.created_at.desc()).limit(limit).all()
    return {"jobs": [_job_public(j) for j in jobs]}


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"message": "Job not found"}})
    return {"job": _job_public(job)}


@router.post("")
def create_job(
    payload: schemas.CreateJobRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    job = models.Job(
        title=payload.title,
        posting_code=payload.postingCode,
        description=payload.description,
        status="ACTIVE",
        created_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job": _job_public(job)}


@router.post("/{job_id}/lock-checklist")
def lock_checklist(
    job_id: str,
    payload: schemas.LockChecklistRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"message": "Job not found"}})

    job.requirements = payload.rules
    job.checklist_locked = 1
    job.status = "ACTIVE"
    db.commit()
    db.refresh(job)
    return {"job": _job_public(job)}


@router.post("/extract-jd")
async def extract_jd(
    file: UploadFile = File(...),
    jobId: str = Form("draft"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    STAGE 1 of the pipeline: parses an uploaded JD PDF and returns AI-extracted
    hiring criteria for the recruiter to review before applying it to the job.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail={"error": {"message": "Only PDF job descriptions are supported."}}
        )

    tmp_path = os.path.join(settings.JD_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    post_hint = ""
    if jobId and jobId != "draft":
        job = db.query(models.Job).filter(models.Job.id == jobId).first()
        if job:
            post_hint = job.title

    try:
        text = pdf_text_with_page_markers(tmp_path)
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail={"error": {"message": "Could not read any text from this PDF. Is it a scanned image?"}},
            )
        result = stage1_jd_extraction.run(text, post_hint=post_hint)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail={"error": {"message": f"JD extraction failed: {exc}"}}
        )
