# Studio — local-AI SVG generator

Generates modern, **layered, no-gradient, 3D-look** SVG visuals — icons, 3D
papercraft clip art, and cloud/AI architecture diagrams (charts, graphs, tables,
custom viz coming in v1) — driven by a local AI model (Ollama by default), with
a tagged, searchable library on disk.

The "3D look" comes from **stacking flat solid-color polygons** like cut paper
— never gradients. A multi-stage sanitizer guarantees that no gradient, filter,
mask, or off-palette color ever ships, no matter what the model emits.

```
$ studio generate clipart_3d_layered "isometric data center" \
        --palette cobalt --aspect 16:9 --layering 5 \
        --component server --component database --component router
```

## Features

- **Three ways in**: CLI (`studio …`), HTTP API (`studio serve`), MCP server
  (`studio mcp`, for Claude Desktop / claude.ai web).
- **Local-first**: works against your own Ollama by default. Auto-detects
  OpenAI-compatible local servers (LM Studio, llama-server) or Hugging Face
  Inference (free token tier) as fallbacks.
- **Free hosting**: a static GitHub Pages gallery reads the committed
  `library/index.json`; an HF Space exposes the FastAPI backend for browsers.
- **Tagged library**: every generated asset is committed to disk with auto +
  user tags (`type:icon`, `palette:dusk`, `domain:aws`, …) — searchable and
  re-usable forever.
- **Structured inputs beyond the prompt**: pass `style_mode` (`flat` /
  `layered_3d`), aspect ratio, target component list, shape vocabulary,
  composition hint, grouping, and per-palette color overrides.
- **Deterministic recolor**: re-skin any asset to any palette without a model
  call (instant, lossless). Lineage is tracked via `parent_slug`.

## 📱 Verify on your phone (1-tap, no install)

Pick whichever loads fastest for you — each is free, each gives a public URL:

