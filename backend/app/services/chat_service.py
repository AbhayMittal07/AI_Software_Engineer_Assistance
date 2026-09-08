"""RAG chat over an indexed repository."""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.models.repository import Repository
from app.models.user import User
from app.repositories.analysis_repository import ChatRepository
from app.services.ai.factory import get_ai_provider
from app.services.ai.prompts import CHAT_SYSTEM, chat_prompt
from app.services.repository_service import RepositoryService
from app.services.vector_store import vector_store

logger = get_logger(__name__)

SUGGESTED_QUESTIONS = [
    "Explain the overall architecture of this repository",
    "How does authentication work here?",
    "Find potential bugs in the core modules",
    "Explain the main entrypoint step by step",
    "Suggest performance optimizations",
    "Generate unit tests for the most critical function",
    "Document the public API",
    "Which parts of this code are hardest to maintain?",
]


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chats = ChatRepository(session)
        self.repos = RepositoryService(session)

    async def ensure_session(self, repo: Repository, user: User, session_id: int | None, first_message: str) -> ChatSession:
        if session_id:
            chat = await self.chats.get_session(session_id, user.id)
            if not chat or chat.repository_id != repo.id:
                raise NotFoundError("Chat session not found")
            return chat
        title = first_message.strip()[:80] or "New conversation"
        chat = await self.chats.create(repository_id=repo.id, user_id=user.id, title=title)
        await self.session.commit()
        return chat

    async def ask(self, repo: Repository, user: User, question: str, session_id: int | None) -> dict[str, Any]:
        chat = await self.ensure_session(repo, user, session_id, question)
        await self.chats.add_message(chat.id, "user", question, [])
        await self.session.commit()

        hits = await vector_store.search(repo.id, question, settings.RAG_TOP_K)
        context = "\n\n".join(
            f"[{index + 1}] {hit['path']}\n{hit['content'][:1800]}" for index, hit in enumerate(hits)
        )
        citations = [
            {"path": hit["path"], "snippet": hit["content"][:400], "score": hit["score"]} for hit in hits
        ]
        history_rows = list(await self.chats.messages(chat.id))[-8:]
        history = "\n".join(f"{row.role.upper()}: {row.content[:800]}" for row in history_rows[:-1])

        provider = get_ai_provider()
        ai_powered = provider.available
        if ai_powered:
            try:
                answer = await provider.generate_text(
                    chat_prompt(question, context, self.repos.analysis_context(repo), history),
                    system=CHAT_SYSTEM,
                    temperature=0.35,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Chat generation failed: %s", str(exc)[:200])
                ai_powered = False
                answer = self._fallback_answer(repo, question, hits)
        else:
            answer = self._fallback_answer(repo, question, hits)

        message: ChatMessage = await self.chats.add_message(chat.id, "assistant", answer, citations)
        await self.session.commit()
        return {
            "session_id": chat.id,
            "message": message,
            "citations": citations,
            "chunks_used": len(hits),
            "ai_powered": ai_powered,
        }

    def _fallback_answer(self, repo: Repository, question: str, hits: list[dict[str, Any]]) -> str:
        snippets = "\n\n".join(
            f"**`{hit['path']}`**\n```\n{hit['content'][:700]}\n```" for hit in hits[:3]
        )
        return (
            f"AI generation is unavailable (no `GEMINI_API_KEY` configured), so here is the retrieved "
            f"context for **{question.strip()}** from `{repo.name}`.\n\n"
            f"**Repository facts**\n"
            f"- Language: {repo.primary_language}\n- Framework: {repo.framework}\n"
            f"- Architecture: {repo.architecture}\n- Files: {repo.file_count} / {repo.total_lines} lines\n\n"
            f"**Most relevant code**\n\n{snippets or '_No indexed chunks matched this question._'}"
        )

    async def sessions(self, repo: Repository, user: User) -> list[dict[str, Any]]:
        rows = await self.chats.sessions_for_repo(repo.id, user.id)
        result = []
        for row in rows:
            result.append(
                {
                    "id": row.id,
                    "repository_id": row.repository_id,
                    "title": row.title,
                    "created_at": row.created_at,
                    "message_count": await self.chats.message_count(row.id),
                }
            )
        return result

    async def messages(self, session_id: int, user: User) -> list[ChatMessage]:
        chat = await self.chats.get_session(session_id, user.id)
        if not chat:
            raise NotFoundError("Chat session not found")
        return list(await self.chats.messages(session_id))

    async def delete_session(self, session_id: int, user: User) -> None:
        chat = await self.chats.get_session(session_id, user.id)
        if not chat:
            raise NotFoundError("Chat session not found")
        await self.chats.delete(chat)
        await self.session.commit()
