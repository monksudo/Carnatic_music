"""Auto-detect an available LLM backend.

Probe order:
  1. $STUDIO_BACKEND  ("ollama" | "openai" | "hf")  — explicit user choice
  2. Ollama at $OLLAMA_HOST (default 127.0.0.1:11434)
  3. OpenAI-compatible server at $OPENAI_BASE_URL  (LM Studio / llama-server)
  4. Hugging Face Inference API   ($HF_TOKEN set)
  5. Fail with a clear error message.
"""

from __future__ import annotations

import os

from studio.core.llm import LLMClient, LLMError
from studio.core.ollama import OllamaClient


def detect_backend() -> LLMClient:
    explicit = os.environ.get("STUDIO_BACKEND", "").lower().strip()
    if explicit == "ollama":
        return _ollama_or_die()
    if explicit in {"openai", "openai_compat"}:
        return _openai_or_die()
    if explicit in {"hf", "huggingface"}:
        return _hf_or_die()

    # Auto-probe.
    client: LLMClient | None = None
    try:
        client = OllamaClient()
        if client.health():
            return client
    except Exception:
        pass

    if os.environ.get("OPENAI_BASE_URL"):
        try:
            return _openai_or_die()
        except LLMError:
            pass

    if os.environ.get("HF_TOKEN"):
        try:
            return _hf_or_die()
        except LLMError:
            pass

    raise LLMError(
        "No LLM backend reachable. Tried Ollama at $OLLAMA_HOST, "
        "$OPENAI_BASE_URL, and Hugging Face. Either start `ollama serve` and "
        "`ollama pull qwen2.5-coder:7b-instruct`, set OPENAI_BASE_URL to an "
        "OpenAI-compatible local server, or set HF_TOKEN."
    )


def _ollama_or_die() -> OllamaClient:
    c = OllamaClient()
    if not c.health():
        raise LLMError(f"Ollama not reachable at {c.host}. Run `ollama serve`.")
    return c


def _openai_or_die() -> LLMClient:
    try:
        from studio.core.openai_compat import OpenAICompatClient
    except ImportError as e:
        raise LLMError(f"OpenAI client not installed: pip install 'studio-svg[openai]' — {e}") from e
    c = OpenAICompatClient()
    if not c.health():
        raise LLMError("OpenAI-compatible endpoint did not respond.")
    return c


def _hf_or_die() -> LLMClient:
    try:
        from studio.core.hf_inference import HFInferenceClient
    except ImportError as e:
        raise LLMError(f"huggingface_hub not installed: pip install 'studio-svg[hf]' — {e}") from e
    c = HFInferenceClient()
    if not c.health():
        raise LLMError("Hugging Face Inference endpoint did not respond.")
    return c
