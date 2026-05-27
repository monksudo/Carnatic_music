"""Structured generation inputs beyond a free-form description.

The user can pass these to constrain the model so prompts are not the only
control surface. The Generator turns these into both:
  (a) extra rules appended to the system prompt
  (b) machine-checkable expectations the validator can enforce
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

StyleMode = Literal["flat", "layered_3d"]
ProjectionMode = Literal["front", "isometric", "top", "3q"]


# Common aspect-ratio presets → viewBox dimensions.
_AR_PRESETS: dict[str, tuple[int, int]] = {
    "1:1": (512, 512),
    "square": (512, 512),
    "16:9": (960, 540),
    "9:16": (540, 960),
    "4:3": (640, 480),
    "3:4": (480, 640),
    "21:9": (1050, 450),
    "icon": (64, 64),
}


def _parse_aspect_ratio(ar: str) -> tuple[int, int]:
    ar = ar.strip().lower()
    if ar in _AR_PRESETS:
        return _AR_PRESETS[ar]
    m = re.fullmatch(r"(\d+)\s*[:x/]\s*(\d+)", ar)
    if not m:
        raise ValueError(f"Bad aspect_ratio {ar!r}; try '1:1', '16:9', '4:3', etc.")
    w, h = int(m.group(1)), int(m.group(2))
    # scale to ~512 on the longer edge
    longest = max(w, h)
    scale = 512 / longest
    return (max(1, round(w * scale)), max(1, round(h * scale)))


@dataclass
class GenerationOptions:
    """Structured controls on top of the free-form description.

    All fields are optional; sensible defaults are chosen per generator type.
    """

    # ----- canvas -----
    aspect_ratio: str | None = None  # "1:1", "16:9", or "WxH"
    width: int | None = None  # explicit override of viewBox width
    height: int | None = None  # explicit override of viewBox height

    # ----- depth & style -----
    style_mode: StyleMode = "layered_3d"
    layering: int = 4  # 1=mostly flat, 6=many stacked depth slices
    projection: ProjectionMode | None = None  # for layered_3d

    # ----- composition -----
    components: list[str] = field(default_factory=list)
    # e.g. ["server", "database", "user", "api-gateway"] — each must appear as a
    # data-role group in the output.

    shapes: list[str] = field(default_factory=list)
    # preferred shape vocabulary, e.g. ["polygon", "rect", "ellipse", "path"]

    combinations: str = ""
    # short free-form hint about how components combine, e.g.
    # "user on the left, two services in the middle, db on the right".

    grouping: bool = True  # wrap each component in a <g data-role="component:X">

    # ----- color -----
    color_overrides: dict[str, str] = field(default_factory=dict)
    # override individual palette stops, e.g. {"accent_a": "#ff0066"}.

    # ----- misc -----
    temperature: float = 0.4
    seed: int | None = None

    def viewbox(self, default_w: int = 512, default_h: int = 512) -> tuple[int, int]:
        if self.width and self.height:
            return (self.width, self.height)
        if self.aspect_ratio:
            return _parse_aspect_ratio(self.aspect_ratio)
        return (default_w, default_h)

    def min_layers(self, generator_default: int) -> int:
        if self.style_mode == "flat":
            return max(1, min(generator_default, 1))
        return max(generator_default, max(1, min(self.layering, 6)))

    def to_prompt_block(self) -> str:
        """Render the options as additional instructions the LLM can follow."""
        w, h = self.viewbox()
        lines: list[str] = [
            "## Caller constraints",
            f"- viewBox: `0 0 {w} {h}`",
            f"- style_mode: `{self.style_mode}`"
            + (
                "  (use 1 flat fill per object — no stacked depth slices)"
                if self.style_mode == "flat"
                else "  (papercraft layered 3D, still no gradients)"
            ),
            f"- layering: {self.layering}  "
            + (
                "(target this many distinct `data-layer` values across the scene)"
            ),
        ]
        if self.projection:
            lines.append(f"- projection: `{self.projection}`")
        if self.components:
            lines.append(
                "- required components (each must appear with `data-role` "
                "matching its name):\n  - " + "\n  - ".join(self.components)
            )
        if self.shapes:
            lines.append("- prefer these SVG elements: " + ", ".join(self.shapes))
        if self.combinations:
            lines.append(f"- composition: {self.combinations}")
        if self.grouping:
            lines.append(
                "- grouping: wrap each component's shapes in a "
                "`<g data-role=\"component:<name>\">…</g>` group."
            )
        if self.color_overrides:
            ov = ", ".join(f"{k}={v}" for k, v in self.color_overrides.items())
            lines.append(f"- color overrides: {ov}")
        return "\n".join(lines)

    def apply_color_overrides(self, palette_dict: dict[str, str]) -> dict[str, str]:
        out = dict(palette_dict)
        for k, v in self.color_overrides.items():
            if k in out:
                out[k] = v
        return out
