"""Authentication endpoints."""
from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, session: DbSession) -> AuthResponse:
    service = AuthService(session)
    return await service.register(
        payload.email, payload.password, payload.full_name, request.headers.get("User-Agent", "")
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, session: DbSession) -> AuthResponse:
    service = AuthService(session)
    return await service.login(payload.email, payload.password, request.headers.get("User-Agent", ""))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, request: Request, session: DbSession) -> TokenPair:
    service = AuthService(session)
    return await service.refresh(payload.refresh_token, request.headers.get("User-Agent", ""))


@router.post("/logout", response_model=MessageResponse)
async def logout(user: CurrentUser, session: DbSession) -> MessageResponse:
    await AuthService(session).logout(user.id)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, session: DbSession) -> MessageResponse:
    token = await AuthService(session).forgot_password(payload.email)
    message = "If the email exists, a reset link has been generated (check server logs in development)."
    if token:
        message = f"{message} Reset token: {token}"
    return MessageResponse(message=message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, session: DbSession) -> MessageResponse:
    await AuthService(session).reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password updated. Please sign in again.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, session: DbSession
) -> MessageResponse:
    await AuthService(session).change_password(user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed successfully")
