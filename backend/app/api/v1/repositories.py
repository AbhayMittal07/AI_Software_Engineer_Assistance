"""Repository management endpoints."""
from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.repositories.analysis_repository import (
    DiagramRepository,
    DocumentRepository,
    ReportRepository,
    RepositoryRepository,
    ReviewRepository,
)
from app.schemas.analysis import (
    FileContentOut,
    GithubImportRequest,
    RepositoryDetail,
    RepositoryOut,
    RepositoryUpdate,
)
from app.schemas.common import MessageResponse, Page
from app.services.repository_service import RepositoryService

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get("", response_model=Page[RepositoryOut])
async def list_repositories(
    user: CurrentUser,
    session: DbSession,
    q: str | None = Query(default=None, max_length=200),
    language: str | None = None,
    repo_status: str | None = Query(default=None, alias="status"),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=60),
) -> Page[RepositoryOut]:
    repos = RepositoryRepository(session)
    rows, total = await repos.search(
        user.id,
        is_admin=user.role.value == "admin",
        query=q,
        language=language,
        status=repo_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return Page[RepositoryOut](
        items=[RepositoryOut.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max((total + page_size - 1) // page_size, 1),
    )


@router.post("/upload", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def upload_repository(
    user: CurrentUser,
    session: DbSession,
    file: UploadFile = File(...),
    description: str = Form(default=""),
) -> RepositoryOut:
    payload = await file.read()
    service = RepositoryService(session)
    repo = await service.create_from_zip(user, file.filename or "repository.zip", payload, description)
    return RepositoryOut.model_validate(repo)


@router.post("/github", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def import_github(
    payload: GithubImportRequest, user: CurrentUser, session: DbSession
) -> RepositoryOut:
    service = RepositoryService(session)
    repo = await service.create_from_github(
        user, payload.url, payload.branch, payload.name, payload.description
    )
    return RepositoryOut.model_validate(repo)


@router.get("/{repo_id}", response_model=RepositoryDetail)
async def get_repository(repo_id: int, user: CurrentUser, session: DbSession) -> RepositoryDetail:
    service = RepositoryService(session)
    repo = await service.get_or_404(repo_id, user)
    reviews = ReviewRepository(session)
    latest = await reviews.latest_for_repo(repo.id)
    detail = RepositoryDetail.model_validate(repo)
    detail.review_count = await reviews.count(repository_id=repo.id)
    detail.document_count = len(await DocumentRepository(session).for_repo(repo.id))
    detail.diagram_count = len(await DiagramRepository(session).for_repo(repo.id))
    detail.report_count = len(await ReportRepository(session).for_user(user.id, repository_id=repo.id))
    detail.latest_review_id = latest.id if latest else None
    return detail


@router.patch("/{repo_id}", response_model=RepositoryOut)
async def update_repository(
    repo_id: int, payload: RepositoryUpdate, user: CurrentUser, session: DbSession
) -> RepositoryOut:
    service = RepositoryService(session)
    repo = await service.get_or_404(repo_id, user)
    await RepositoryRepository(session).update(repo, **payload.model_dump(exclude_none=True))
    await session.commit()
    return RepositoryOut.model_validate(repo)


@router.post("/{repo_id}/reanalyze", response_model=RepositoryOut)
async def reanalyze(repo_id: int, user: CurrentUser, session: DbSession) -> RepositoryOut:
    service = RepositoryService(session)
    repo = await service.get_or_404(repo_id, user)
    await service.analyze(repo)
    return RepositoryOut.model_validate(repo)


@router.get("/{repo_id}/file", response_model=FileContentOut)
async def read_repository_file(
    repo_id: int, path: str, user: CurrentUser, session: DbSession
) -> FileContentOut:
    service = RepositoryService(session)
    repo = await service.get_or_404(repo_id, user)
    return FileContentOut(**service.read_file(repo, path))


@router.delete("/{repo_id}", response_model=MessageResponse)
async def delete_repository(repo_id: int, user: CurrentUser, session: DbSession) -> MessageResponse:
    service = RepositoryService(session)
    repo = await service.get_or_404(repo_id, user)
    await service.delete(repo)
    return MessageResponse(message="Repository deleted")
