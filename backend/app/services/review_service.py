"""AI code review orchestration with deterministic fallback analysis."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.analysis import Review, ReviewStatus
from app.models.repository import Repository
from app.models.user import User
from app.repositories.analysis_repository import ReviewRepository
from app.services.ai.factory import get_ai_provider
from app.services.ai.prompts import REVIEW_SYSTEM, review_prompt
from app.services.code_analyzer import AnalysisResult, code_analyzer
from app.services.scoring import compute_static_scores

logger = get_logger(__name__)

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _as_list(payload: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = payload.get(key)
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _clamp(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return round(max(0.0, min(100.0, number)), 1)


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reviews = ReviewRepository(session)

    async def run_review(self, repo: Repository, user: User, depth: str = "standard") -> Review:
        provider = get_ai_provider()
        review = await self.reviews.create(
            repository_id=repo.id,
            user_id=user.id,
            status=ReviewStatus.running,
            depth=depth,
            provider=provider.name,
            model=provider.text_model,
        )
        await self.session.commit()

        root = Path(repo.storage_path)
        try:
            analysis = await asyncio.to_thread(code_analyzer.analyze, root)
            static = compute_static_scores(analysis)
            payload: Dict[str, Any] = {}
            ai_powered = False
            if provider.available:
                max_files = {"quick": 8, "standard": settings.MAX_ANALYZED_FILES_FOR_AI, "deep": 28}.get(
                    depth, settings.MAX_ANALYZED_FILES_FOR_AI
                )
                bundle = await asyncio.to_thread(
                    code_analyzer.select_code_bundle, root, analysis, max_files
                )
                try:
                    payload = await provider.generate_json(
                        review_prompt(analysis.as_context(), bundle, depth),
                        system=REVIEW_SYSTEM,
                        temperature=0.2,
                    )
                    ai_powered = bool(payload)
                except Exception as exc:  # noqa: BLE001 - degrade to static review
                    logger.warning("AI review failed for repo %s: %s", repo.id, str(exc)[:250])

            self._apply(review, repo, analysis, static, payload, ai_powered)
            review.status = ReviewStatus.completed
            review.completed_at = datetime.now(timezone.utc)
            await self.session.commit()
        except Exception as exc:  # noqa: BLE001
            review.status = ReviewStatus.failed
            review.error_message = str(exc)[:500]
            await self.session.commit()
            logger.exception("Review %s failed", review.id)
            raise
        return review

    # -------------------------------------------------------------- merging
    def _apply(
        self,
        review: Review,
        repo: Repository,
        analysis: AnalysisResult,
        static: Dict[str, Any],
        payload: Dict[str, Any],
        ai_powered: bool,
    ) -> None:
        scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
        static_scores = static["scores"]
        review.quality_score = _clamp(scores.get("quality"), static_scores["quality"])
        review.maintainability_score = _clamp(scores.get("maintainability"), static_scores["maintainability"])
        review.security_score = _clamp(scores.get("security"), static_scores["security"])
        review.performance_score = _clamp(scores.get("performance"), static_scores["performance"])
        review.complexity_score = _clamp(scores.get("complexity"), static_scores["complexity"])
        review.technical_debt_score = _clamp(scores.get("technical_debt"), static_scores["technical_debt"])
        review.scalability_score = _clamp(scores.get("scalability"), static_scores["scalability"])

        static_findings = static["findings"]
        findings = _as_list(payload, "findings") + static_findings
        findings.sort(key=lambda f: SEVERITY_ORDER.get(str(f.get("severity", "low")).lower(), 5))
        review.findings = findings[:80]
        review.security_findings = (_as_list(payload, "security_findings") + static["security_findings"])[:40]
        review.performance_findings = (_as_list(payload, "performance_findings") + static["performance_findings"])[:30]
        review.code_smells = (_as_list(payload, "code_smells") + static["code_smells"])[:40]
        review.dead_code = (_as_list(payload, "dead_code") + static["dead_code"])[:30]
        review.duplicate_code = (_as_list(payload, "duplicate_code") + analysis.duplicates)[:20]
        review.unused_symbols = (_as_list(payload, "unused_symbols") + static["unused_symbols"])[:40]
        review.complexity_analysis = (_as_list(payload, "complexity_analysis") + static["complexity_analysis"])[:30]
        review.solid_violations = (_as_list(payload, "solid_violations") + static["solid_violations"])[:20]
        review.design_patterns = _as_list(payload, "design_patterns")[:20] or static["design_patterns"]
        review.dependency_analysis = _as_list(payload, "dependency_analysis")[:40] or static["dependency_analysis"]
        review.refactoring_suggestions = _as_list(payload, "refactoring_suggestions")[:20] or static["refactoring"]
        review.optimization_suggestions = _as_list(payload, "optimization_suggestions")[:20] or static["optimizations"]
        review.auto_fixes = _as_list(payload, "auto_fixes")[:20]
        review.generated_tests = _as_list(payload, "generated_tests")[:12] or static["generated_tests"]
        clean = payload.get("clean_architecture")
        review.clean_architecture = clean if isinstance(clean, dict) and clean else static["clean_architecture"]
        review.best_practices = _as_list(payload, "best_practices")[:25] or static["best_practices"]
        review.ai_powered = ai_powered
        summary = str(payload.get("summary") or "").strip()
        review.summary = summary or static["summary"]
        review.stats = {
            "total_findings": len(review.findings),
            "critical": len([f for f in review.findings if str(f.get("severity")).lower() == "critical"]),
            "high": len([f for f in review.findings if str(f.get("severity")).lower() == "high"]),
            "medium": len([f for f in review.findings if str(f.get("severity")).lower() == "medium"]),
            "low": len([f for f in review.findings if str(f.get("severity")).lower() == "low"]),
            "security_issues": len(review.security_findings),
            "performance_issues": len(review.performance_findings),
            "code_smells": len(review.code_smells),
            "dead_code": len(review.dead_code),
            "duplicate_blocks": len(review.duplicate_code),
            "unused_symbols": len(review.unused_symbols),
            "solid_violations": len(review.solid_violations),
            "generated_tests": len(review.generated_tests),
            "inline_comments": _as_list(payload, "inline_comments")[:40],
            "files_analyzed": min(analysis.file_count, settings.MAX_ANALYZED_FILES_FOR_AI),
            "lines_analyzed": analysis.total_lines,
            "static_metrics": analysis.metrics,
        }
