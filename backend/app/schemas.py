from pydantic import BaseModel, Field, field_validator


def _check_basic_email_shape(v: str) -> str:
    v = (v or "").strip()
    if "@" not in v or v.startswith("@") or v.endswith("@") or " " in v:
        raise ValueError("Enter a valid email address")
    return v


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    firstName: str = ""
    lastName: str = ""
    role: str = "RECRUITER"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _check_basic_email_shape(v)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return _check_basic_email_shape(v)


class CreateJobRequest(BaseModel):
    title: str
    postingCode: str = ""
    description: str = ""


class LockChecklistRequest(BaseModel):
    rules: list[dict]


class OverrideRequest(BaseModel):
    verdict: str
    reason: str = ""
