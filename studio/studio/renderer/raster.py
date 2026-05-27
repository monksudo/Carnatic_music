"""SVG → PNG rasterization (resvg-py primary, cairosvg fallback).

Optional dependency — install with `pip install 'studio-svg[raster]'`. The CLI
and API fall back gracefully when neither is available.
"""

from __future__ import annotations


class RasterizeError(RuntimeError):
    pass


def available() -> tuple[bool, str]:
    try:
        import resvg_py  # noqa: F401

        return True, "resvg-py"
    except ImportError:
        pass
    try:
        import cairosvg  # noqa: F401

        return True, "cairosvg"
    except ImportError:
        return False, "none"


def rasterize(
    svg_text: str,
    *,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
) -> bytes:
    """Render `svg_text` to PNG bytes."""
    try:
        import resvg_py

        opts = {}
        if width:
            opts["width"] = width
        if height:
            opts["height"] = height
        if scale:
            opts["zoom"] = scale
        try:
            return resvg_py.svg_to_bytes(svg_string=svg_text, **opts)  # type: ignore[attr-defined]
        except AttributeError:
            # Older API surface.
            return resvg_py.svg_to_png(svg=svg_text, **opts)  # type: ignore[attr-defined]
    except ImportError:
        pass

    try:
        import cairosvg

        kwargs = {"bytestring": svg_text.encode("utf-8")}
        if width:
            kwargs["output_width"] = width
        if height:
            kwargs["output_height"] = height
        if scale:
            kwargs["scale"] = scale
        return cairosvg.svg2png(**kwargs)
    except ImportError as e:
        raise RasterizeError(
            "Neither resvg-py nor cairosvg is installed. Install raster extras: "
            "pip install 'studio-svg[raster]'"
        ) from e
