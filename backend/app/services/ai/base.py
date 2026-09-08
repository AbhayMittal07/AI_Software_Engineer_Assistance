"""Provider-agnostic AI interface so OpenAI/DeepSeek can be added later."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIProvider(ABC):
    name: str = "base"
    text_model: str = ""
    embed_model: str = ""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether the provider is configured and usable."""

    @abstractmethod
    async def generate_text(self, prompt: str, *, system: str | None = None, temperature: float = 0.3) -> str:
        ...

    @abstractmethod
    async def generate_json(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.2
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...
