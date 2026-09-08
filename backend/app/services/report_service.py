"""PDF report generation using ReportLab."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.analysis import Diagram, Document, Report, Review
from app.models.repository import Repository
from app.models.user import User
from app.repositories.analysis_repository import (
    DiagramRepository,
    DocumentRepository,
    ReportRepository,
    ReviewRepository,
)

logger = get_logger(__name__)

ACCENT = colors.HexColor("#0055FF")
DARK = colors.HexColor("#0F0F0F")
MUTED = colors.HexColor("#71717A")
BORDER = colors.HexColor("#D4D4D8")


def _clean(text: Any, limit: int = 1200) -> str:
    value = re.sub(r"[<>&]", " ", str(text or ""))
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reports = ReportRepository(session)
        self.reviews = ReviewRepository(session)
        self.docs = DocumentRepository(session)
        self.diagrams = DiagramRepository(session)

    async def create_report(
        self, repo: Repository, user: User, review_id: int | None = None,
        include_documentation: bool = True, include_diagrams: bool = True,
    ) -> Report:
        review = None
        if review_id:
            review = await self.reviews.get(review_id)
        if review is None:
            review = await self.reviews.latest_for_repo(repo.id)
        documents = list(await self.docs.for_repo(repo.id)) if include_documentation else []
        diagrams = list(await self.diagrams.for_repo(repo.id)) if include_diagrams else []

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        file_name = f"{re.sub(r'[^A-Za-z0-9_-]', '_', repo.name)}_report_{timestamp}.pdf"
        file_path = settings.report_dir / file_name
        sections = await asyncio.to_thread(
            self._render, file_path, repo, review, documents, diagrams
        )
        report = await self.reports.create(
            repository_id=repo.id,
            review_id=review.id if review else None,
            user_id=user.id,
            title=f"{repo.name} - Engineering Report",
            file_name=file_name,
            file_path=str(file_path),
            size_bytes=file_path.stat().st_size if file_path.exists() else 0,
            sections=sections,
        )
        await self.session.commit()
        return report

    # --------------------------------------------------------------- render
    def _render(
        self,
        path: Path,
        repo: Repository,
        review: Review | None,
        documents: Sequence[Document],
        diagrams: Sequence[Diagram],
    ) -> list[str]:
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20,
                            textColor=DARK, spaceAfter=10)
        h2 = ParagraphStyle("H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                            textColor=ACCENT, spaceBefore=14, spaceAfter=6)
        body = ParagraphStyle("Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9,
                              leading=13, alignment=TA_LEFT, textColor=colors.HexColor("#27272A"))
        mono = ParagraphStyle("Monox", parent=body, fontName="Courier", fontSize=7.5, leading=9.5)
        label = ParagraphStyle("Labelx", parent=body, fontName="Helvetica-Bold", fontSize=8, textColor=MUTED)

        doc = SimpleDocTemplate(
            str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=16 * mm, bottomMargin=16 * mm,
            title=f"{repo.name} Engineering Report", author="AI Software Engineering Assistant",
        )
        story: list[Any] = []
        sections: list[str] = []

        def table(rows: list[list[str]], widths: list[float], header: bool = True) -> Table:
            tbl = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
            style = [
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            if header:
                style += [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F4F5")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), DARK),
                ]
            tbl.setStyle(TableStyle(style))
            return tbl

        # Cover / summary
        story.append(Paragraph("AI SOFTWARE ENGINEERING REPORT", label))
        story.append(Paragraph(_clean(repo.name, 120), h1))
        story.append(Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')} &nbsp;|&nbsp; "
            f"Source: {repo.source_type.value} &nbsp;|&nbsp; Status: {repo.status.value}", body))
        story.append(Spacer(1, 8))
        sections.append("Repository Summary")
        story.append(Paragraph("1. Repository Summary", h2))
        story.append(table([
            ["Property", "Value", "Property", "Value"],
            ["Primary language", _clean(repo.primary_language, 40), "Framework", _clean(repo.framework, 40)],
            ["Architecture", _clean(repo.architecture, 40), "Project type", _clean(repo.project_type, 40)],
            ["Package manager", _clean(repo.package_manager, 40), "Build tool", _clean(repo.build_tool, 40)],
            ["Files", str(repo.file_count), "Lines of code", str(repo.total_lines)],
            ["Size (KB)", str(round(repo.size_bytes / 1024, 1)), "Indexed chunks", str(repo.indexed_chunks)],
        ], [32 * mm, 45 * mm, 32 * mm, 45 * mm]))

        sections.append("Metrics")
        story.append(Paragraph("2. Quality Metrics", h2))
        if review:
            story.append(table([
                ["Metric", "Score", "Metric", "Score"],
                ["Code quality", f"{review.quality_score}/100", "Maintainability", f"{review.maintainability_score}/100"],
                ["Security", f"{review.security_score}/100", "Performance", f"{review.performance_score}/100"],
                ["Complexity", f"{review.complexity_score}/100", "Technical debt", f"{review.technical_debt_score}/100"],
                ["Scalability", f"{review.scalability_score}/100", "AI powered", "Yes" if review.ai_powered else "Static only"],
            ], [38 * mm, 38 * mm, 38 * mm, 38 * mm]))
            story.append(Spacer(1, 6))
            sections.append("Review Summary")
            story.append(Paragraph("3. Review Summary", h2))
            story.append(Paragraph(_clean(review.summary, 3000), body))
        else:
            story.append(Paragraph("No completed review is available for this repository yet.", body))

        if review:
            story.append(PageBreak())
            sections.append("Security Findings")
            story.append(Paragraph("4. Security Findings (OWASP)", h2))
            if review.security_findings:
                rows = [["Severity", "Title", "OWASP / CWE", "File:Line", "Remediation"]]
                for item in review.security_findings[:20]:
                    rows.append([
                        _clean(item.get("severity"), 10).upper(),
                        Paragraph(_clean(item.get("title"), 90), mono),
                        Paragraph(f"{_clean(item.get('owasp'), 40)}<br/>{_clean(item.get('cwe'), 15)}", mono),
                        Paragraph(f"{_clean(item.get('file'), 46)}:{item.get('line', 0)}", mono),
                        Paragraph(_clean(item.get("remediation"), 200), mono),
                    ])
                story.append(table(rows, [16 * mm, 38 * mm, 30 * mm, 34 * mm, 56 * mm]))
            else:
                story.append(Paragraph("No security findings were reported.", body))

            sections.append("Code Quality")
            story.append(Paragraph("5. Code Quality Findings", h2))
            if review.findings:
                rows = [["Sev", "Category", "Finding", "File:Line", "Recommendation"]]
                for item in review.findings[:24]:
                    rows.append([
                        _clean(item.get("severity"), 8).upper(),
                        _clean(item.get("category"), 14),
                        Paragraph(_clean(item.get("title"), 110), mono),
                        Paragraph(f"{_clean(item.get('file'), 46)}:{item.get('line', 0)}", mono),
                        Paragraph(_clean(item.get("recommendation") or item.get("description"), 220), mono),
                    ])
                story.append(table(rows, [14 * mm, 22 * mm, 44 * mm, 34 * mm, 60 * mm]))
            else:
                story.append(Paragraph("No findings were reported.", body))

            story.append(PageBreak())
            sections.append("Performance Report")
            story.append(Paragraph("6. Performance & Complexity", h2))
            rows = [["File", "Function", "Cyclomatic", "Time", "Space"]]
            for item in (review.complexity_analysis or [])[:18]:
                rows.append([
                    Paragraph(_clean(item.get("file"), 50), mono),
                    Paragraph(_clean(item.get("function"), 30), mono),
                    str(item.get("cyclomatic", "-")),
                    _clean(item.get("time_complexity"), 14),
                    _clean(item.get("space_complexity"), 14),
                ])
            if len(rows) > 1:
                story.append(table(rows, [54 * mm, 38 * mm, 22 * mm, 30 * mm, 30 * mm]))
            else:
                story.append(Paragraph("No complexity hotspots detected.", body))

            sections.append("Recommendations")
            story.append(Paragraph("7. Recommendations", h2))
            recommendations = [
                *[f"Refactor: {_clean(item.get('title'), 160)}" for item in (review.refactoring_suggestions or [])[:8]],
                *[f"Optimise: {_clean(item.get('title'), 160)}" for item in (review.optimization_suggestions or [])[:8]],
                *[f"{_clean(item.get('area'), 40)} ({_clean(item.get('status'), 20)}): {_clean(item.get('action'), 140)}"
                  for item in (review.best_practices or [])[:8]],
            ]
            if recommendations:
                for line in recommendations:
                    story.append(Paragraph(f"&bull; {line}", body))
            else:
                story.append(Paragraph("No recommendations were generated.", body))

        if diagrams:
            story.append(PageBreak())
            sections.append("Diagrams")
            story.append(Paragraph("8. Architecture Diagrams (source)", h2))
            for diagram in diagrams[:6]:
                block = [
                    Paragraph(f"{_clean(diagram.title, 80)} &mdash; {diagram.diagram_type}", label),
                    Paragraph(_clean(diagram.mermaid, 2200).replace(" ", "&nbsp;"), mono),
                    Spacer(1, 6),
                ]
                story.append(KeepTogether(block))

        if documents:
            story.append(PageBreak())
            sections.append("Documentation")
            story.append(Paragraph("9. Documentation Extracts", h2))
            for document in documents[:6]:
                story.append(Paragraph(_clean(document.title, 90), label))
                story.append(Paragraph(_clean(document.content, 2600), body))
                story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "Generated by the AI Software Engineering Assistant. Findings are advisory and should be "
            "validated by an engineer before acting on them.", label))
        doc.build(story)
        logger.info("Report written to %s", path)
        return sections
