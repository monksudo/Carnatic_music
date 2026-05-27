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
