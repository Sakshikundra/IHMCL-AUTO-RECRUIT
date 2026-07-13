from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.auth import decode_access_token
from app import models


def _extract_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.cookies.get(settings.COOKIE_NAME)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "Not authenticated. Please log in."}},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "Invalid or expired session. Please log in again."}},
        )
    user = db.query(models.User).filter(models.User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "User no longer exists."}},
        )
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> models.User | None:
    token = _extract_token(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    return db.query(models.User).filter(models.User.id == payload.get("sub")).first()
