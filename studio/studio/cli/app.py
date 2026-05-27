"""Studio CLI — Typer + Rich.

Examples:
  studio generate icon "aws lambda" --palette dusk
  studio generate clipart_3d_layered "isometric data center" \\
        --palette cobalt --aspect 16:9 --layering 5 \\
        --component server --component database --component user
  studio recolor my-aws-lambda --palette forest
  studio export my-aws-lambda --format png --width 1024
  studio search "aws"   # or:  studio list --tag domain:aws
  studio tag my-aws-lambda +domain:aws +style:papercraft
  studio palettes
  studio types
  studio serve
  studio mcp
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from studio.core.detect import detect_backend
from studio.core.llm import LLMError
from studio.generators import (
    GenerationOptions,
    GeneratorError,
    get_generator,
    list_types,
)
from studio.library.store import Library
from studio.renderer.raster import RasterizeError, rasterize
from studio.renderer.raster import available as raster_available
from studio.style.palettes import get_palette, list_palettes
from studio.style.recolor import list_roles, recolor

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Studio — local-AI SVG generator (layered, no-gradient, 3D look).",
)
console = Console()
err_console = Console(stderr=True, style="bold red")


def _library() -> Library:
    return Library()


def _parse_color_overrides(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise typer.BadParameter(
                f"--color must be NAME=HEX, got {item!r}. "
                "Names: highlight, light, mid, base, shadow, accent_a, accent_b, background, ink."
            )
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", v):
            raise typer.BadParameter(f"--color value must be #RGB or #RRGGBB, got {v!r}")
        out[k] = v
    return out


# ----------------------------- generate -----------------------------


@app.command()
def generate(
    type_name: str = typer.Argument(..., help="Generator type. Run `studio types` to list."),
    prompt: str = typer.Argument(..., help="Free-form description of what to draw."),
    palette: str = typer.Option("dusk", "--palette", "-p", help="Named palette."),
    aspect: str | None = typer.Option(None, "--aspect", "-a", help="Aspect ratio: 1:1, 16:9, 4:3, or WxH"),
    width: int | None = typer.Option(None, "--width", "-w", help="Explicit viewBox width."),
    height: int | None = typer.Option(None, "--height", "-h", help="Explicit viewBox height."),
    style_mode: str = typer.Option("layered_3d", "--style", help="flat | layered_3d"),
    layering: int = typer.Option(4, "--layering", "-l", min=1, max=6, help="Depth slice count target."),
    projection: str | None = typer.Option(None, "--projection", help="front | isometric | top | 3q"),
    component: list[str] = typer.Option([], "--component", "-c", help="Required component (repeatable)."),
    shape: list[str] = typer.Option([], "--shape", help="Preferred shape vocabulary (repeatable)."),
    combinations: str = typer.Option("", "--combinations", help="Composition hint."),
    grouping: bool = typer.Option(True, "--grouping/--no-grouping", help="Wrap components in <g>."),
    color: list[str] = typer.Option([], "--color", help="Palette override: name=#hex (repeatable)."),
    seed: int | None = typer.Option(None, "--seed", help="Random seed."),
    temperature: float = typer.Option(0.4, "--temperature", "-t", min=0.0, max=2.0),
    tag: list[str] = typer.Option([], "--tag", help="Tags to attach (repeatable)."),
    title: str | None = typer.Option(None, "--title", help="Override title in library."),
    description: str = typer.Option("", "--description", help="Long description for the library."),
    out: Path | None = typer.Option(None, "--out", "-o", help="Also save SVG to this path."),
    no_save: bool = typer.Option(False, "--no-save", help="Don't add to library."),
    print_svg: bool = typer.Option(False, "--print", help="Print the SVG to stdout."),
):
    """Generate a new SVG."""
    if style_mode not in {"flat", "layered_3d"}:
        raise typer.BadParameter(f"--style must be flat|layered_3d, got {style_mode!r}")
    try:
        pal = get_palette(palette)
        gen_cls = get_generator(type_name)
    except KeyError as e:
        err_console.print(str(e))
        raise typer.Exit(2) from e

    try:
        llm = detect_backend()
    except LLMError as e:
        err_console.print(f"LLM backend not available: {e}")
        raise typer.Exit(3) from e

    opts = GenerationOptions(
        aspect_ratio=aspect,
        width=width,
        height=height,
        style_mode=style_mode,  # type: ignore[arg-type]
        layering=layering,
        projection=projection,  # type: ignore[arg-type]
        components=list(component or []),
        shapes=list(shape or []),
        combinations=combinations or "",
        grouping=grouping,
        color_overrides=_parse_color_overrides(color),
        temperature=temperature,
        seed=seed,
    )

    console.print(
        f"[cyan]→ generating {type_name} | palette={palette} | "
        f"style={style_mode} | layering={layering} | backend={llm.name}:{llm.model}[/cyan]"
    )
    try:
        result = gen_cls(llm).generate(prompt, pal, opts)
    except GeneratorError as e:
        err_console.print(str(e))
        raise typer.Exit(4) from e

    if print_svg:
        sys.stdout.write(result.svg + "\n")

    if out:
        out = Path(out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.svg, encoding="utf-8")
        console.print(f"[green]✓ wrote[/green] {out}")

    if not no_save:
        lib = _library()
        asset = lib.add_from_result(
            result, title=title, description=description, tags=list(tag or [])
        )
        console.print(
            f"[green]✓ added to library[/green] slug=[bold]{asset.slug}[/bold] "
            f"path={asset.svg_path}  attempts={result.attempts}"
        )
        if result.sanitize_report.gradients_removed or result.sanitize_report.refs_remapped:
            console.print(
                f"[yellow]sanitizer note:[/yellow] removed "
                f"{result.sanitize_report.gradients_removed} gradient defs, "
                f"remapped {result.sanitize_report.refs_remapped} url(#) refs."
            )


# ----------------------------- recolor -----------------------------


@app.command(name="recolor")
def recolor_cmd(
    slug: str = typer.Argument(..., help="Slug of an existing library asset."),
    palette: str = typer.Option(..., "--palette", "-p", help="Target palette."),
    title: str | None = typer.Option(None, "--title"),
    tag: list[str] = typer.Option([], "--tag"),
):
    """Re-skin an existing asset to a new palette (deterministic, no LLM)."""
    lib = _library()
    source = lib.get(slug)
    if not source:
        err_console.print(f"unknown slug: {slug}")
        raise typer.Exit(2)
    src_pal = get_palette(source.palette)
    tgt_pal = get_palette(palette)
    svg = lib.read_svg(slug)
    new_svg, report = recolor(svg, src_pal, tgt_pal)
    new_asset = lib.add_raw(
        new_svg,
        type_name=source.type,
        title=title or f"{source.title} [{palette}]",
        description=source.description,
        palette=palette,
        model=source.model,
        prompt=source.prompt,
        tags=sorted(set([*source.tags, *tag]) - {f"palette:{source.palette}"}),
        parent_slug=slug,
        seed=source.seed,
        slug_hint=f"{source.slug}-{palette}",
    )
    console.print(
        f"[green]✓ recolored[/green] {slug} → {new_asset.slug}  "
        f"(fills_changed={report.fills_changed}, strokes_changed={report.strokes_changed})"
    )


# ----------------------------- export -----------------------------


@app.command()
def export(
    slug: str = typer.Argument(...),
    format: str = typer.Option("png", "--format", "-f", help="png | svg"),
    width: int | None = typer.Option(None, "--width", "-w"),
    height: int | None = typer.Option(None, "--height", "-h"),
    out: Path | None = typer.Option(None, "--out", "-o"),
):
    """Export an asset to a file (or stdout for SVG)."""
    lib = _library()
    asset = lib.get(slug)
    if not asset:
        err_console.print(f"unknown slug: {slug}")
        raise typer.Exit(2)
    svg = lib.read_svg(slug)
    if format == "svg":
        if out:
            Path(out).write_text(svg, encoding="utf-8")
            console.print(f"[green]✓ wrote[/green] {out}")
        else:
            sys.stdout.write(svg)
        return
    if format != "png":
        raise typer.BadParameter("--format must be png|svg")
    try:
        png = rasterize(svg, width=width, height=height)
    except RasterizeError as e:
        err_console.print(str(e))
        raise typer.Exit(5) from e
    target = Path(out) if out else (lib.root / "png" / f"{slug}.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(png)
    if not out:
        lib.write_png(slug, png)
    console.print(f"[green]✓ wrote[/green] {target}")


# ----------------------------- library ops -----------------------------


@app.command(name="list")
def list_cmd(
    type_name: str | None = typer.Option(None, "--type", "-t"),
    tag: list[str] = typer.Option([], "--tag"),
    limit: int = typer.Option(40, "--limit", "-n"),
):
    """List library assets."""
    lib = _library()
    results = lib.search(type_name=type_name, tags=list(tag or []), limit=limit)
    _print_assets(results)


@app.command()
def search(
    query: str = typer.Argument(...),
    type_name: str | None = typer.Option(None, "--type", "-t"),
    tag: list[str] = typer.Option([], "--tag"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Full-text search across the library."""
    lib = _library()
    results = lib.search(query, type_name=type_name, tags=list(tag or []), limit=limit)
    _print_assets(results)


