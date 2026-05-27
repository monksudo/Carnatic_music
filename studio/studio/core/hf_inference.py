"""Hugging Face Inference API client — the free-tier serverless path.

Requires `pip install 'studio-svg[hf]'` and `HF_TOKEN` env var.
"""

from __future__ import annotations

import os

from studio.core.llm import LLMError, LLMMessage

DEFAULT_MODEL = os.environ.get(
    "STUDIO_HF_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct"
)


class HFInferenceClient:
    name = "hf_inference"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        token: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        try:
            from huggingface_hub import InferenceClient
        except ImportError as e:
            raise LLMError("Install with: pip install 'studio-svg[hf]'") from e
        tok = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        if not tok:
            raise LLMError("HF_TOKEN env var not set.")
        self.model = model
        self._client = InferenceClient(model=model, token=tok, timeout=timeout)

    def health(self) -> bool:
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
            resp = self._client.chat_completion(
                messages=[{"role": m.role, "content": m.content} for m in messages],
                max_tokens=max_tokens,
                temperature=temperature,
                seed=seed,
            )
        except Exception as e:
            raise LLMError(f"HF Inference request failed: {e}") from e
        choices = getattr(resp, "choices", None) or []
        if not choices:
            raise LLMError("HF Inference response had no choices.")
        return choices[0].message.content or ""
