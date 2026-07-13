import os
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")
load_dotenv(ENV_PATH, override=False)


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    JWT_SECRET: str = os.getenv("JWT_SECRET", "insecure-dev-secret-change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    COOKIE_NAME: str = os.getenv("COOKIE_NAME", "access_token")
    COOKIE_MAX_AGE_DAYS: int = int(os.getenv("COOKIE_MAX_AGE_DAYS", "30"))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./recruit.db")

    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    PORT: int = int(os.getenv("PORT", "3001"))

    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
    RESUME_DIR: str = os.path.join(STORAGE_DIR, "resumes")
    JD_DIR: str = os.path.join(STORAGE_DIR, "jd")
    ZIP_DIR: str = os.path.join(STORAGE_DIR, "zips")


settings = Settings()

for d in (settings.STORAGE_DIR, settings.RESUME_DIR, settings.JD_DIR, settings.ZIP_DIR):
    os.makedirs(d, exist_ok=True)