@app.command()
def tag(
    slug: str = typer.Argument(...),
    items: list[str] = typer.Argument(..., help="+tag to add, -tag to remove."),
):
    """Edit tags on an asset:  studio tag SLUG +domain:aws -style:flat"""
    add: list[str] = []
    remove: list[str] = []
    for it in items:
        if it.startswith("+"):
            add.append(it[1:])
        elif it.startswith("-"):
            remove.append(it[1:])
        else:
            add.append(it)
    lib = _library()
    try:
        asset = lib.update_tags(slug, add=add, remove=remove)
    except KeyError as e:
        err_console.print(f"unknown slug: {slug}")
        raise typer.Exit(2) from e
    console.print(f"[green]✓ tags updated[/green] {asset.slug}: {', '.join(asset.tags)}")


@app.command()
def delete(slug: str):
    """Delete an asset from the library."""
    lib = _library()
    try:
        lib.delete(slug)
    except KeyError as e:
        err_console.print(f"unknown slug: {slug}")
        raise typer.Exit(2) from e
    console.print(f"[green]✓ deleted[/green] {slug}")


@app.command()
def info(slug: str):
    """Show full metadata for an asset."""
    lib = _library()
    asset = lib.get(slug)
    if not asset:
        err_console.print(f"unknown slug: {slug}")
        raise typer.Exit(2)
    svg = lib.read_svg(slug)
    roles = list_roles(svg)
    out = asset.as_dict()
    out["roles"] = roles
    console.print(json.dumps(out, indent=2))


