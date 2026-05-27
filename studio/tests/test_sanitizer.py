"""Tests for the no-gradient guarantee. This is the killer feature."""

from __future__ import annotations

import re

import pytest

from studio.style.palettes import get_palette
from studio.style.sanitizer import sanitize_svg
from studio.style.validator import validate_svg

DUSK = get_palette("dusk")

# ----- helpers -----


def _has_no_gradients(svg: str) -> bool:
    forbidden = ["linearGradient", "radialGradient", "<filter", "<mask", "<image",
                 "<foreignObject", "<pattern", "url(#"]
    return not any(tok in svg for tok in forbidden)


# ----- fixtures -----

CLEAN_LAYERED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path d="M10 50 L50 10 L90 50 Z" fill="#161d3a" data-layer="0" data-role="server-shadow"/>
  <path d="M15 50 L50 15 L85 50 Z" fill="#2c3a6b" data-layer="1" data-role="server-base"/>
  <path d="M20 50 L50 20 L80 50 Z" fill="#5d7bc7" data-layer="2" data-role="server-mid"/>
  <path d="M25 50 L50 25 L75 50 Z" fill="#a8c0ee" data-layer="3" data-role="server-light"/>
</svg>"""

GRADIENT_INJECTED = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <linearGradient id="g1" x1="0" x2="1">
      <stop offset="0" stop-color="#102040"/>
      <stop offset="0.5" stop-color="#3060a0"/>
      <stop offset="1" stop-color="#a0c0ff"/>
    </linearGradient>
    <radialGradient id="g2">
      <stop offset="0" stop-color="#ff0000"/>
      <stop offset="1" stop-color="#00ff00"/>
    </radialGradient>
    <filter id="blur1"><feGaussianBlur stdDeviation="3"/></filter>
  </defs>
  <rect x="10" y="10" width="80" height="80" fill="url(#g1)" filter="url(#blur1)"
        data-layer="0" data-role="card-base"/>
  <circle cx="50" cy="50" r="20" fill="url(#g2)" data-layer="1" data-role="card-mid"/>
  <path d="M30 30 L70 30 L50 70 Z" style="fill: url(#g1); stroke: #112233"
        data-layer="2" data-role="card-light"/>
</svg>"""

OFF_PALETTE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#abcdef" data-layer="0" data-role="bg"/>
  <rect x="10" y="10" width="80" height="80" fill="#13579b" data-layer="1" data-role="card"/>
  <rect x="20" y="20" width="60" height="60" fill="#fedcba" data-layer="2" data-role="inner"/>
</svg>"""

JUNK_AROUND_SVG = """Here is the SVG you asked for!
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
  <rect width="10" height="10" fill="#5d7bc7" data-layer="0" data-role="card-base"/>
  <rect width="5" height="5" fill="#a8c0ee" data-layer="1" data-role="card-light"/>
  <rect width="2" height="2" fill="#e8f0ff" data-layer="2" data-role="card-highlight"/>
</svg>
```
Hope that helps!"""

EXTERNAL_HREF = """<svg xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 50 50">
  <image href="https://evil.example.com/x.png" width="50" height="50"/>
  <use xlink:href="https://evil.example.com/sprite.svg#bad"/>
  <rect width="50" height="50" fill="#2c3a6b" data-layer="0" data-role="card-base"/>
  <rect width="25" height="25" fill="#5d7bc7" data-layer="1" data-role="card-mid"/>
  <rect width="10" height="10" fill="#a8c0ee" data-layer="2" data-role="card-light"/>
</svg>"""


# ----- tests -----


def test_clean_svg_passes_through_unchanged():
    out, report = sanitize_svg(CLEAN_LAYERED, DUSK)
    assert _has_no_gradients(out)
    assert report.gradients_removed == 0
    assert report.refs_remapped == 0
    assert validate_svg(out) == []


def test_gradient_fills_get_remapped_to_palette():
    out, report = sanitize_svg(GRADIENT_INJECTED, DUSK)
    assert _has_no_gradients(out), f"gradients leaked through: {out}"
    assert report.gradients_removed == 2
    assert report.filters_removed == 1
    assert report.refs_remapped >= 2  # the two url(#g1)/url(#g2) fills
    # The url-style on the path should be gone too.
    assert "url(" not in out
    # All fills should now be palette colors.
    fills = re.findall(r'fill="([^"]+)"', out)
    palette_colors = set(c.lower() for c in DUSK.all_colors())
    for fill in fills:
        assert fill.lower() in palette_colors, f"off-palette fill {fill!r} in {out}"


def test_off_palette_colors_snap_to_nearest_palette():
    out, report = sanitize_svg(OFF_PALETTE, DUSK)
    assert report.colors_snapped >= 2
    fills = re.findall(r'fill="([^"]+)"', out)
    palette_colors = set(c.lower() for c in DUSK.all_colors())
    for fill in fills:
        assert fill.lower() in palette_colors


def test_extracts_svg_from_surrounding_junk():
    out, _ = sanitize_svg(JUNK_AROUND_SVG, DUSK)
    assert out.startswith("<svg")
    assert out.endswith("</svg>")
    assert _has_no_gradients(out)


def test_external_hrefs_removed():
    out, report = sanitize_svg(EXTERNAL_HREF, DUSK)
    assert "evil.example.com" not in out
    assert "<image" not in out
    assert report.nodes_removed >= 1


def test_validator_rejects_layered_svg_with_too_few_layers():
    weak = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
      <rect width="10" height="10" fill="#2c3a6b" data-layer="0" data-role="card"/>
    </svg>"""
    errors = validate_svg(weak)
    assert any(e.code == "FEW_LAYERS" for e in errors)


def test_validator_rejects_missing_viewbox():
    bad = """<svg xmlns="http://www.w3.org/2000/svg">
      <rect width="10" height="10" fill="#2c3a6b" data-layer="0" data-role="card"/>
      <rect width="5" height="5" fill="#5d7bc7" data-layer="1" data-role="card-mid"/>
      <rect width="2" height="2" fill="#a8c0ee" data-layer="2" data-role="card-light"/>
    </svg>"""
    errors = validate_svg(bad)
    assert any(e.code == "VIEWBOX" for e in errors)


def test_sanitize_then_validate_full_pipeline():
    out, _ = sanitize_svg(GRADIENT_INJECTED, DUSK)
    errors = validate_svg(out)
    assert errors == [], f"validation failed after sanitize: {errors}\n\n{out}"


def test_no_svg_raises():
    with pytest.raises(ValueError):
        sanitize_svg("no svg here", DUSK)
