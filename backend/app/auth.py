import datetime as dt

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(user_id: str, role: str) -> str:
    expire = dt.datetime.utcnow() + dt.timedelta(days=settings.COOKIE_MAX_AGE_DAYS)
    payload = {"sub": user_id, "role": role, "exp": expire, "iat": dt.datetime.utcnow()}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
