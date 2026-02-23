"""LLM client wrapper for Claude API calls."""

import logging
from typing import Optional

import anthropic

from config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Async wrapper around the Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or settings.llm_model
        self._max_tokens = settings.llm_max_tokens
        self._client: Optional[anthropic.AsyncAnthropic] = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY not set. Add it to your .env file."
                )
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key, timeout=300.0)
        return self._client

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: Optional[int] = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a prompt to Claude and return the response text."""
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens or self._max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        try:
            response = await client.messages.create(**kwargs)
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def complete_with_json(
        self,
        prompt: str,
        system: str = "",
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a prompt expecting JSON output."""
        json_system = (system + "\n\n" if system else "")
        json_system += "Respond with valid JSON only. No markdown, no explanation."
        return await self.complete(
            prompt, system=json_system, max_tokens=max_tokens, temperature=0.1
        )

    async def complete_with_vision(
        self,
        prompt: str,
        images: list[dict],
        system: str = "",
        max_tokens: Optional[int] = None,
        temperature: float = 0.3,
    ) -> str:
        """Send a prompt with images to Claude's vision API.

        Args:
            images: list of dicts with "base64" and optional "media_type" keys.
        """
        client = self._get_client()

        content: list[dict] = []
        for img in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.get("media_type", "image/png"),
                    "data": img["base64"],
                },
            })
        content.append({"type": "text", "text": prompt})

        messages = [{"role": "user", "content": content}]
        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens or self._max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        try:
            response = await client.messages.create(**kwargs)
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude Vision API error: {e}")
            raise
