"""LLMClient protocol + a tiny dataclass for messages.

Every backend (Ollama, openai-compat, HF Inference, future Gemini/SD) implements
this same surface so generators don't care which one is wired in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class LLMError(RuntimeError):
    """Raised when an LLM backend can't fulfill a request."""


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@runtime_checkable
class LLMClient(Protocol):
    """Minimal sync chat interface. We don't need streaming for the MVP."""

    name: str
    model: str

    def chat(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        seed: int | None = None,
    ) -> str: ...

    def health(self) -> bool: ...
