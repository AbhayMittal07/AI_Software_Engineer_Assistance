"""Repository/review/document/diagram/report/chat data-access layer."""
from typing import Any, Sequence

from sqlalchemy import asc, desc, func, select

from app.models.analysis import Diagram, Document, Report, Review
from app.models.chat import ChatMessage, ChatSession
from app.models.repository import Repository
from app.repositories.base import BaseRepository

SORTABLE_REPO_FIELDS = {
    "created_at": Repository.created_at,
    "updated_at": Repository.updated_at,
    "name": Repository.name,
    "total_lines": Repository.total_lines,
    "file_count": Repository.file_count,
}


class RepositoryRepository(BaseRepository[Repository]):
    model = Repository

    async def get_owned(self, repo_id: int, user_id: int, is_admin: bool = False) -> Repository | None:
        stmt = select(Repository).where(Repository.id == repo_id)
        if not is_admin:
            stmt = stmt.where(Repository.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def search(
        self,
        user_id: int,
        *,
        is_admin: bool = False,
        query: str | None = None,
        language: str | None = None,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[Sequence[Repository], int]:
        stmt = select(Repository)
        if not is_admin:
            stmt = stmt.where(Repository.user_id == user_id)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(Repository.name.ilike(like) | Repository.description.ilike(like))
        if language and language != "all":
            stmt = stmt.where(Repository.primary_language == language)
        if status and status != "all":
            stmt = stmt.where(Repository.status == status)

        total = int(
            (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        )
        column = SORTABLE_REPO_FIELDS.get(sort_by, Repository.created_at)
        order = asc(column) if sort_dir == "asc" else desc(column)
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return rows, total

    async def recent(self, user_id: int, limit: int = 5, is_admin: bool = False) -> Sequence[Repository]:
        stmt = select(Repository)
        if not is_admin:
            stmt = stmt.where(Repository.user_id == user_id)
        stmt = stmt.order_by(desc(Repository.created_at)).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def language_distribution(self, user_id: int, is_admin: bool = False) -> dict[str, int]:
        stmt = select(Repository.primary_language, func.count(Repository.id))
        if not is_admin:
            stmt = stmt.where(Repository.user_id == user_id)
        stmt = stmt.group_by(Repository.primary_language)
        return {row[0] or "Unknown": int(row[1]) for row in (await self.session.execute(stmt)).all()}


class ReviewRepository(BaseRepository[Review]):
    model = Review

    async def get_owned(self, review_id: int, user_id: int, is_admin: bool = False) -> Review | None:
        stmt = select(Review).where(Review.id == review_id)
        if not is_admin:
            stmt = stmt.where(Review.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def history(
        self,
        user_id: int,
        *,
        is_admin: bool = False,
        repository_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Review], int]:
        stmt = select(Review)
        if not is_admin:
            stmt = stmt.where(Review.user_id == user_id)
        if repository_id:
            stmt = stmt.where(Review.repository_id == repository_id)
        if status and status != "all":
            stmt = stmt.where(Review.status == status)
        total = int(
            (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        )
        stmt = stmt.order_by(desc(Review.created_at)).offset((page - 1) * page_size).limit(page_size)
        return (await self.session.execute(stmt)).scalars().all(), total

    async def latest_for_repo(self, repository_id: int) -> Review | None:
        stmt = (
            select(Review)
            .where(Review.repository_id == repository_id, Review.status == "completed")
            .order_by(desc(Review.created_at))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def completed_for_user(self, user_id: int, is_admin: bool = False, limit: int = 200) -> Sequence[Review]:
        stmt = select(Review).where(Review.status == "completed")
        if not is_admin:
            stmt = stmt.where(Review.user_id == user_id)
        stmt = stmt.order_by(desc(Review.created_at)).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def for_repo(self, repository_id: int) -> Sequence[Document]:
        stmt = select(Document).where(Document.repository_id == repository_id).order_by(asc(Document.id))
        return (await self.session.execute(stmt)).scalars().all()

    async def get_by_type(self, repository_id: int, doc_type: str) -> Document | None:
        stmt = select(Document).where(
            Document.repository_id == repository_id, Document.doc_type == doc_type
        )
        return (await self.session.execute(stmt)).scalars().first()


class DiagramRepository(BaseRepository[Diagram]):
    model = Diagram

    async def for_repo(self, repository_id: int) -> Sequence[Diagram]:
        stmt = select(Diagram).where(Diagram.repository_id == repository_id).order_by(asc(Diagram.id))
        return (await self.session.execute(stmt)).scalars().all()

    async def get_by_type(self, repository_id: int, diagram_type: str) -> Diagram | None:
        stmt = select(Diagram).where(
            Diagram.repository_id == repository_id, Diagram.diagram_type == diagram_type
        )
        return (await self.session.execute(stmt)).scalars().first()


class ReportRepository(BaseRepository[Report]):
    model = Report

    async def for_user(
        self, user_id: int, *, is_admin: bool = False, repository_id: int | None = None
    ) -> Sequence[Report]:
        stmt = select(Report)
        if not is_admin:
            stmt = stmt.where(Report.user_id == user_id)
        if repository_id:
            stmt = stmt.where(Report.repository_id == repository_id)
        stmt = stmt.order_by(desc(Report.created_at))
        return (await self.session.execute(stmt)).scalars().all()

    async def get_owned(self, report_id: int, user_id: int, is_admin: bool = False) -> Report | None:
        stmt = select(Report).where(Report.id == report_id)
        if not is_admin:
            stmt = stmt.where(Report.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class ChatRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def sessions_for_repo(self, repository_id: int, user_id: int) -> Sequence[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.repository_id == repository_id, ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.created_at))
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def get_session(self, session_id: int, user_id: int) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def messages(self, session_id: int) -> Sequence[ChatMessage]:
        stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(asc(ChatMessage.id))
        return (await self.session.execute(stmt)).scalars().all()

    async def add_message(self, session_id: int, role: str, content: str, citations: list[Any]) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content, citations=citations)
        self.session.add(message)
        await self.session.flush()
        return message

    async def message_count(self, session_id: int) -> int:
        stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session_id)
        return int((await self.session.execute(stmt)).scalar() or 0)
