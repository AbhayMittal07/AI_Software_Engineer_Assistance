"""Authentication and user management service."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.logging_config import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import (
    PasswordResetRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.schemas.common import AuthResponse, TokenPair, UserOut

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = RefreshTokenRepository(session)
        self.resets = PasswordResetRepository(session)

    async def _issue_tokens(self, user: User, user_agent: str = "") -> TokenPair:
        access = create_access_token(user.id, user.email, user.role.value)
        refresh, expires_at, token_hash = create_refresh_token(user.id)
        await self.tokens.create(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at, user_agent=user_agent[:255]
        )
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register(self, email: str, password: str, full_name: str, user_agent: str = "") -> AuthResponse:
        email = email.lower().strip()
        if await self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists")
        user = await self.users.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name.strip(),
            role=UserRole.developer,
        )
        await self.users.ensure_settings(user)
        tokens = await self._issue_tokens(user, user_agent)
        await self.users.touch_login(user)
        await self.session.commit()
        await self.session.refresh(user)
        logger.info("Registered user %s", email)
        return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)

    async def login(self, email: str, password: str, user_agent: str = "") -> AuthResponse:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("This account has been deactivated")
        await self.users.ensure_settings(user)
        tokens = await self._issue_tokens(user, user_agent)
        await self.users.touch_login(user)
        await self.session.commit()
        await self.session.refresh(user)
        return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)

    async def refresh(self, refresh_token: str, user_agent: str = "") -> TokenPair:
        payload = decode_token(refresh_token, "refresh")
        stored = await self.tokens.get_active(hash_token(refresh_token))
        if not stored:
            raise UnauthorizedError("Refresh token revoked or unknown")
        if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise UnauthorizedError("Refresh token expired")
        user = await self.users.get(int(payload["sub"]))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found")
        stored.revoked = True
        tokens = await self._issue_tokens(user, user_agent)
        await self.session.commit()
        return tokens

    async def logout(self, user_id: int, refresh_token: str | None = None) -> None:
        if refresh_token:
            stored = await self.tokens.get_active(hash_token(refresh_token))
            if stored:
                stored.revoked = True
        else:
            await self.tokens.revoke_all(user_id)
        await self.session.commit()

    async def forgot_password(self, email: str) -> str | None:
        user = await self.users.get_by_email(email)
        if not user:
            return None
        token = generate_reset_token()
        await self.resets.create(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        await self.session.commit()
        logger.info("Password reset token for %s: %s", email, token)
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        record = await self.resets.get_valid(hash_token(token))
        if not record:
            raise UnauthorizedError("Invalid or already used reset token")
        if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise UnauthorizedError("Reset token expired")
        user = await self.users.get(record.user_id)
        if not user:
            raise NotFoundError("User not found")
        user.hashed_password = hash_password(new_password)
        record.used = True
        await self.tokens.revoke_all(user.id)
        await self.session.commit()

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        await self.tokens.revoke_all(user.id)
        await self.session.commit()
