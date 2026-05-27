"""Hugging Face Spaces wrapper around studio.api.app.

Free CPU tier: install studio + ship a small GGUF locally via llama-cpp-python.
Or set HF_TOKEN as a Space secret and the auto-detect path will use the
HF Inference API instead (much faster).

Run with:  python app.py
"""

from __future__ import annotations

import os

import uvicorn

# Re-export the FastAPI app so HF's auto-detection (gradio/asgi) finds it.
from studio.api.app import app  # noqa: F401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("studio.api.app:app", host="0.0.0.0", port=port)
