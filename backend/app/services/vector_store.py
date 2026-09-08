"""ChromaDB-backed vector store for repository RAG."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.ai.factory import get_ai_provider
from app.services.code_analyzer import CODE_LANGUAGES, AnalysisResult, _read_text

logger = get_logger(__name__)


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    lines = text.splitlines()
    chunks: List[str] = []
    buffer: List[str] = []
    length = 0
    for line in lines:
        buffer.append(line)
        length += len(line) + 1
        if length >= size:
            chunks.append("\n".join(buffer))
            keep = max(int(len(buffer) * (overlap / max(size, 1))), 2)
            buffer = buffer[-keep:]
            length = sum(len(item) + 1 for item in buffer)
    if buffer:
        chunks.append("\n".join(buffer))
    return [c for c in chunks if c.strip()]


class VectorStore:
    def __init__(self) -> None:
        self._client = None

    def _get_collection(self):
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            Path(settings.CHROMA_PATH).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PATH,
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )
        return self._client.get_or_create_collection(
            name="repository_chunks", metadata={"hnsw:space": "cosine"}
        )

    async def index_repository(self, repo_id: int, root: Path, analysis: AnalysisResult) -> int:
        provider = get_ai_provider()
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []
        ids: List[str] = []

        for info in analysis.files:
            if len(documents) >= settings.RAG_MAX_CHUNKS_PER_REPO:
                break
            if info.language not in CODE_LANGUAGES and info.language not in {"Markdown", "YAML", "JSON", "SQL"}:
                continue
            content = _read_text(root / info.path, 120_000)
            if not content.strip():
                continue
            for index, chunk in enumerate(
                chunk_text(content, settings.RAG_CHUNK_SIZE, settings.RAG_CHUNK_OVERLAP)
            ):
                if len(documents) >= settings.RAG_MAX_CHUNKS_PER_REPO:
                    break
                documents.append(f"FILE: {info.path}\nLANGUAGE: {info.language}\n\n{chunk}")
                metadatas.append(
                    {"repo_id": repo_id, "path": info.path, "language": info.language, "chunk": index}
                )
                ids.append(f"repo{repo_id}-{re.sub(r'[^A-Za-z0-9]', '_', info.path)}-{index}")

        if not documents:
            return 0

        await self.delete_repository(repo_id)
        embeddings = await provider.embed_texts(documents)
        collection = self._get_collection()
        batch = 128
        for start in range(0, len(documents), batch):
            await asyncio.to_thread(
                collection.upsert,
                ids=ids[start : start + batch],
                documents=documents[start : start + batch],
                metadatas=metadatas[start : start + batch],
                embeddings=embeddings[start : start + batch],
            )
        logger.info("Indexed %s chunks for repository %s", len(documents), repo_id)
        return len(documents)

    async def search(self, repo_id: int, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        provider = get_ai_provider()
        top_k = top_k or settings.RAG_TOP_K
        try:
            vector = (await provider.embed_texts([query]))[0]
            collection = self._get_collection()
            result = await asyncio.to_thread(
                collection.query,
                query_embeddings=[vector],
                n_results=top_k,
                where={"repo_id": repo_id},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:  # noqa: BLE001 - retrieval must never break chat
            logger.warning("Vector search failed: %s", str(exc)[:200])
            return []

        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        hits: List[Dict[str, Any]] = []
        for doc, meta, dist in zip(docs, metas, dists):
            hits.append(
                {
                    "path": (meta or {}).get("path", "unknown"),
                    "language": (meta or {}).get("language", ""),
                    "content": doc,
                    "score": round(1 - float(dist), 4) if dist is not None else None,
                }
            )
        return hits

    async def delete_repository(self, repo_id: int) -> None:
        try:
            collection = self._get_collection()
            await asyncio.to_thread(collection.delete, where={"repo_id": repo_id})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector delete failed for repo %s: %s", repo_id, str(exc)[:160])


vector_store = VectorStore()
