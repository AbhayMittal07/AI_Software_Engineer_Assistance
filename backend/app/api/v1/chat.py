"""RAG chat endpoints."""
from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.analysis import ChatAnswer, ChatAskRequest, ChatMessageOut, ChatSessionOut
from app.schemas.common import MessageResponse
from app.services.chat_service import SUGGESTED_QUESTIONS, ChatService
from app.services.repository_service import RepositoryService

router = APIRouter(tags=["AI Chat"])


@router.get("/chat/suggestions", response_model=list[str])
async def suggestions() -> list[str]:
    return SUGGESTED_QUESTIONS


@router.get("/repositories/{repo_id}/chat/sessions", response_model=list[ChatSessionOut])
async def list_sessions(repo_id: int, user: CurrentUser, session: DbSession) -> list[ChatSessionOut]:
    repo = await RepositoryService(session).get_or_404(repo_id, user)
    rows = await ChatService(session).sessions(repo, user)
    return [ChatSessionOut(**row) for row in rows]


@router.post("/repositories/{repo_id}/chat", response_model=ChatAnswer)
async def ask(
    repo_id: int, payload: ChatAskRequest, user: CurrentUser, session: DbSession
) -> ChatAnswer:
    repo = await RepositoryService(session).get_or_404(repo_id, user)
    result = await ChatService(session).ask(repo, user, payload.message, payload.session_id)
    return ChatAnswer(
        session_id=result["session_id"],
        answer=ChatMessageOut.model_validate(result["message"]),
        citations=result["citations"],
        chunks_used=result["chunks_used"],
        ai_powered=result["ai_powered"],
    )


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def messages(session_id: int, user: CurrentUser, session: DbSession) -> list[ChatMessageOut]:
    rows = await ChatService(session).messages(session_id, user)
    return [ChatMessageOut.model_validate(row) for row in rows]


@router.delete("/chat/sessions/{session_id}", response_model=MessageResponse)
async def delete_session(session_id: int, user: CurrentUser, session: DbSession) -> MessageResponse:
    await ChatService(session).delete_session(session_id, user)
    return MessageResponse(message="Chat session deleted")
