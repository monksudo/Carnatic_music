"""FastAPI surface mirroring the CLI.

Endpoints:
  POST /generate            — generate a new asset
  POST /recolor             — recolor an existing asset to a new palette
  GET  /library             — list / search assets
  GET  /library/{slug}      — fetch a single asset's metadata
  GET  /library/{slug}/svg  — fetch raw SVG
  GET  /library/{slug}/png  — fetch (or render+cache) PNG
  POST /library/{slug}/tags — add/remove tags
  GET  /palettes            — list palettes
  GET  /types               — list generator types
  GET  /health
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from studio.core.detect import detect_backend
from studio.core.llm import LLMError
from studio.generators import GenerationOptions, GeneratorError, get_generator, list_types
from studio.library.store import Library
from studio.renderer.raster import RasterizeError, rasterize
from studio.style.palettes import get_palette, list_palettes
from studio.style.recolor import list_roles, recolor

_TAG_QUERY = Query(default=[])

app = FastAPI(title="Studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # GitHub Pages will read the API; tighten in v1.
    allow_methods=["*"],
    allow_headers=["*"],
)


def _lib() -> Library:
    return Library()


# -------- request / response models --------


class GenerateRequest(BaseModel):
    type: str = Field(..., description="Generator type — see /types")
    prompt: str = Field(..., min_length=1)
    palette: str = "dusk"
    aspect_ratio: str | None = None
    width: int | None = None
    height: int | None = None
    style_mode: str = "layered_3d"
    layering: int = 4
    projection: str | None = None
    components: list[str] = []
    shapes: list[str] = []
    combinations: str = ""
    grouping: bool = True
    color_overrides: dict[str, str] = {}
    temperature: float = 0.4
    seed: int | None = None
    title: str | None = None
    description: str = ""
    tags: list[str] = []
    save: bool = True


class RecolorRequest(BaseModel):
    slug: str
    palette: str
    title: str | None = None
    tags: list[str] = []


class TagRequest(BaseModel):
    add: list[str] = []
    remove: list[str] = []


# -------- routes --------


@app.get("/health")
def health() -> dict:
    try:
        backend = detect_backend()
        return {"ok": True, "backend": backend.name, "model": backend.model}
    except LLMError as e:
        return {"ok": False, "backend": None, "error": str(e)}


@app.get("/palettes")
def palettes() -> list[dict]:
    return [p.as_dict() for p in list_palettes()]


@app.get("/types")
def types() -> list[str]:
    return list_types()


@app.post("/generate")
def generate(req: GenerateRequest) -> dict:
    try:
        pal = get_palette(req.palette)
        gen_cls = get_generator(req.type)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    try:
        llm = detect_backend()
    except LLMError as e:
        raise HTTPException(503, f"No LLM backend available: {e}") from e

    opts = GenerationOptions(
        aspect_ratio=req.aspect_ratio,
        width=req.width,
        height=req.height,
        style_mode=req.style_mode,  # type: ignore[arg-type]
        layering=req.layering,
        projection=req.projection,  # type: ignore[arg-type]
        components=req.components,
        shapes=req.shapes,
        combinations=req.combinations,
        grouping=req.grouping,
        color_overrides=req.color_overrides,
        temperature=req.temperature,
        seed=req.seed,
    )
    try:
        result = gen_cls(llm).generate(req.prompt, pal, opts)
    except GeneratorError as e:
        raise HTTPException(422, str(e)) from e

    body = {
        "svg": result.svg,
        "generator": result.generator,
        "palette": result.palette_id,
        "model": result.model,
        "seed": result.seed,
        "attempts": result.attempts,
        "sanitize_report": result.sanitize_report.as_dict(),
        "options": result.options,
    }
    if req.save:
        asset = _lib().add_from_result(
            result, title=req.title, description=req.description, tags=req.tags
        )
        body["asset"] = asset.as_dict()
    return body


@app.post("/recolor")
def recolor_endpoint(req: RecolorRequest) -> dict:
    lib = _lib()
    asset = lib.get(req.slug)
    if not asset:
        raise HTTPException(404, "unknown slug")
    try:
        src = get_palette(asset.palette)
        tgt = get_palette(req.palette)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    svg = lib.read_svg(req.slug)
    new_svg, report = recolor(svg, src, tgt)
    new_asset = lib.add_raw(
        new_svg,
        type_name=asset.type,
        title=req.title or f"{asset.title} [{req.palette}]",
        description=asset.description,
        palette=req.palette,
        model=asset.model,
        prompt=asset.prompt,
        tags=sorted(set([*asset.tags, *req.tags]) - {f"palette:{asset.palette}"}),
        parent_slug=req.slug,
        seed=asset.seed,
        slug_hint=f"{asset.slug}-{req.palette}",
    )
    return {
        "asset": new_asset.as_dict(),
        "fills_changed": report.fills_changed,
        "strokes_changed": report.strokes_changed,
    }


@app.get("/library")
def library_list(
    q: str = "",
    type: str | None = None,
    tag: list[str] = _TAG_QUERY,
    limit: int = 100,
) -> list[dict]:
    return [a.as_dict() for a in _lib().search(q, type_name=type, tags=tag, limit=limit)]


@app.get("/library/{slug}")
def library_get(slug: str) -> dict:
    lib = _lib()
    asset = lib.get(slug)
    if not asset:
        raise HTTPException(404, "unknown slug")
    svg = lib.read_svg(slug)
    out = asset.as_dict()
    out["roles"] = list_roles(svg)
    return out


@app.get("/library/{slug}/svg")
def library_svg(slug: str) -> PlainTextResponse:
    lib = _lib()
    if not lib.exists(slug):
        raise HTTPException(404, "unknown slug")
    return PlainTextResponse(content=lib.read_svg(slug), media_type="image/svg+xml")


@app.get("/library/{slug}/png")
def library_png(slug: str, width: int | None = None, height: int | None = None) -> Response:
    lib = _lib()
    if not lib.exists(slug):
        raise HTTPException(404, "unknown slug")
    svg = lib.read_svg(slug)
    try:
        png = rasterize(svg, width=width, height=height)
    except RasterizeError as e:
        raise HTTPException(501, str(e)) from e
    return Response(content=png, media_type="image/png")


@app.post("/library/{slug}/tags")
def library_tags(slug: str, req: TagRequest) -> dict:
    lib = _lib()
    try:
        asset = lib.update_tags(slug, add=req.add, remove=req.remove)
    except KeyError as e:
        raise HTTPException(404, "unknown slug") from e
    return asset.as_dict()


@app.delete("/library/{slug}")
def library_delete(slug: str) -> dict:
    lib = _lib()
    try:
        lib.delete(slug)
    except KeyError as e:
        raise HTTPException(404, "unknown slug") from e
    return {"deleted": slug}
