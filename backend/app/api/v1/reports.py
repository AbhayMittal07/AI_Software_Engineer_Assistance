"""PDF report endpoints."""
from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.analysis_repository import RepositoryRepository, ReportRepository
from app.schemas.analysis import ReportCreate, ReportOut
from app.schemas.common import MessageResponse
from app.services.report_service import ReportService
from app.services.repository_service import RepositoryService

router = APIRouter(tags=["Reports"])


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    user: CurrentUser, session: DbSession, repository_id: int | None = None
) -> list[ReportOut]:
    rows = await ReportRepository(session).for_user(
        user.id, is_admin=user.role.value == "admin", repository_id=repository_id
    )
    repos = RepositoryRepository(session)
    result: list[ReportOut] = []
    for row in rows:
        out = ReportOut.model_validate(row)
        repo = await repos.get(row.repository_id)
        out.repository_name = repo.name if repo else None
        result.append(out)
    return result


@router.post(
    "/repositories/{repo_id}/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED
)
async def create_report(
    repo_id: int, payload: ReportCreate, user: CurrentUser, session: DbSession
) -> ReportOut:
    repo = await RepositoryService(session).get_or_404(repo_id, user)
    report = await ReportService(session).create_report(
        repo, user, payload.review_id, payload.include_documentation, payload.include_diagrams
    )
    out = ReportOut.model_validate(report)
    out.repository_name = repo.name
    return out


@router.get("/reports/{report_id}/download")
async def download_report(report_id: int, user: CurrentUser, session: DbSession) -> FileResponse:
    report = await ReportRepository(session).get_owned(report_id, user.id, user.role.value == "admin")
    if not report:
        raise NotFoundError("Report not found")
    path = Path(report.file_path)
    if not path.exists():
        raise NotFoundError("Report file is missing on disk")
    return FileResponse(path, media_type="application/pdf", filename=report.file_name)


@router.delete("/reports/{report_id}", response_model=MessageResponse)
async def delete_report(report_id: int, user: CurrentUser, session: DbSession) -> MessageResponse:
    reports = ReportRepository(session)
    report = await reports.get_owned(report_id, user.id, user.role.value == "admin")
    if not report:
        raise NotFoundError("Report not found")
    Path(report.file_path).unlink(missing_ok=True)
    await reports.delete(report)
    await session.commit()
    return MessageResponse(message="Report deleted")
