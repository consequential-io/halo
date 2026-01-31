"""
LLM Client abstraction for Gemini API.
Provides unified interface for text generation with structured output.
"""

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Structured response from LLM."""
    content: str
    model: str
    usage: dict[str, int] | None = None
    error: str | None = None


class LLMClient:
    """
    LLM client for Gemini API.

    Usage:
        client = LLMClient()
        response = await client.generate(prompt="...")
    """

    def __init__(self, provider: str | None = None):
        self.provider = provider or settings.ai_provider
        self.api_key = settings.gemini_api_key
        self.timeout = settings.llm_timeout_seconds
        self.model = settings.gemini_model

        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. LLM enrichment will be skipped.")

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Generate text using Gemini API.

        Args:
            prompt: User prompt with grounding context
            system: Optional system instructions
            temperature: Sampling temperature (0.0-1.0), low for factual responses
            max_tokens: Maximum response tokens

        Returns:
            LLMResponse with content or error
        """
        if not self.api_key:
            logger.info("LLM reasoning disabled: GEMINI_API_KEY not configured.")
            return LLMResponse(
                content="",
                model=self.model,
                error="API key not configured"
            )

        try:
            return await self._generate_gemini(prompt, system, temperature, max_tokens)
        except httpx.TimeoutException:
            logger.warning(f"LLM request timed out after {self.timeout}s. Using template reasoning.")
            return LLMResponse(
                content="",
                model=self.model,
                error=f"Request timed out after {self.timeout}s"
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"LLM API error: {e.response.status_code}. Using template reasoning.")
            return LLMResponse(
                content="",
                model=self.model,
                error=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            logger.warning(f"LLM generation failed: {type(e).__name__}: {e}. Using template reasoning.")
            return LLMResponse(
                content="",
                model=self.model,
                error=str(e)
            )

    async def _generate_gemini(
        self,
        prompt: str,
        system: str | None,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate using Google Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        # Build request payload
        contents = []

        # Add system instruction if provided
        if system:
            contents.append({
                "role": "user",
                "parts": [{"text": system}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "I understand. I will follow these instructions."}]
            })

        # Add user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            # Extract content from Gemini response
            try:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                logger.warning(f"Failed to parse Gemini response structure: {e}")
                return LLMResponse(
                    content="",
                    model=self.model,
                    error=f"Invalid response structure: {e}"
                )

            # Extract usage if available
            usage = None
            if "usageMetadata" in data:
                usage = {
                    "prompt_tokens": data["usageMetadata"].get("promptTokenCount", 0),
                    "completion_tokens": data["usageMetadata"].get("candidatesTokenCount", 0),
                    "total_tokens": data["usageMetadata"].get("totalTokenCount", 0),
                }

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                error=None,
            )