# ----------------------------- introspection -----------------------------


@app.command()
def palettes():
    """List available palettes."""
    table = Table(title="Palettes")
    table.add_column("id")
    table.add_column("name")
    table.add_column("description")
    table.add_column("ramp")
    for p in list_palettes():
        ramp = " ".join(p.ramp())
        table.add_row(p.id, p.name, p.description, ramp)
    console.print(table)


@app.command()
def types():
    """List available generator types."""
    for t in list_types():
        console.print(f"  • {t}")


@app.command()
def doctor():
    """Diagnose LLM backend + raster availability."""
    ok, raster_name = raster_available()
    console.print(f"raster backend: [bold]{raster_name}[/bold] ({'ok' if ok else 'MISSING — pip install studio-svg[raster]'})")
    try:
        llm = detect_backend()
        console.print(f"LLM backend: [bold green]{llm.name}[/bold green] model=[bold]{llm.model}[/bold] healthy=[bold]{llm.health()}[/bold]")
    except LLMError as e:
        console.print(f"[red]LLM backend: NOT AVAILABLE[/red] — {e}")


# ----------------------------- serve / mcp -----------------------------


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
):
    """Start the FastAPI server."""
    import uvicorn

    uvicorn.run("studio.api.app:app", host=host, port=port, reload=False)


@app.command()
def mcp():
    """Start the MCP stdio server (for Claude Desktop)."""
    try:
        from studio.mcp.server import run_stdio
    except ImportError as e:
        err_console.print(f"MCP server requires extras: pip install 'studio-svg[mcp]' — {e}")
        raise typer.Exit(6) from e
    run_stdio()


# ----------------------------- helpers -----------------------------


def _print_assets(rows):
    if not rows:
        console.print("[dim]no assets[/dim]")
        return
    table = Table(show_lines=False)
    table.add_column("slug")
    table.add_column("type")
    table.add_column("palette")
    table.add_column("title", overflow="fold")
    table.add_column("tags", overflow="fold")
    for a in rows:
        table.add_row(a.slug, a.type, a.palette, a.title, ", ".join(a.tags))
    console.print(table)


def main() -> None:  # entry point referenced by [project.scripts]
    app()


if __name__ == "__main__":
    main()
