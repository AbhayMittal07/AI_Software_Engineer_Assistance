"""Dashboard aggregation service."""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis import Diagram, Document, Report, Review
from app.models.user import User
from app.repositories.analysis_repository import (
    DiagramRepository,
    DocumentRepository,
    ReportRepository,
    RepositoryRepository,
    ReviewRepository,
)
from app.schemas.analysis import DashboardStats, RepositoryOut, ReviewOut
from app.services.ai.factory import get_ai_provider


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repos = RepositoryRepository(session)
        self.reviews = ReviewRepository(session)
        self.docs = DocumentRepository(session)
        self.diagrams = DiagramRepository(session)
        self.reports = ReportRepository(session)

    async def _count_for_user(self, model: Any, user: User, is_admin: bool) -> int:
        stmt = select(func.count()).select_from(model)
        if not is_admin and hasattr(model, "user_id"):
            stmt = stmt.where(model.user_id == user.id)
        elif not is_admin:
            from app.models.repository import Repository

            stmt = stmt.join(Repository, Repository.id == model.repository_id).where(
                Repository.user_id == user.id
            )
        return int((await self.session.execute(stmt)).scalar() or 0)

    async def stats(self, user: User) -> DashboardStats:
        is_admin = user.role.value == "admin"
        repositories, total_repos = await self.repos.search(user.id, is_admin=is_admin, page=1, page_size=6)
        reviews = list(await self.reviews.completed_for_user(user.id, is_admin))
        total_reviews = await self._count_for_user(Review, user, is_admin)

        severity: Counter[str] = Counter()
        total_findings = 0
        for review in reviews:
            for finding in review.findings or []:
                key = str(finding.get("severity", "info")).lower()
                severity[key if key in {"critical", "high", "medium", "low", "info"} else "info"] += 1
                total_findings += 1

        def average(attribute: str) -> float:
            values = [getattr(r, attribute) for r in reviews if getattr(r, attribute)]
            return round(sum(values) / len(values), 1) if values else 0.0

        trend = [
            {
                "date": review.created_at.strftime("%d %b"),
                "quality": review.quality_score,
                "security": review.security_score,
                "maintainability": review.maintainability_score,
                "performance": review.performance_score,
            }
            for review in sorted(reviews, key=lambda r: r.created_at)[-12:]
        ]
        provider = get_ai_provider()
        recent_reviews, _ = await self.reviews.history(user.id, is_admin=is_admin, page=1, page_size=6)

        return DashboardStats(
            total_repositories=total_repos,
            total_reviews=total_reviews,
            total_reports=await self._count_for_user(Report, user, is_admin),
            total_documents=await self._count_for_user(Document, user, is_admin),
            total_diagrams=await self._count_for_user(Diagram, user, is_admin),
            total_findings=total_findings,
            critical_findings=severity.get("critical", 0) + severity.get("high", 0),
            avg_quality_score=average("quality_score"),
            avg_security_score=average("security_score"),
            avg_maintainability_score=average("maintainability_score"),
            avg_performance_score=average("performance_score"),
            avg_complexity_score=average("complexity_score"),
            avg_technical_debt_score=average("technical_debt_score"),
            language_distribution=await self.repos.language_distribution(user.id, is_admin),
            severity_distribution=dict(severity),
            score_trend=trend,
            recent_repositories=[RepositoryOut.model_validate(repo) for repo in repositories],
            recent_reviews=[ReviewOut.model_validate(review) for review in recent_reviews],
            ai_enabled=provider.available,
            ai_model=provider.text_model,
        )
