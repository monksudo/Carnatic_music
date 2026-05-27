"""Deterministic recolor + object replacement (no LLM call needed).

Recolor:
  Walk the sanitized SVG, group fills/strokes by their `data-layer` value, and
  remap each layer's color to the new palette's corresponding ramp stop. This is
  lossless and instant. If `data-layer` is missing on some node, we fall back to
  matching the source color to the source palette's nearest ramp stop.

Replace object:
  Find every node carrying `data-role="<role>"` (or its descendants in a
  matching `<g>`), regenerate just that subtree with the LLM, splice it back in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml import etree

from studio.style.palettes import Palette, nearest_palette_color

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _normalize_hex(value: str) -> str | None:
    if not value:
        return None
    m = _HEX_RE.match(value.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h.lower()


# Mapping from layer integer → palette stop name. Larger layer = closer to viewer.
_LAYER_TO_STOP = {
    0: "shadow",
    1: "base",
    2: "mid",
    3: "light",
    4: "highlight",
    5: "highlight",
    6: "highlight",
}


@dataclass
class RecolorReport:
    fills_changed: int = 0
    strokes_changed: int = 0
    layer_counts: dict[str, int] | None = None


def recolor(svg_text: str, source_palette: Palette, target_palette: Palette) -> tuple[str, RecolorReport]:
    """Return new SVG re-skinned to `target_palette`."""
    parser = etree.XMLParser(remove_blank_text=False, recover=True)
    root = etree.fromstring(svg_text.encode("utf-8"), parser=parser)
    report = RecolorReport(layer_counts={})
    src_lookup = _color_to_stop(source_palette)
    target_dict = _palette_dict(target_palette)

    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        layer_attr = el.get("data-layer")
        for attr in ("fill", "stroke"):
            v = el.get(attr)
            if not v:
                continue
            hx = _normalize_hex(v)
            if not hx:
                continue

            # 1. Try mapping by data-layer.
            stop = None
            if layer_attr is not None:
                try:
                    li = int(layer_attr)
                    stop = _LAYER_TO_STOP.get(li, "mid")
                except ValueError:
                    stop = None

            # 2. Fall back: look up the source color by nearest palette stop.
            if stop is None:
                stop = src_lookup.get(hx) or _nearest_stop(hx, source_palette)

            new_color = target_dict[stop]
            if new_color.lower() != hx:
                el.set(attr, new_color)
                if attr == "fill":
                    report.fills_changed += 1
                else:
                    report.strokes_changed += 1
                report.layer_counts[stop] = (report.layer_counts.get(stop, 0)) + 1

    out = etree.tostring(root, pretty_print=False, encoding="unicode")
    return out, report


def _palette_dict(p: Palette) -> dict[str, str]:
    return {
        "highlight": p.highlight,
        "light": p.light,
        "mid": p.mid,
        "base": p.base,
        "shadow": p.shadow,
        "accent_a": p.accent_a,
        "accent_b": p.accent_b,
        "background": p.background,
        "ink": p.ink,
    }


def _color_to_stop(p: Palette) -> dict[str, str]:
    return {v.lower(): k for k, v in _palette_dict(p).items()}


def _nearest_stop(target_hex: str, p: Palette) -> str:
    pal_dict = _palette_dict(p)
    chosen = nearest_palette_color(target_hex, list(pal_dict.values()))
    for stop, col in pal_dict.items():
        if col.lower() == chosen.lower():
            return stop
    return "mid"


def list_roles(svg_text: str) -> list[str]:
    """List every distinct `data-role` value in the SVG."""
    roles: list[str] = []
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(svg_text.encode("utf-8"), parser=parser)
    seen = set()
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        r = el.get("data-role")
        if r and r not in seen:
            seen.add(r)
            roles.append(r)
    return roles
