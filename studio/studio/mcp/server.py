"""MCP server exposing Studio over stdio (for Claude Desktop).

The official `mcp` Python SDK exposes both stdio and HTTP/SSE transports; this
module wires the stdio one. We expose the same tool surface as the CLI:

  studio.generate(type, prompt, palette, options...) → asset
  studio.search(query, type?, tags?)               → [asset_meta]
  studio.get(slug, format='svg'|'png')             → content
  studio.recolor(slug, palette)                    → new_slug
  studio.export(slug, format, width?, height?)     → bytes
  studio.tag(slug, add[], remove[])
  studio.list_palettes / studio.list_types

NB: tool results > 32KB are returned via a `studio://asset/<slug>` resource URI
rather than inline payloads.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from studio.core.detect import detect_backend
from studio.core.llm import LLMError
from studio.generators import GenerationOptions, GeneratorError, get_generator, list_types
from studio.library.store import Library
from studio.renderer.raster import RasterizeError, rasterize
from studio.style.palettes import get_palette, list_palettes
from studio.style.recolor import recolor

INLINE_LIMIT = 32 * 1024


def _serialize_asset(asset, svg: str | None = None) -> dict[str, Any]:
    d = asset.as_dict()
    if svg is None or len(svg) > INLINE_LIMIT:
        d["svg_uri"] = f"studio://asset/{asset.slug}"
    else:
        d["svg"] = svg
    return d


def build_server():
    """Construct the MCP server. Imported lazily so the import doesn't fail
    when the optional `mcp` extra isn't installed."""
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError(
            "MCP extras not installed. Run: pip install 'studio-svg[mcp]'"
        ) from e

    server = Server("studio-svg")

    # ----- tool: studio.generate -----

    @server.list_tools()
    async def list_tools_handler() -> list[Tool]:  # noqa: D401
        return [
            Tool(
                name="studio.generate",
                description=(
                    "Generate a new layered, no-gradient SVG. Accepts type, prompt, "
                    "palette, plus structured options: aspect_ratio, style_mode (flat|layered_3d), "
                    "layering, components, shapes, combinations, color_overrides."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["type", "prompt"],
                    "properties": {
                        "type": {"type": "string", "enum": list_types()},
                        "prompt": {"type": "string"},
                        "palette": {"type": "string", "default": "dusk"},
                        "aspect_ratio": {"type": "string"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                        "style_mode": {"type": "string", "enum": ["flat", "layered_3d"]},
                        "layering": {"type": "integer", "minimum": 1, "maximum": 6},
                        "projection": {"type": "string", "enum": ["front", "isometric", "top", "3q"]},
                        "components": {"type": "array", "items": {"type": "string"}},
                        "shapes": {"type": "array", "items": {"type": "string"}},
                        "combinations": {"type": "string"},
                        "grouping": {"type": "boolean", "default": True},
                        "color_overrides": {"type": "object", "additionalProperties": {"type": "string"}},
                        "temperature": {"type": "number"},
                        "seed": {"type": "integer"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "save": {"type": "boolean", "default": True},
                    },
                },
            ),
            Tool(
                name="studio.search",
                description="Search the library by free-text query and/or tag filters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "type": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            ),
            Tool(
                name="studio.get",
                description="Fetch an asset by slug. format='svg' returns SVG text; format='png' returns base64 PNG.",
                inputSchema={
                    "type": "object",
                    "required": ["slug"],
                    "properties": {
                        "slug": {"type": "string"},
                        "format": {"type": "string", "enum": ["svg", "png"], "default": "svg"},
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                },
            ),
            Tool(
                name="studio.recolor",
                description="Deterministically re-skin an existing asset to a new palette (no LLM call).",
                inputSchema={
                    "type": "object",
                    "required": ["slug", "palette"],
                    "properties": {
                        "slug": {"type": "string"},
                        "palette": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="studio.tag",
                description="Add/remove tags on an asset.",
                inputSchema={
                    "type": "object",
                    "required": ["slug"],
                    "properties": {
                        "slug": {"type": "string"},
                        "add": {"type": "array", "items": {"type": "string"}},
                        "remove": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
            Tool(
                name="studio.list_palettes",
                description="List available palettes.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="studio.list_types",
                description="List available generator types.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool_handler(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        args = arguments or {}
        try:
            payload = _dispatch(name, args)
        except (KeyError, LLMError, GeneratorError, RasterizeError, ValueError) as e:
            payload = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]

    return server


def _dispatch(name: str, args: dict[str, Any]) -> dict[str, Any]:
    lib = Library()
    if name == "studio.generate":
        pal = get_palette(args.get("palette") or "dusk")
        gen_cls = get_generator(args["type"])
        llm = detect_backend()
        opts = GenerationOptions(
            aspect_ratio=args.get("aspect_ratio"),
            width=args.get("width"),
            height=args.get("height"),
            style_mode=args.get("style_mode") or "layered_3d",  # type: ignore[arg-type]
            layering=int(args.get("layering") or 4),
            projection=args.get("projection"),  # type: ignore[arg-type]
            components=list(args.get("components") or []),
            shapes=list(args.get("shapes") or []),
            combinations=args.get("combinations") or "",
            grouping=bool(args.get("grouping", True)),
            color_overrides=dict(args.get("color_overrides") or {}),
            temperature=float(args.get("temperature") or 0.4),
            seed=args.get("seed"),
        )
        res = gen_cls(llm).generate(args["prompt"], pal, opts)
        if args.get("save", True):
            asset = lib.add_from_result(
                res,
                title=args.get("title"),
                description=args.get("description") or "",
                tags=list(args.get("tags") or []),
            )
            return _serialize_asset(asset, res.svg)
        return {
            "svg": res.svg if len(res.svg) <= INLINE_LIMIT else None,
            "svg_uri": None if len(res.svg) <= INLINE_LIMIT else "studio://transient",
            "generator": res.generator,
            "palette": res.palette_id,
            "attempts": res.attempts,
            "sanitize_report": res.sanitize_report.as_dict(),
        }

    if name == "studio.search":
        q = args.get("query") or ""
        results = lib.search(
            q,
            type_name=args.get("type"),
            tags=list(args.get("tags") or []),
            limit=int(args.get("limit") or 20),
        )
        return {"results": [a.as_dict() for a in results]}

    if name == "studio.get":
        slug = args["slug"]
        asset = lib.get(slug)
        if not asset:
            raise KeyError(slug)
        svg = lib.read_svg(slug)
        fmt = args.get("format") or "svg"
        if fmt == "svg":
            return _serialize_asset(asset, svg)
        if fmt == "png":
            png = rasterize(svg, width=args.get("width"), height=args.get("height"))
            return {
                "asset": asset.as_dict(),
                "png_base64": base64.b64encode(png).decode("ascii"),
            }
        raise ValueError(f"unknown format {fmt}")

    if name == "studio.recolor":
        asset = lib.get(args["slug"])
        if not asset:
            raise KeyError(args["slug"])
        src = get_palette(asset.palette)
        tgt = get_palette(args["palette"])
        svg = lib.read_svg(args["slug"])
        new_svg, report = recolor(svg, src, tgt)
        new_asset = lib.add_raw(
            new_svg,
            type_name=asset.type,
            title=f"{asset.title} [{args['palette']}]",
            description=asset.description,
            palette=args["palette"],
            model=asset.model,
            prompt=asset.prompt,
            tags=sorted(set(asset.tags) - {f"palette:{asset.palette}"}),
            parent_slug=asset.slug,
            seed=asset.seed,
            slug_hint=f"{asset.slug}-{args['palette']}",
        )
        return {
            "asset": _serialize_asset(new_asset, new_svg),
            "fills_changed": report.fills_changed,
            "strokes_changed": report.strokes_changed,
        }

    if name == "studio.tag":
        asset = lib.update_tags(args["slug"], add=list(args.get("add") or []), remove=list(args.get("remove") or []))
        return asset.as_dict()

    if name == "studio.list_palettes":
        return {"palettes": [p.as_dict() for p in list_palettes()]}

    if name == "studio.list_types":
        return {"types": list_types()}

    raise ValueError(f"unknown tool {name}")


def run_stdio() -> None:
    """Block on stdio MCP transport. Used by `studio mcp` and `python -m studio.mcp`."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("pip install 'studio-svg[mcp]' to enable MCP server.") from e

    server = build_server()

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    run_stdio()
