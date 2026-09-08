from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------- auth
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)


class RegisterRequest(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must contain both letters and numbers")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserSettingsOut(ORMModel):
    theme: str
    ai_model: str
    review_depth: str
    auto_generate_docs: bool
    auto_generate_diagrams: bool
    email_notifications: bool


class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = Field(default=None, pattern="^(dark|light|system)$")
    ai_model: Optional[str] = None
    review_depth: Optional[str] = Field(default=None, pattern="^(quick|standard|deep)$")
    auto_generate_docs: Optional[bool] = None
    auto_generate_diagrams: Optional[bool] = None
    email_notifications: Optional[bool] = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    bio: str = ""
    company: str = ""
    created_at: datetime
    last_login_at: Optional[datetime] = None
    settings: Optional[UserSettingsOut] = None

    @field_validator("role", mode="before")
    @classmethod
    def role_to_str(cls, value: Any) -> str:
        return getattr(value, "value", value)


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    bio: Optional[str] = Field(default=None, max_length=500)
    company: Optional[str] = Field(default=None, max_length=150)


class RoleUpdate(BaseModel):
    role: str = Field(pattern="^(admin|reviewer|developer)$")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserOut
    tokens: TokenPair