| Service | What it gives you | Tap to deploy |
|---|---|---|
| **Vercel** (fastest, ~30s) | Static site (gallery + verify + browser-side HF generator) on a `*.vercel.app` URL | [Deploy to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fmonksudo%2FCarnatic_music&branch=claude%2Flocal-ai-3d-visuals-hYSiJ&project-name=studio-svg) |
| **Cloudflare Pages** | Same site, on a `*.pages.dev` URL | [pages.cloudflare.com](https://pages.cloudflare.com) → Connect Git → pick this repo |
| **Netlify** | Same site, on a `*.netlify.app` URL | [netlify.com/start](https://app.netlify.com/start) → Connect GitHub → pick this repo |
| **GitHub Pages** (slowest setup but built-in) | `https://<your-username>.github.io/Carnatic_music/` | One time: open [repo Settings → Pages](https://github.com/monksudo/Carnatic_music/settings/pages) on your phone, set **Source: GitHub Actions**, Save. Next push auto-deploys. |

After the URL is live you get **three pages** on your phone:
- `/` — gallery of all 7 seeded SVGs (proof the no-gradient layered look works)
- `/verify.html` — **interactive editor**: swap palettes, recolor any layer/role, toggle layers, download. 100% client-side.
- `/generator.html` — playground. Switch to the **HF Inference** tab, paste a free HF token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), and generate brand-new SVGs from your phone with no backend at all.

## Verify it works (free, zero install)

Two free paths, neither requires installing anything locally:

### 1. GitHub Pages — live URL with editor

After the `Deploy gallery to GitHub Pages` workflow runs on this branch (it
triggers automatically on every push), Pages will host three pages at:

- `https://<your-gh-username>.github.io/<repo-name>/`
  → gallery of all seeded SVGs
- `…/verify.html` → **interactive editor**: pick any seed, swap palette,
  tweak per-stop / per-role colors, toggle layers, download the result.
  100% client-side, zero backend.
- `…/generator.html` → playground that calls either a local API *or*
  the **Hugging Face Inference API** directly from your browser using your
  own free HF token (no backend, no install).

First-time setup the user has to do once: in repo settings, **Pages → Build
and deployment → Source: GitHub Actions**. The next workflow run will print
the URL.

### 2. Open the files locally (one-liner)

```bash
cd studio
python3 -m studio.web.dev_serve     # binds 127.0.0.1:8000
```

That builds a temp dir mirroring the GH Pages layout (HTMLs + JS + library
side-by-side) and serves it. Prints the gallery / verify / generator URLs on
start. Stdlib-only: no `pip install` required to run this command, only the
package being importable. Browsers block `fetch()` from `file://`, which is
why a server is needed.

### 3. Generate brand-new SVGs without a local model

Open `generator.html`, switch to the **HF Inference** tab, paste a free
Hugging Face token (from <https://huggingface.co/settings/tokens>), pick a
type / palette / structured options, and hit Generate. The system prompt and
the sanitizer both run in your browser — the only network call is directly
to `api-inference.huggingface.co`. The token stays in browser memory; this
site never touches it.

## Install

```bash
pip install -e ./studio                # or:  pip install studio-svg
pip install -e ./studio[raster,mcp]    # add PNG export + MCP server

# Pull a local model
ollama serve
ollama pull qwen2.5-coder:7b-instruct
```

Smoke-test the install:
```bash
studio doctor       # ✓ LLM backend ok, ✓ raster backend ok
studio types
studio palettes
```

## Quick start

```bash
# Single-color icon (papercraft style) using the "dusk" palette.
studio generate icon "aws lambda" --palette dusk --tag domain:aws

# Slide-ready 3-component architecture diagram in 16:9.
studio generate arch_diagram "user → api gateway → postgres database" \
    --palette cobalt --aspect 16:9 --layering 4 \
    --component user --component api-gateway --component database \
    --tag domain:aws --tag style:papercraft

# Re-skin a previous result without re-running the model (instant).
studio recolor user-api-gateway-postgres-database --palette forest

# Export PNG at 1024px wide.
studio export user-api-gateway-postgres-database --format png --width 1024

# Search + tag the library.
studio search "lambda"
studio list --tag domain:aws
studio tag aws-lambda +icon-set:aws-core
```

## API

Start the FastAPI server:
```bash
studio serve   # http://127.0.0.1:8000  (docs at /docs)
```

```http
POST /generate
{
  "type": "arch_diagram",
  "prompt": "user → api → db",
  "palette": "cobalt",
  "aspect_ratio": "16:9",
  "layering": 5,
  "components": ["user", "api-gateway", "database"],
  "combinations": "user on left, db on right",
  "tags": ["domain:aws"]
}
```

## MCP — Claude Desktop / claude.ai

```bash
pip install -e ./studio[mcp]
studio mcp                   # runs the MCP server over stdio
```

`~/.config/claude/claude_desktop_config.json` (or the macOS equivalent):
```json
{
  "mcpServers": {
    "studio": {
      "command": "studio",
      "args": ["mcp"]
    }
  }
}
```

Tools exposed: `studio.generate`, `studio.search`, `studio.get`,
`studio.recolor`, `studio.tag`, `studio.list_palettes`, `studio.list_types`.

## Backends

| Backend | When to use | Set |
|---|---|---|
| Ollama (default) | You run a model locally | `OLLAMA_HOST`, `STUDIO_OLLAMA_MODEL` |
| OpenAI-compatible | LM Studio, llama-server, Groq free | `OPENAI_BASE_URL`, `STUDIO_OPENAI_MODEL` |
| Hugging Face | Free serverless tier | `HF_TOKEN`, `STUDIO_HF_MODEL` |
| Auto | Probe in the order above | `STUDIO_BACKEND=auto` (default) |

Recommended models:

- Local: `qwen2.5-coder:7b-instruct` (default), `qwen2.5-coder:14b-instruct`, `deepseek-coder-v2:16b-lite-instruct`.
- HF Inference: `Qwen/Qwen2.5-Coder-32B-Instruct`, `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct`.

## How "no gradients, 3D look" actually ships

Defense in depth (all four must agree before output is saved):

1. **Prompt**: system prompt forbids gradients/filters/masks and teaches the
   "papercraft" technique (each depth slice = a flat-fill polygon with
   `data-layer="N"` and `data-role="…"`).
2. **Palette injection**: the active palette's 5 ramp stops + 4 utility colors
   are embedded in the prompt — the model is told to use only those hex codes.
3. **Sanitizer** (`studio/style/sanitizer.py`): parses the SVG with `lxml`,
   strips every `<linearGradient>`/`<radialGradient>`/`<filter>`/`<mask>`/`<image>`,
   rewrites every `url(#…)` reference to the palette swatch nearest the
   gradient's mid-stop (OKLab ΔE), snaps any off-palette solid color, and drops
   external `href` links.
4. **Validator**: rejects output missing a `viewBox`, with no `data-role`, with
   < N layers, or with any lingering gradient/filter reference. On fail → 1
   retry with the violation echoed back to the model. Two failures → hard error.

## Repo layout

```
studio/
  studio/         Python package
    core/         LLM client + per-backend adapters + system prompts
    generators/   per-type generators + structured options
    style/        palettes, sanitizer, validator, recolor
    library/      JSON-indexed asset store + seed data
    renderer/     SVG → PNG (resvg-py)
    cli/          Typer CLI
    api/          FastAPI app
    mcp/          MCP server (stdio)
    web/          static gallery + generator playground
  spaces/         HF Spaces wrapper (Dockerfile + app.py)
  npm/            `npx @monksudo/studio-mcp` launcher
  tests/          pytest suite (sanitizer, recolor, generator pipeline)
```

## Tests

```bash
cd studio && pytest -v
```

The sanitizer + validator are covered by golden-fixture tests that include a
deliberately-malicious SVG (gradient + filter + off-palette + external href +
junk wrapper) to prove they survive contact with real-world model output.
