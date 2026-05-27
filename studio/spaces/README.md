---
title: Studio SVG
emoji: 🎨
colorFrom: indigo
colorTo: teal
sdk: docker
pinned: false
license: mit
---

# Studio (free CPU tier)

Hosted Hugging Face Space for the Studio SVG generator. Two ways to run:

- **HF Inference API** (recommended, fast). Set `HF_TOKEN` as a Space secret;
  `STUDIO_BACKEND=hf` is already set. Default model:
  `Qwen/Qwen2.5-Coder-32B-Instruct`. Override with `STUDIO_HF_MODEL`.
- **No-token demo** (slow). Without `HF_TOKEN`, every `/generate` call returns
  a 503 with instructions. We deliberately do NOT auto-fetch a GGUF on free CPU —
  cold-start would exceed Space timeouts.

API surface is documented at the root after deploy: `/docs`.
