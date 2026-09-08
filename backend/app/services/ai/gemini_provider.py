"""Google Gemini provider implementation (google-genai SDK)."""
import asyncio
import json
import re
from typing import Any, Dict, List

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.core.logging_config import get_logger
from app.services.ai.base import AIProvider

logger = get_logger(__name__)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(raw: str) -> Dict[str, Any]:
    """Tolerant JSON extraction from an LLM response."""
    if not raw:
        return {}
    text = raw.strip()
    match = _JSON_BLOCK.search(text)
    if match:
        text = match.group(1).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"items": parsed}
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"items": parsed}
        except json.JSONDecodeError:
            pass
    logger.warning("Could not parse JSON from model output (%s chars)", len(raw))
    return {}


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        text_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.text_model = text_model or settings.GEMINI_TEXT_MODEL
        self.embed_model = embed_model or settings.GEMINI_EMBED_MODEL
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            if not self.available:
                raise AIServiceError("GEMINI_API_KEY is not configured")
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def _generate(self, prompt: str, system: str | None, temperature: float, json_mode: bool) -> str:
        client = self._get_client()
        config: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": settings.AI_MAX_OUTPUT_TOKENS,
        }
        if system:
            config["system_instruction"] = system
        if json_mode:
            config["response_mime_type"] = "application/json"

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=self.text_model, contents=prompt, config=config
                    ),
                    timeout=settings.AI_REQUEST_TIMEOUT,
                )
                return (response.text or "").strip()
            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning("Gemini timeout (attempt %s)", attempt + 1)
            except Exception as exc:  # noqa: BLE001 - SDK raises many error types
                last_error = exc
                logger.warning("Gemini error (attempt %s): %s", attempt + 1, str(exc)[:200])
                if "API_KEY_INVALID" in str(exc) or "PERMISSION_DENIED" in str(exc):
                    break
            await asyncio.sleep(1.5 * (attempt + 1))
        raise AIServiceError(f"Gemini request failed: {str(last_error)[:200]}")

    async def generate_text(self, prompt: str, *, system: str | None = None, temperature: float = 0.3) -> str:
        return await self._generate(prompt, system, temperature, json_mode=False)

    async def generate_json(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.2
    ) -> Dict[str, Any]:
        raw = await self._generate(prompt, system, temperature, json_mode=True)
        return extract_json(raw)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        vectors: List[List[float]] = []
        batch_size = 16
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            try:
                response = await asyncio.wait_for(
                    client.aio.models.embed_content(
                        model=self.embed_model,
                        contents=batch,
                        config={"output_dimensionality": 768},
                    ),
                    timeout=settings.AI_REQUEST_TIMEOUT,
                )
                vectors.extend([list(emb.values) for emb in response.embeddings])
            except Exception as exc:  # noqa: BLE001
                raise AIServiceError(f"Gemini embedding failed: {str(exc)[:200]}") from exc
        return vectors
