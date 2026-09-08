"""FastAPI dependencies: DB session, current user, role guards."""
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        raise UnauthorizedError("Not authenticated")
    payload = decode_token(token, "access")
    users = UserRepository(session)
    user = await users.get(int(payload["sub"]))
    if not user:
        raise UnauthorizedError("User no longer exists")
    if not user.is_active:
        raise ForbiddenError("Account deactivated")
    await users.ensure_settings(user)
    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role.value != "admin":
        raise ForbiddenError("Administrator privileges required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
