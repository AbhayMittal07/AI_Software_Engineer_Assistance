"""Repository model holding detected project intelligence."""
import enum
from typing import Any

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin


class RepoSource(str, enum.Enum):
    zip = "zip"
    github = "github"


class RepoStatus(str, enum.Enum):
    pending = "pending"
    analyzing = "analyzing"
    ready = "ready"
    failed = "failed"


class Repository(Base, PKMixin, TimestampMixin):
    __tablename__ = "repositories"
    __table_args__ = (
        Index("ix_repositories_user_created", "user_id", "created_at"),
        Index("ix_repositories_user_status", "user_id", "status"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    source_type: Mapped[RepoSource] = mapped_column(Enum(RepoSource, native_enum=False, length=20), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    branch: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    storage_path: Mapped[str] = mapped_column(String(600), default="", nullable=False)
    status: Mapped[RepoStatus] = mapped_column(
        Enum(RepoStatus, native_enum=False, length=20), default=RepoStatus.pending, nullable=False, index=True
    )
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)

    primary_language: Mapped[str] = mapped_column(String(60), default="Unknown", nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(120), default="Unknown", nullable=False)
    architecture: Mapped[str] = mapped_column(String(160), default="Unknown", nullable=False)
    project_type: Mapped[str] = mapped_column(String(120), default="Unknown", nullable=False)
    package_manager: Mapped[str] = mapped_column(String(80), default="Unknown", nullable=False)
    build_tool: Mapped[str] = mapped_column(String(80), default="Unknown", nullable=False)

    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    languages: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    dependencies: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    entrypoints: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    file_tree: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    indexed_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="repositories")  # noqa: F821
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    diagrams: Mapped[list["Diagram"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
