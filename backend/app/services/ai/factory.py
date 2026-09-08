"""AI provider factory + offline fallback provider."""
import hashlib
import math
from functools import lru_cache
from typing import Any, Dict, List

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.services.ai.base import AIProvider
from app.services.ai.gemini_provider import GeminiProvider


class NullProvider(AIProvider):
    """Used when no API key is configured.

    Text generation raises a clear error (callers fall back to deterministic
    analysis) while embeddings use a stable hashing vectoriser so that RAG
    indexing and retrieval keep working offline.
    """

    name = "none"

    def __init__(self) -> None:
        self.text_model = "deterministic-fallback"
        self.embed_model = "hashing-vectorizer-768"

    @property
    def available(self) -> bool:
        return False

    async def generate_text(self, prompt: str, *, system: str | None = None, temperature: float = 0.3) -> str:
        raise AIServiceError("No AI provider configured. Set GEMINI_API_KEY in backend/.env")

    async def generate_json(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.2
    ) -> Dict[str, Any]:
        raise AIServiceError("No AI provider configured. Set GEMINI_API_KEY in backend/.env")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [hashing_vector(text) for text in texts]


def hashing_vector(text: str, dim: int = 768) -> List[float]:
    vector = [0.0] * dim
    tokens = [t for t in text.lower().replace("\n", " ").split() if t]
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


@lru_cache
def get_ai_provider() -> AIProvider:
    provider_name = (settings.AI_PROVIDER or "gemini").lower()
    if provider_name == "gemini" and settings.ai_enabled:
        return GeminiProvider(settings.GEMINI_API_KEY)
    return NullProvider()
