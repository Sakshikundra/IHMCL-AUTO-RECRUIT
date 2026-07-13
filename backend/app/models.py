import uuid
import datetime as dt

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    role = Column(String, default="RECRUITER")  # RECRUITER | HIRING_MANAGER | ADMIN
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    jobs = relationship("Job", back_populates="creator")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    posting_code = Column(String, default="")
    description = Column(String, default="")
    status = Column(String, default="DRAFT")  # DRAFT | ACTIVE | CLOSED
    requirements = Column(JSON, nullable=True)  # list[rule dict], set on lock-checklist
    checklist_locked = Column(Integer, default=0)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    creator = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=gen_id)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    reference_number = Column(String, nullable=False)
    candidate_name = Column(String, default="")
    candidate_email = Column(String, default="")
    status = Column(String, default="PENDING")  # PENDING | PARSED | EVALUATED | FAILED_EVALUATION
    resume_path = Column(String, nullable=True)
    resume_text = Column(Text, nullable=True)
    parsed_form_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    job = relationship("Job", back_populates="applications")
    match_results = relationship(
        "MatchResult", back_populates="application",
        cascade="all, delete-orphan", order_by="desc(MatchResult.created_at)"
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(String, primary_key=True, default=gen_id)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    verdict = Column(String, default="semi_eligible")  # eligible | semi_eligible | not_eligible
    confidence = Column(Integer, default=0)
    rule_results = Column(JSON, nullable=True)
    stage = Column(String, default="stage4_verdict")
    override_by = Column(String, ForeignKey("users.id"), nullable=True)
    override_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    application = relationship("Application", back_populates="match_results")
