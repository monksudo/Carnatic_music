"""Structural / semantic validation of sanitized SVG.

A sanitized SVG must:
  - parse as a single <svg> root with a viewBox
  - contain ZERO forbidden tags (gradient/filter/mask/image/foreignObject/pattern)
  - have NO `url(#...)` references in fill/stroke or style attributes
  - have at least one element carrying `data-role="..."`
  - have at least 3 distinct `data-layer` values (to qualify as "3D layered")
  - have no inline `style="..."` containing the words gradient/filter/mask
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lxml import etree

_FORBIDDEN = {
    "linearGradient",
    "radialGradient",
    "filter",
    "mask",
    "image",
    "foreignObject",
    "pattern",
}
_URL_REF_RE = re.compile(r"url\(\s*#")
_BAD_STYLE_RE = re.compile(r"\b(gradient|filter|mask)\b", re.IGNORECASE)


@dataclass
class ValidationError:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def validate_svg(svg_text: str, *, min_layers: int = 3, require_role: bool = True) -> list[ValidationError]:
    """Return a list of errors. Empty list ⇒ valid."""
    errors: list[ValidationError] = []
    try:
        root = etree.fromstring(svg_text.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        return [ValidationError("PARSE", f"SVG is not well-formed: {e}")]

    if _local(root.tag) != "svg":
        errors.append(ValidationError("ROOT", "Root element is not <svg>."))
        return errors

    if not root.get("viewBox"):
        errors.append(ValidationError("VIEWBOX", "Missing required `viewBox` attribute on root."))

    forbidden_seen: dict[str, int] = {}
    layer_values: set[str] = set()
    role_count = 0
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        name = _local(el.tag)
        if name in _FORBIDDEN:
            forbidden_seen[name] = forbidden_seen.get(name, 0) + 1

        for attr in ("fill", "stroke"):
            v = el.get(attr) or ""
            if _URL_REF_RE.search(v):
                errors.append(
                    ValidationError(
                        "URL_REF",
                        f"<{name}> still has {attr}=\"{v}\" referencing a removed def.",
                    )
                )

        style = el.get("style") or ""
        if style and (_URL_REF_RE.search(style) or _BAD_STYLE_RE.search(style)):
            errors.append(
                ValidationError(
                    "STYLE_LEAK",
                    f"<{name}> has style=\"{style}\" referencing gradient/filter/mask.",
                )
            )

        lv = el.get("data-layer")
        if lv is not None:
            layer_values.add(lv.strip())
        if el.get("data-role"):
            role_count += 1

    for tag, n in forbidden_seen.items():
        errors.append(ValidationError("FORBIDDEN_TAG", f"{n}× <{tag}> still present."))

    if require_role and role_count == 0:
        errors.append(
            ValidationError(
                "NO_ROLES",
                "No element carries `data-role`. The output is unaddressable for recolor/replace.",
            )
        )

    if len(layer_values) < min_layers:
        errors.append(
            ValidationError(
                "FEW_LAYERS",
                f"Only {len(layer_values)} distinct data-layer values (need ≥{min_layers}).",
            )
        )

    return errors
