"""Ollama backend: talks to a local Ollama daemon at OLLAMA_HOST."""

from __future__ import annotations

import os

import httpx

from studio.core.llm import LLMError, LLMMessage

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("STUDIO_OLLAMA_MODEL", "qwen2.5-coder:7b-instruct")


class OllamaClient:
    """Sync httpx client against /api/chat. No streaming for now — generators
    are bounded by `max_tokens` and the request finishes in one shot."""

    name = "ollama"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self._client = httpx.Client(base_url=self.host, timeout=timeout)

    def health(self) -> bool:
        try:
            r = self._client.get("/api/tags")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        seed: int | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if seed is not None:
            payload["options"]["seed"] = seed
        try:
            r = self._client.post("/api/chat", json=payload)
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama request failed: {e}") from e
        if r.status_code != 200:
            raise LLMError(f"Ollama returned HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        msg = data.get("message") or {}
        content = msg.get("content") or ""
        if not content:
            raise LLMError(f"Ollama returned empty content; raw={data}")
        return content
