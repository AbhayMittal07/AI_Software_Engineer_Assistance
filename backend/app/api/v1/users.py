"""User, profile, settings and admin user-management endpoints."""
from fastapi import APIRouter

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.common import (
    MessageResponse,
    ProfileUpdate,
    RoleUpdate,
    UserOut,
    UserSettingsOut,
    UserSettingsUpdate,
)

router = APIRouter(tags=["Users & Settings"])


@router.get("/users/me", response_model=UserOut)
async def get_profile(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/users/me", response_model=UserOut)
async def update_profile(payload: ProfileUpdate, user: CurrentUser, session: DbSession) -> UserOut:
    users = UserRepository(session)
    await users.update(user, **payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(user)
    return UserOut.model_validate(user)


@router.get("/settings", response_model=UserSettingsOut)
async def get_settings(user: CurrentUser, session: DbSession) -> UserSettingsOut:
    row = await UserRepository(session).ensure_settings(user)
    return UserSettingsOut.model_validate(row)


@router.patch("/settings", response_model=UserSettingsOut)
async def update_settings(
    payload: UserSettingsUpdate, user: CurrentUser, session: DbSession
) -> UserSettingsOut:
    users = UserRepository(session)
    row = await users.ensure_settings(user)
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return UserSettingsOut.model_validate(row)


@router.get("/users", response_model=list[UserOut])
async def list_users(admin: AdminUser, session: DbSession) -> list[UserOut]:
    rows = await UserRepository(session).list_all()
    return [UserOut.model_validate(row) for row in rows]


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_role(user_id: int, payload: RoleUpdate, admin: AdminUser, session: DbSession) -> UserOut:
    users = UserRepository(session)
    target = await users.get(user_id)
    if not target:
        raise NotFoundError("User not found")
    target.role = UserRole(payload.role)
    await session.commit()
    await session.refresh(target)
    return UserOut.model_validate(target)


@router.patch("/users/{user_id}/status", response_model=UserOut)
async def toggle_status(user_id: int, admin: AdminUser, session: DbSession) -> UserOut:
    users = UserRepository(session)
    target = await users.get(user_id)
    if not target:
        raise NotFoundError("User not found")
    target.is_active = not target.is_active
    await session.commit()
    await session.refresh(target)
    return UserOut.model_validate(target)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(user_id: int, admin: AdminUser, session: DbSession) -> MessageResponse:
    users = UserRepository(session)
    target = await users.get(user_id)
    if not target:
        raise NotFoundError("User not found")
    await users.delete(target)
    await session.commit()
    return MessageResponse(message="User deleted")
