import logging

from sqlalchemy.orm import Session

from app import models
from app.pipeline import stage2_resume_parsing, stage3_rule_matching, stage4_verdict
from app.pipeline.extract_text import pdf_text_with_page_markers

logger = logging.getLogger("pipeline.orchestrator")


def evaluate_application(db: Session, application: models.Application) -> models.MatchResult:
    """
    Runs the full Stage 2 -> Stage 3 -> Stage 4 pipeline for one candidate
    application and persists a new MatchResult row.
    """
    job = application.job

    # Load document text (cached on the row after first parse to avoid re-reading the PDF every time)
    document_text = application.resume_text or ""
    if not document_text and application.resume_path:
        try:
            document_text = pdf_text_with_page_markers(application.resume_path)
            application.resume_text = document_text
        except Exception as exc:
            logger.warning("Could not extract text for application %s: %s", application.id, exc)
            document_text = ""

    try:
        # Stage 2: structured candidate data extraction (skip if already parsed)
        parsed = application.parsed_form_data
        if not parsed:
            parsed = stage2_resume_parsing.run(
                application.reference_number, application.candidate_name, document_text
            )
            application.parsed_form_data = parsed

        rules = job.requirements or []

        # Stage 3: rule-by-rule verification with citations
        rule_results = stage3_rule_matching.run(rules, parsed, document_text)

        # Stage 4: deterministic verdict aggregation
        verdict_info = stage4_verdict.run(rules, rule_results)

        match = models.MatchResult(
            application_id=application.id,
            verdict=verdict_info["verdict"],
            confidence=verdict_info["confidence"],
            rule_results=rule_results,
            stage="stage4_verdict",
        )
        db.add(match)
        application.status = "EVALUATED"
        db.commit()
        db.refresh(application)
        return match

    except Exception as exc:
        logger.exception("Evaluation failed for application %s", application.id)
        application.status = "FAILED_EVALUATION"
        db.commit()
        raise
