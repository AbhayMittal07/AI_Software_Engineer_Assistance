"""User and token data-access repositories."""
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update

from app.models.user import PasswordResetToken, RefreshToken, User, UserSettings
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower().strip())
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_all(self, limit: int = 200) -> Sequence[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def ensure_settings(self, user: User) -> UserSettings:
        stmt = select(UserSettings).where(UserSettings.user_id == user.id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing
        settings_row = UserSettings(user_id=user.id)
        self.session.add(settings_row)
        await self.session.flush()
        return settings_row

    async def touch_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_active(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def revoke_all(self, user_id: int) -> None:
        await self.session.execute(
            update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True)
        )
        await self.session.flush()


class PasswordResetRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    async def get_valid(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash, PasswordResetToken.used.is_(False)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
