"""OpenAI-compatible client: LM Studio, llama-server --api, Groq, HF router."""

from __future__ import annotations

import os

from studio.core.llm import LLMError, LLMMessage


class OpenAICompatClient:
    name = "openai_compat"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMError("Install with: pip install 'studio-svg[openai]'") from e
        self.model = model or os.environ.get("STUDIO_OPENAI_MODEL", "qwen2.5-coder")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:1234/v1")
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=api_key or os.environ.get("OPENAI_API_KEY", "not-needed"),
            timeout=timeout,
        )

    def health(self) -> bool:
        try:
            # Lightweight probe; some local servers don't have /models — fall back to chat.
            self._client.models.list()
            return True
        except Exception:
            try:
                self.chat(
                    [LLMMessage("user", "ping")],
                    max_tokens=4,
                    temperature=0.0,
                )
                return True
            except Exception:
                return False

    def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        seed: int | None = None,
    ) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed,
            )
        except Exception as e:
            raise LLMError(f"OpenAI-compatible request failed: {e}") from e
        if not resp.choices:
            raise LLMError("OpenAI-compatible response had no choices.")
        return resp.choices[0].message.content or ""
