from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ForgotPasswordResponse(BaseModel):
    ok: bool
    message: str
    reset_url: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    password: str = Field(min_length=8, max_length=256)


class UserPublic(BaseModel):
    id: str
    email: str
    display_name: str | None = None


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    display_name: str | None


@dataclass(frozen=True)
class CreatedSession:
    token: str
    expires_at: datetime
    user: AuthUser
