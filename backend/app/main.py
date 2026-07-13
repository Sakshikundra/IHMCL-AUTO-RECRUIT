import logging

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.deps import get_optional_user
from app import models
from app.auth import hash_password
from app.routers import auth_router, jobs_router, applications_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IHMCL Auto Recruit Validator — API")

# The bundled React frontend (services/api.js) always talks to http://localhost:3001,
# so CORS must allow that origin (and whatever FRONTEND_ORIGIN is set to) with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_router.router)
app.include_router(jobs_router.router)
app.include_router(applications_router.router)


@app.on_event("startup")
def seed_demo_users():
    """
    Seeds the two demo accounts the React frontend auto-logs in with
    (see src/services/api.js CREDENTIALS), so the app works out of the box.
    """
    db: Session = next(get_db())
    try:
        demo_accounts = [
            ("recruiter@recruitment.local", "Recruiter@123456", "RECRUITER", "Demo", "Recruiter"),
            ("manager@recruitment.local", "Manager@123456", "HIRING_MANAGER", "Demo", "Manager"),
        ]
        for email, password, role, first, last in demo_accounts:
            existing = db.query(models.User).filter(models.User.email == email).first()
            if not existing:
                db.add(models.User(
                    email=email,
                    password_hash=hash_password(password),
                    first_name=first,
                    last_name=last,
                    role=role,
                ))
        db.commit()
        logger.info("Demo accounts ready: %s", [a[0] for a in demo_accounts])
    finally:
        db.close()


# ── Auth gateway pages (IHMCL-branded) ──────────────────────────────────────

@app.get("/login")
def login_page(request: Request, user=Depends(get_optional_user)):
    if user:
        return RedirectResponse(url=f"{settings.FRONTEND_ORIGIN}/")
    return templates.TemplateResponse(
        "login.html", {"request": request, "frontend_origin": settings.FRONTEND_ORIGIN}
    )


@app.get("/signup")
def signup_page(request: Request, user=Depends(get_optional_user)):
    if user:
        return RedirectResponse(url=f"{settings.FRONTEND_ORIGIN}/")
    return templates.TemplateResponse(
        "signup.html", {"request": request, "frontend_origin": settings.FRONTEND_ORIGIN}
    )


@app.get("/")
def root(user=Depends(get_optional_user)):
    if user:
        return RedirectResponse(url=f"{settings.FRONTEND_ORIGIN}/")
    return RedirectResponse(url="/login")


@app.get("/api/health")
def health():
    return {"status": "ok"}
