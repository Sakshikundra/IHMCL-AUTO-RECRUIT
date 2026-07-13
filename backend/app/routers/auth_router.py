from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token
from app.config import settings
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_MAX_AGE = settings.COOKIE_MAX_AGE_DAYS * 24 * 60 * 60


def _user_public(user: models.User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "role": user.role,
    }


def _issue_session(response: Response, user: models.User) -> str:
    token = create_access_token(user.id, user.role)
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return token


@router.post("/signup")
def signup(payload: schemas.SignupRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"message": "An account with this email already exists."}},
        )

    role = payload.role if payload.role in ("RECRUITER", "HIRING_MANAGER") else "RECRUITER"
    user = models.User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        first_name=payload.firstName,
        last_name=payload.lastName,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _issue_session(response, user)
    return {"accessToken": token, "user": _user_public(user)}


@router.post("/login")
def login(payload: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "Invalid email or password."}},
        )

    token = _issue_session(response, user)
    return {"accessToken": token, "user": _user_public(user)}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.COOKIE_NAME, path="/")
    return {"success": True}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {"user": _user_public(user)}
