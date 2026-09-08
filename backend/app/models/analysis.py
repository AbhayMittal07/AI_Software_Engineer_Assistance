"""Review, documentation, diagram and report models."""
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Review(Base, PKMixin, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_repo_created", "repository_id", "created_at"),)

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False, length=20), default=ReviewStatus.pending, nullable=False, index=True
    )
    depth: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    provider: Mapped[str] = mapped_column(String(40), default="gemini", nullable=False)
    model: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    ai_powered: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)

    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    maintainability_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    security_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    performance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    complexity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    technical_debt_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scalability_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    findings: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    security_findings: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    performance_findings: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    code_smells: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    dead_code: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    duplicate_code: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    unused_symbols: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    complexity_analysis: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    solid_violations: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    design_patterns: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    dependency_analysis: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    refactoring_suggestions: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    optimization_suggestions: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    auto_fixes: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    generated_tests: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    clean_architecture: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    best_practices: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="reviews")  # noqa: F821
    reports: Mapped[list["Report"]] = relationship(back_populates="review")


class Document(Base, PKMixin, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_repo_type", "repository_id", "doc_type"),)

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ai_powered: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="documents")  # noqa: F821


class Diagram(Base, PKMixin, TimestampMixin):
    __tablename__ = "diagrams"
    __table_args__ = (Index("ix_diagrams_repo_type", "repository_id", "diagram_type"),)

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    diagram_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    mermaid: Mapped[str] = mapped_column(Text, default="", nullable=False)
    plantuml: Mapped[str] = mapped_column(Text, default="", nullable=False)
    drawio_xml: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ai_powered: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="diagrams")  # noqa: F821


class Report(Base, PKMixin, TimestampMixin):
    __tablename__ = "reports"

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_id: Mapped[int | None] = mapped_column(
        ForeignKey("reviews.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sections: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)

    repository: Mapped["Repository"] = relationship(back_populates="reports")  # noqa: F821
    review: Mapped["Review | None"] = relationship(back_populates="reports")
