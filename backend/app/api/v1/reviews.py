"""AI review endpoints."""
from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.analysis_repository import RepositoryRepository, ReviewRepository
from app.schemas.analysis import ReviewCreate, ReviewDetail, ReviewOut
from app.schemas.common import MessageResponse, Page
from app.services.repository_service import RepositoryService
from app.services.review_service import ReviewService

router = APIRouter(tags=["AI Review"])


@router.post(
    "/repositories/{repo_id}/reviews", response_model=ReviewDetail, status_code=status.HTTP_201_CREATED
)
async def create_review(
    repo_id: int, payload: ReviewCreate, user: CurrentUser, session: DbSession
) -> ReviewDetail:
    repo_service = RepositoryService(session)
    repo = await repo_service.get_or_404(repo_id, user)
    if repo.status.value not in {"ready", "failed"}:
        raise ValidationError("Repository is still being analysed")
    review = await ReviewService(session).run_review(repo, user, payload.depth)
    detail = ReviewDetail.model_validate(review)
    detail.repository_name = repo.name
    return detail


@router.get("/repositories/{repo_id}/reviews", response_model=list[ReviewOut])
async def list_repo_reviews(repo_id: int, user: CurrentUser, session: DbSession) -> list[ReviewOut]:
    await RepositoryService(session).get_or_404(repo_id, user)
    rows, _ = await ReviewRepository(session).history(
        user.id, is_admin=user.role.value == "admin", repository_id=repo_id, page=1, page_size=50
    )
    return [ReviewOut.model_validate(row) for row in rows]


@router.get("/reviews", response_model=Page[ReviewOut])
async def review_history(
    user: CurrentUser,
    session: DbSession,
    repository_id: int | None = None,
    review_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ReviewOut]:
    rows, total = await ReviewRepository(session).history(
        user.id,
        is_admin=user.role.value == "admin",
        repository_id=repository_id,
        status=review_status,
        page=page,
        page_size=page_size,
    )
    return Page[ReviewOut](
        items=[ReviewOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max((total + page_size - 1) // page_size, 1),
    )


@router.get("/reviews/{review_id}", response_model=ReviewDetail)
async def get_review(review_id: int, user: CurrentUser, session: DbSession) -> ReviewDetail:
    reviews = ReviewRepository(session)
    review = await reviews.get_owned(review_id, user.id, user.role.value == "admin")
    if not review:
        raise NotFoundError("Review not found")
    repo = await RepositoryRepository(session).get(review.repository_id)
    detail = ReviewDetail.model_validate(review)
    detail.repository_name = repo.name if repo else None
    return detail


@router.delete("/reviews/{review_id}", response_model=MessageResponse)
async def delete_review(review_id: int, user: CurrentUser, session: DbSession) -> MessageResponse:
    reviews = ReviewRepository(session)
    review = await reviews.get_owned(review_id, user.id, user.role.value == "admin")
    if not review:
        raise NotFoundError("Review not found")
    await reviews.delete(review)
    await session.commit()
    return MessageResponse(message="Review deleted")
