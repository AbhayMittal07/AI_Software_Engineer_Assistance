"""AI documentation endpoints."""
from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.analysis_repository import DocumentRepository
from app.schemas.analysis import DocumentGenerateRequest, DocumentOut
from app.schemas.common import MessageResponse
from app.services.documentation_service import DEFAULT_DOC_TYPES, DocumentationService
from app.services.repository_service import RepositoryService

router = APIRouter(tags=["Documentation"])


@router.get("/documentation/types", response_model=list[str])
async def documentation_types() -> list[str]:
    return DEFAULT_DOC_TYPES


@router.get("/repositories/{repo_id}/documentation", response_model=list[DocumentOut])
async def list_documents(repo_id: int, user: CurrentUser, session: DbSession) -> list[DocumentOut]:
    await RepositoryService(session).get_or_404(repo_id, user)
    rows = await DocumentRepository(session).for_repo(repo_id)
    return [DocumentOut.model_validate(row) for row in rows]


@router.post("/repositories/{repo_id}/documentation", response_model=list[DocumentOut])
async def generate_documents(
    repo_id: int, payload: DocumentGenerateRequest, user: CurrentUser, session: DbSession
) -> list[DocumentOut]:
    repo = await RepositoryService(session).get_or_404(repo_id, user)
    rows = await DocumentationService(session).generate(repo, payload.doc_types, payload.regenerate)
    return [DocumentOut.model_validate(row) for row in rows]


@router.get("/documentation/{document_id}", response_model=DocumentOut)
async def get_document(document_id: int, user: CurrentUser, session: DbSession) -> DocumentOut:
    docs = DocumentRepository(session)
    row = await docs.get(document_id)
    if not row:
        raise NotFoundError("Document not found")
    await RepositoryService(session).get_or_404(row.repository_id, user)
    return DocumentOut.model_validate(row)


@router.delete("/documentation/{document_id}", response_model=MessageResponse)
async def delete_document(document_id: int, user: CurrentUser, session: DbSession) -> MessageResponse:
    docs = DocumentRepository(session)
    row = await docs.get(document_id)
    if not row:
        raise NotFoundError("Document not found")
    await RepositoryService(session).get_or_404(row.repository_id, user)
    await docs.delete(row)
    await session.commit()
    return MessageResponse(message="Document deleted")
