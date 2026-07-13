import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.pipeline import import_utils
from app.pipeline.orchestrator import evaluate_application

router = APIRouter(prefix="/api", tags=["applications"])

VERDICT_FILTERS = {"eligible", "semi_eligible", "not_eligible"}


def _match_result_public(mr: models.MatchResult | None) -> dict:
    if not mr:
        return {}
    return {
        "id": mr.id,
        "verdict": mr.verdict,
        "confidence": mr.confidence,
        "ruleResults": mr.rule_results or [],
        "overrideBy": mr.override_by,
        "overrideReason": mr.override_reason,
        "createdAt": mr.created_at.isoformat(),
    }


def _application_public(app: models.Application) -> dict:
    latest = app.match_results[0] if app.match_results else None
    return {
        "id": app.id,
        "jobId": app.job_id,
        "referenceNumber": app.reference_number,
        "candidateName": app.candidate_name,
        "candidateEmail": app.candidate_email,
        "status": app.status,
        "parsedFormData": app.parsed_form_data,
        "matchResults": [_match_result_public(m) for m in app.match_results] if app.match_results else [],
    }


@router.get("/jobs/{job_id}/applications")
def list_applications(
    job_id: str,
    limit: int = 100,
    verdict: str | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"message": "Job not found"}})

    apps = (
        db.query(models.Application)
        .filter(models.Application.job_id == job_id)
        .order_by(models.Application.created_at.desc())
        .limit(limit)
        .all()
    )

    results = [_application_public(a) for a in apps]

    if verdict in VERDICT_FILTERS:
        results = [r for r in results if r["matchResults"] and r["matchResults"][0].get("verdict") == verdict]

    return {"applications": results}


@router.post("/jobs/{job_id}/applications/import")
async def import_applications(
    job_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Imports the recruiter's candidate sheet (Excel) and creates PENDING application rows."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"message": "Job not found"}})

    tmp_path = os.path.join(settings.STORAGE_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        candidates = import_utils.parse_candidate_excel(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": {"message": f"Could not read Excel sheet: {exc}"}})

    created = []
    for c in candidates:
        existing = (
            db.query(models.Application)
            .filter(
                models.Application.job_id == job_id,
                models.Application.reference_number == c["reference_number"],
            )
            .first()
        )
        if existing:
            continue
        app_row = models.Application(
            job_id=job_id,
            reference_number=c["reference_number"],
            candidate_name=c["candidate_name"],
            candidate_email=c["candidate_email"],
            status="PENDING",
        )
        db.add(app_row)
        created.append(app_row)

    db.commit()
    return {"imported": len(created)}


@router.post("/jobs/{job_id}/applications/import-zip")
async def import_documents_zip(
    job_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """
    Imports a ZIP of candidate documents (resumes/certificates/etc.) and best-effort
    matches each file to an already-imported application by reference number / name.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail={"error": {"message": "Job not found"}})

    zip_path = os.path.join(settings.ZIP_DIR, f"{uuid.uuid4().hex}_{file.filename}")
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    dest_dir = os.path.join(settings.RESUME_DIR, job_id)
    try:
        extracted_files = import_utils.extract_zip(zip_path, dest_dir)
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": {"message": f"Could not read ZIP file: {exc}"}})

    apps = db.query(models.Application).filter(models.Application.job_id == job_id).all()
    matched_count = 0
    for app_row in apps:
        if app_row.resume_path:
            continue
        match = import_utils.match_resume_for_candidate(
            extracted_files, app_row.reference_number, app_row.candidate_name
        )
        if match:
            app_row.resume_path = match
            matched_count += 1

    db.commit()
    return {"filesExtracted": len(extracted_files), "matched": matched_count}


@router.post("/applications/{application_id}/evaluate")
def evaluate(
    application_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Runs Stage 2 (parse) -> Stage 3 (rule matching) -> Stage 4 (verdict) for one candidate."""
    app_row = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail={"error": {"message": "Application not found"}})

    try:
        match = evaluate_application(db, app_row)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": {"message": f"Evaluation failed: {exc}"}})

    db.refresh(app_row)
    return {"application": _application_public(app_row), "matchResult": _match_result_public(match)}


@router.post("/applications/{application_id}/override")
def override(
    application_id: str,
    payload: schemas.OverrideRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Manual recruiter/hiring-manager override of the AI verdict (used by Manual Review & Verification screens)."""
    app_row = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail={"error": {"message": "Application not found"}})

    if payload.verdict not in VERDICT_FILTERS:
        raise HTTPException(status_code=400, detail={"error": {"message": "Invalid verdict value"}})

    latest = app_row.match_results[0] if app_row.match_results else None
    match = models.MatchResult(
        application_id=app_row.id,
        verdict=payload.verdict,
        confidence=latest.confidence if latest else 50,
        rule_results=latest.rule_results if latest else [],
        stage="manual_override",
        override_by=user.id,
        override_reason=payload.reason,
    )
    db.add(match)
    db.commit()
    db.refresh(app_row)
    return {"application": _application_public(app_row), "matchResult": _match_result_public(match)}
