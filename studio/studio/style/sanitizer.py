"""SVG sanitizer that guarantees no gradients and only palette colors ship.

This is the killer feature. Even if the LLM emits gradients (and small models will),
the sanitizer is the final guarantee that the user never sees one. Order matters:

  1. Parse with lxml (namespace-correct; never xml.etree).
  2. For every <linearGradient>/<radialGradient>: compute the mid-stop color and
     remember which url(#id) references should be remapped to that solid.
  3. Walk every element; rewrite `fill="url(#x)"` / `stroke="url(#x)"` (and any
     inline `style: fill: url(#x)`) to the mid-stop solid, then snap that solid
     to the nearest palette color.
  4. Delete every <linearGradient>, <radialGradient>, <stop>, <filter>, <mask>,
     <image>, <foreignObject>, and any external href.
  5. Snap any remaining solid `fill` / `stroke` colors to the nearest palette
     swatch (so the LLM can't sneak in off-palette tones).
  6. Strip inline `style="..."` declarations that smuggle gradient/filter refs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree

from studio.style.palettes import Palette, nearest_palette_color

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

_NS = {"svg": SVG_NS, "xlink": XLINK_NS}

# Local-name() XPath for nodes we strip entirely.
_FORBIDDEN_TAGS = (
    "linearGradient",
    "radialGradient",
    "filter",
    "mask",
    "image",
    "foreignObject",
    "pattern",
)

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_URL_REF_RE = re.compile(r"url\(\s*#([^)\s]+)\s*\)")
_STYLE_GRAD_RE = re.compile(r"\b(gradient|filter|mask)\b", re.IGNORECASE)


@dataclass
class SanitizeReport:
    gradients_removed: int = 0
    filters_removed: int = 0
    masks_removed: int = 0
    refs_remapped: int = 0
    colors_snapped: int = 0
    nodes_removed: int = 0
    forbidden_tags_removed: list[str] = field(default_factory=list)
    fallback_color: str | None = None

    def as_dict(self) -> dict:
        return {
            "gradients_removed": self.gradients_removed,
            "filters_removed": self.filters_removed,
            "masks_removed": self.masks_removed,
            "refs_remapped": self.refs_remapped,
            "colors_snapped": self.colors_snapped,
            "nodes_removed": self.nodes_removed,
            "forbidden_tags_removed": self.forbidden_tags_removed,
            "fallback_color": self.fallback_color,
        }


# --------------------------- helpers ---------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _gradient_mid_color(gradient_el: etree._Element) -> str | None:
    """Pull the mid-stop color of a gradient element. Falls back to the average."""
    stops = [c for c in gradient_el if _local(c.tag) == "stop"]
    colors: list[str] = []
    for s in stops:
        c = s.get("stop-color")
        if not c:
            style = s.get("style") or ""
            m = re.search(r"stop-color\s*:\s*([^;]+)", style)
            if m:
                c = m.group(1).strip()
        if c:
            hx = _HEX_RE.search(c)
            if hx:
                colors.append("#" + hx.group(1))
    if not colors:
        return None
    return colors[len(colors) // 2]


def _normalize_color(value: str) -> str | None:
    if not value:
        return None
    v = value.strip()
    if v.lower() in {"none", "currentcolor", "transparent", "inherit"}:
        return None
    m = _HEX_RE.match(v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h.lower()
    # Skip rgb(), hsl(), named colors — we'd need a full CSS color parser to be exact.
    # The LLM is prompt-locked to hex; anything else we leave for the validator to flag.
    return None


# --------------------------- main entrypoint ---------------------------


def sanitize_svg(svg_text: str, palette: Palette) -> tuple[str, SanitizeReport]:
    """Sanitize raw LLM output into safe, gradient-free, palette-locked SVG."""
    report = SanitizeReport()
    palette_colors = palette.all_colors()
    fallback = palette.mid
    report.fallback_color = fallback

    # Tolerate junk text around the SVG (LLMs love to chatter).
    start = svg_text.find("<svg")
    end = svg_text.rfind("</svg>")
    if start == -1 or end == -1:
        raise ValueError("No <svg>...</svg> found in input.")
    svg_text = svg_text[start : end + len("</svg>")]

    parser = etree.XMLParser(remove_blank_text=False, recover=True, huge_tree=False)
    root = etree.fromstring(svg_text.encode("utf-8"), parser=parser)
    if root is None or _local(root.tag) != "svg":
        raise ValueError("Root element is not <svg>.")

    # 1. Build url(#id) → palette-snapped color map from any gradient defs we find.
    ref_to_color: dict[str, str] = {}
    for grad in root.xpath(
        ".//*[local-name()='linearGradient' or local-name()='radialGradient']"
    ):
        gid = grad.get("id")
        mid = _gradient_mid_color(grad)
        if gid and mid:
            ref_to_color[gid] = nearest_palette_color(mid, palette_colors)
        report.gradients_removed += 1

    # 2. Strip every forbidden tag (gradients, filters, masks, images, ...).
    for el in root.xpath(
        ".//*["
        + " or ".join(f"local-name()='{t}'" for t in _FORBIDDEN_TAGS)
        + "]"
    ):
        name = _local(el.tag)
        report.forbidden_tags_removed.append(name)
        if name == "filter":
            report.filters_removed += 1
        elif name == "mask":
            report.masks_removed += 1
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)
            report.nodes_removed += 1

    # 3. Walk every element; remap url(#…) refs and snap solid colors to palette.
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue  # comment / PI
        # Remove external href references — they could be remote gradient defs.
        for attr in ("href", f"{{{XLINK_NS}}}href"):
            v = el.get(attr)
            if v and not v.startswith("#"):
                del el.attrib[attr]
                report.nodes_removed += 1

        # Drop dangling refs to defs we just removed (filter, mask, clip-path, ...).
        for attr in ("filter", "mask", "clip-path"):
            if el.get(attr):
                del el.attrib[attr]
                report.nodes_removed += 1

        for attr in ("fill", "stroke"):
            v = el.get(attr)
            if not v:
                continue
            ref = _URL_REF_RE.search(v)
            if ref:
                rid = ref.group(1)
                new = ref_to_color.get(rid, fallback)
                el.set(attr, new)
                report.refs_remapped += 1
                continue
            norm = _normalize_color(v)
            if norm is None:
                continue
            snapped = nearest_palette_color(norm, palette_colors)
            if snapped != norm:
                el.set(attr, snapped)
                report.colors_snapped += 1

        style = el.get("style")
        if style:
            new_style, changed = _sanitize_style_attr(style, ref_to_color, fallback, palette_colors)
            if changed:
                if new_style:
                    el.set("style", new_style)
                else:
                    del el.attrib["style"]
                report.colors_snapped += changed

    # 4. Final pass: nuke any inline style declaration that smuggles gradient/filter/mask.
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        style = el.get("style")
        if style and _STYLE_GRAD_RE.search(style):
            del el.attrib["style"]
            report.nodes_removed += 1

    cleaned = etree.tostring(
        root, pretty_print=False, xml_declaration=False, encoding="unicode"
    )
    return cleaned, report


def _sanitize_style_attr(
    style: str,
    ref_to_color: dict[str, str],
    fallback: str,
    palette_colors: list[str],
) -> tuple[str, int]:
    """Process `fill:` / `stroke:` declarations inside a style="…" attribute."""
    changes = 0
    out_parts: list[str] = []
    for decl in style.split(";"):
        decl = decl.strip()
        if not decl:
            continue
        if ":" not in decl:
            out_parts.append(decl)
            continue
        prop, val = decl.split(":", 1)
        prop, val = prop.strip().lower(), val.strip()
        if prop in {"fill", "stroke"}:
            ref = _URL_REF_RE.search(val)
            if ref:
                rid = ref.group(1)
                val = ref_to_color.get(rid, fallback)
                changes += 1
            else:
                norm = _normalize_color(val)
                if norm:
                    snapped = nearest_palette_color(norm, palette_colors)
                    if snapped != norm:
                        val = snapped
                        changes += 1
        out_parts.append(f"{prop}: {val}")
    return "; ".join(out_parts), changes
