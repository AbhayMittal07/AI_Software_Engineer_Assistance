"""Architecture diagram endpoints."""
from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.analysis_repository import DiagramRepository
from app.schemas.analysis import DiagramGenerateRequest, DiagramOut, DiagramUpdate
from app.schemas.common import MessageResponse
from app.services.diagram_service import DEFAULT_DIAGRAM_TYPES, DiagramService
from app.services.repository_service import RepositoryService

router = APIRouter(tags=["Diagrams"])


@router.get("/diagrams/types", response_model=list[str])
async def diagram_types() -> list[str]:
    return DEFAULT_DIAGRAM_TYPES


@router.get("/repositories/{repo_id}/diagrams", response_model=list[DiagramOut])
async def list_diagrams(repo_id: int, user: CurrentUser, session: DbSession) -> list[DiagramOut]:
    await RepositoryService(session).get_or_404(repo_id, user)
    rows = await DiagramRepository(session).for_repo(repo_id)
    return [DiagramOut.model_validate(row) for row in rows]


@router.post("/repositories/{repo_id}/diagrams", response_model=list[DiagramOut])
async def generate_diagrams(
    repo_id: int, payload: DiagramGenerateRequest, user: CurrentUser, session: DbSession
) -> list[DiagramOut]:
    repo = await RepositoryService(session).get_or_404(repo_id, user)
    rows = await DiagramService(session).generate(repo, payload.diagram_types, payload.regenerate)
    return [DiagramOut.model_validate(row) for row in rows]


@router.patch("/diagrams/{diagram_id}", response_model=DiagramOut)
async def update_diagram(
    diagram_id: int, payload: DiagramUpdate, user: CurrentUser, session: DbSession
) -> DiagramOut:
    diagrams = DiagramRepository(session)
    row = await diagrams.get(diagram_id)
    if not row:
        raise NotFoundError("Diagram not found")
    await RepositoryService(session).get_or_404(row.repository_id, user)
    await diagrams.update(row, **payload.model_dump(exclude_none=True))
    await session.commit()
    return DiagramOut.model_validate(row)


@router.get("/diagrams/{diagram_id}/export")
async def export_diagram(
    diagram_id: int, user: CurrentUser, session: DbSession, format: str = "drawio"
) -> Response:
    diagrams = DiagramRepository(session)
    row = await diagrams.get(diagram_id)
    if not row:
        raise NotFoundError("Diagram not found")
    await RepositoryService(session).get_or_404(row.repository_id, user)
    mapping = {
        "drawio": (row.drawio_xml, "application/xml", "drawio"),
        "mermaid": (row.mermaid, "text/plain", "mmd"),
        "plantuml": (row.plantuml, "text/plain", "puml"),
    }
    content, media_type, extension = mapping.get(format, mapping["drawio"])
    file_name = f"{row.diagram_type}-{row.id}.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.delete("/diagrams/{diagram_id}", response_model=MessageResponse)
async def delete_diagram(diagram_id: int, user: CurrentUser, session: DbSession) -> MessageResponse:
    diagrams = DiagramRepository(session)
    row = await diagrams.get(diagram_id)
    if not row:
        raise NotFoundError("Diagram not found")
    await RepositoryService(session).get_or_404(row.repository_id, user)
    await diagrams.delete(row)
    await session.commit()
    return MessageResponse(message="Diagram deleted")
