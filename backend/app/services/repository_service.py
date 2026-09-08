"""Repository ingestion: ZIP upload, GitHub clone, analysis and RAG indexing."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.models.analysis import Report
from app.models.repository import RepoSource, RepoStatus, Repository
from app.models.user import User
from app.repositories.analysis_repository import RepositoryRepository
from app.services.code_analyzer import code_analyzer
from app.services.vector_store import vector_store

logger = get_logger(__name__)

GITHUB_URL_RE = re.compile(r"^https?://(www\.)?(github|gitlab|bitbucket)\.[a-z]+/[\w.\-]+/[\w.\-]+(\.git)?/?$")


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._\- ]", "", value).strip()
    return cleaned[:120] or "repository"


class RepositoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repos = RepositoryRepository(session)

    # ------------------------------------------------------------ ingestion
    async def create_from_zip(
        self, user: User, filename: str, payload: bytes, description: str = ""
    ) -> Repository:
        if not filename.lower().endswith(".zip"):
            raise ValidationError("Only .zip archives are supported")
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if len(payload) > max_bytes:
            raise ValidationError(f"Archive exceeds the {settings.MAX_UPLOAD_MB}MB limit")

        name = safe_name(Path(filename).stem)
        repo = await self.repos.create(
            user_id=user.id,
            name=name,
            description=description,
            source_type=RepoSource.zip,
            status=RepoStatus.analyzing,
        )
        await self.session.commit()

        target = settings.repo_dir / f"repo_{repo.id}"
        archive_path = settings.upload_dir / f"repo_{repo.id}.zip"
        try:
            archive_path.write_bytes(payload)
            await asyncio.to_thread(self._extract_zip, archive_path, target)
            repo.storage_path = str(self._flatten_root(target))
            await self.session.commit()
        except Exception as exc:  # noqa: BLE001
            repo.status = RepoStatus.failed
            repo.error_message = str(exc)[:500]
            await self.session.commit()
            raise AppError(f"Failed to extract archive: {exc}") from exc
        finally:
            archive_path.unlink(missing_ok=True)

        await self.analyze(repo)
        return repo

    async def create_from_github(
        self, user: User, url: str, branch: str | None, name: str | None, description: str = ""
    ) -> Repository:
        if not GITHUB_URL_RE.match(url):
            raise ValidationError("Provide a valid public GitHub/GitLab/Bitbucket repository URL")
        repo_name = safe_name(name or url.rstrip("/").split("/")[-1].replace(".git", ""))
        repo = await self.repos.create(
            user_id=user.id,
            name=repo_name,
            description=description,
            source_type=RepoSource.github,
            source_url=url,
            branch=branch or "",
            status=RepoStatus.analyzing,
        )
        await self.session.commit()

        target = settings.repo_dir / f"repo_{repo.id}"
        try:
            await asyncio.to_thread(self._clone, url, branch, target)
            repo.storage_path = str(target)
            await self.session.commit()
        except Exception as exc:  # noqa: BLE001
            repo.status = RepoStatus.failed
            repo.error_message = str(exc)[:500]
            await self.session.commit()
            raise AppError(f"Clone failed: {str(exc)[:300]}") from exc

        await self.analyze(repo)
        return repo

    @staticmethod
    def _extract_zip(archive: Path, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            members = zf.infolist()
            if len(members) > settings.MAX_FILES_PER_REPO * 2:
                raise ValueError("Archive contains too many entries")
            for member in members:
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    continue  # zip-slip protection
                zf.extract(member, target)

    @staticmethod
    def _clone(url: str, branch: str | None, target: Path) -> None:
        import git

        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        kwargs: dict[str, Any] = {"depth": 1, "single_branch": True}
        if branch:
            kwargs["branch"] = branch
        env = {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "echo", **os.environ}
        git.Repo.clone_from(url, str(target), env=env, **kwargs)
        shutil.rmtree(target / ".git", ignore_errors=True)

    @staticmethod
    def _flatten_root(target: Path) -> Path:
        entries = [p for p in target.iterdir() if p.name not in {"__MACOSX", ".DS_Store"}]
        if len(entries) == 1 and entries[0].is_dir():
            return entries[0]
        return target

    # ------------------------------------------------------------- analysis
    async def analyze(self, repo: Repository) -> Repository:
        root = Path(repo.storage_path)
        if not root.exists():
            repo.status = RepoStatus.failed
            repo.error_message = "Repository files are missing on disk"
            await self.session.commit()
            raise NotFoundError("Repository files are missing on disk")

        repo.status = RepoStatus.analyzing
        await self.session.commit()
        try:
            result = await asyncio.to_thread(code_analyzer.analyze, root)
            repo.primary_language = result.primary_language
            repo.languages = result.languages
            repo.framework = result.framework
            repo.architecture = result.architecture
            repo.project_type = result.project_type
            repo.package_manager = result.package_manager
            repo.build_tool = result.build_tool
            repo.file_count = result.file_count
            repo.total_lines = result.total_lines
            repo.size_bytes = result.size_bytes
            repo.dependencies = result.dependencies
            repo.entrypoints = result.entrypoints
            repo.file_tree = result.file_tree
            repo.metrics = {**result.metrics, "env_vars": result.env_vars[:40]}
            repo.status = RepoStatus.ready
            repo.error_message = ""
            await self.session.commit()

            try:
                chunks = await vector_store.index_repository(repo.id, root, result)
                repo.indexed_chunks = chunks
                await self.session.commit()
            except Exception as exc:  # noqa: BLE001 - indexing is best-effort
                logger.warning("RAG indexing failed for repo %s: %s", repo.id, str(exc)[:200])
        except Exception as exc:  # noqa: BLE001
            repo.status = RepoStatus.failed
            repo.error_message = str(exc)[:500]
            await self.session.commit()
            raise
        return repo

    # -------------------------------------------------------------- queries
    async def get_or_404(self, repo_id: int, user: User) -> Repository:
        repo = await self.repos.get_owned(repo_id, user.id, user.role.value == "admin")
        if not repo:
            raise NotFoundError("Repository not found")
        return repo

    async def delete(self, repo: Repository) -> None:
        repo_id = repo.id
        report_rows = await self.session.execute(select(Report).where(Report.repository_id == repo_id))
        for report in report_rows.scalars().all():
            if report.file_path:
                Path(report.file_path).unlink(missing_ok=True)

        await self.repos.delete(repo)
        await self.session.commit()
        await vector_store.delete_repository(repo_id)

        if repo.storage_path:
            path = Path(repo.storage_path).resolve()
            allowed_root = settings.repo_dir.resolve()
            if allowed_root == path or allowed_root in path.parents:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        path.unlink(missing_ok=True)
        else:
            root = settings.repo_dir / f"repo_{repo_id}"
            if root.exists():
                shutil.rmtree(root, ignore_errors=True)

    def read_file(self, repo: Repository, rel_path: str) -> dict[str, Any]:
        root = Path(repo.storage_path).resolve()
        candidate = (root / rel_path).resolve()
        if not str(candidate).startswith(str(root)):
            raise ValidationError("Invalid file path")
        if not candidate.is_file():
            raise NotFoundError("File not found in repository")
        size = candidate.stat().st_size
        if size > 1_000_000:
            raise ValidationError("File is too large to preview")
        from app.services.code_analyzer import EXTENSION_LANGUAGE, _read_text

        content = _read_text(candidate, 200_000)
        return {
            "path": rel_path,
            "language": EXTENSION_LANGUAGE.get(candidate.suffix.lower(), "Other"),
            "lines": content.count("\n") + 1,
            "size_bytes": size,
            "content": content,
            "truncated": size > 200_000,
        }

    def analysis_context(self, repo: Repository) -> str:
        return (
            f"Repository name: {repo.name}\nSource: {repo.source_type.value} {repo.source_url}\n"
            f"Primary language: {repo.primary_language}\nFramework: {repo.framework}\n"
            f"Architecture: {repo.architecture}\nProject type: {repo.project_type}\n"
            f"Package manager: {repo.package_manager}\nBuild tool: {repo.build_tool}\n"
            f"Files: {repo.file_count}, Lines: {repo.total_lines}\n"
            f"Languages: {repo.languages}\n"
            f"Dependencies: {', '.join(d.get('name', '') for d in (repo.dependencies or [])[:40])}\n"
            f"Entrypoints: {', '.join(repo.entrypoints or [])}\n"
            f"Static metrics: {repo.metrics}"
        )
