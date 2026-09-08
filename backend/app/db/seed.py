"""Seed data: bootstrap admin and demo accounts plus a sample repository."""
from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.models.repository import RepoSource, RepoStatus, Repository
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.repository_service import RepositoryService

logger = get_logger(__name__)

SAMPLE_REPO_DIR = Path(__file__).resolve().parents[2] / "sample_repository"


async def seed() -> None:
    async with SessionLocal() as session:
        users = UserRepository(session)
        accounts = [
            (settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD, "Platform Administrator", UserRole.admin),
            (settings.DEMO_EMAIL, settings.DEMO_PASSWORD, "Demo Developer", UserRole.developer),
        ]
        created: dict[str, User] = {}
        for email, password, name, role in accounts:
            user = await users.get_by_email(email)
            if user is None:
                user = await users.create(
                    email=email.lower(), hashed_password=hash_password(password),
                    full_name=name, role=role,
                )
                logger.info("Seeded %s account: %s", role.value, email)
            elif not verify_password(password, user.hashed_password):
                user.hashed_password = hash_password(password)
                logger.info("Updated password for %s", email)
            await users.ensure_settings(user)
            created[email] = user
        await session.commit()

        demo = created.get(settings.DEMO_EMAIL)
        if demo and SAMPLE_REPO_DIR.exists():
            existing = (
                await session.execute(
                    select(Repository).where(
                        Repository.user_id == demo.id, Repository.name == "sample-task-api"
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                repo = Repository(
                    user_id=demo.id,
                    name="sample-task-api",
                    description="Bundled sample project used to demo AI review, documentation and diagrams.",
                    source_type=RepoSource.zip,
                    status=RepoStatus.analyzing,
                )
                session.add(repo)
                await session.flush()
                target = settings.repo_dir / f"repo_{repo.id}"
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(SAMPLE_REPO_DIR, target)
                repo.storage_path = str(target)
                await session.commit()
                try:
                    await RepositoryService(session).analyze(repo)
                    logger.info("Seeded sample repository (id=%s)", repo.id)
                except Exception as exc:  # noqa: BLE001 - seeding must not block startup
                    logger.warning("Sample repository analysis failed: %s", str(exc)[:200])
