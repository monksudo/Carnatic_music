"""Curated layer ramps: 5 solid colors that read as depth without using any gradient.

Each palette has the same five named stops so generators and the sanitizer can
remap between them deterministically. Stops, light → dark:

    highlight  — top-most catch-light face
    light      — upward-facing face
    mid        — primary body color
    base       — downward-facing face
    shadow     — cast / contact shadow

Accents (`accent_a`, `accent_b`) are optional callouts used for status, glyphs
and contrast pops. They are never used as a fill ramp.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Palette:
    id: str
    name: str
    description: str
    highlight: str
    light: str
    mid: str
    base: str
    shadow: str
    accent_a: str
    accent_b: str
    background: str
    ink: str  # for thin outlines / type

    def ramp(self) -> list[str]:
        """Solid color ramp, light → dark (5 stops)."""
        return [self.highlight, self.light, self.mid, self.base, self.shadow]

    def all_colors(self) -> list[str]:
        """Every color in the palette, useful for nearest-color flattening."""
        return self.ramp() + [self.accent_a, self.accent_b, self.background, self.ink]

    def as_dict(self) -> dict[str, str]:
        return asdict(self)  # type: ignore[arg-type]


PALETTES: dict[str, Palette] = {
    p.id: p
    for p in [
        Palette(
            id="dusk",
            name="Dusk",
            description="Cool indigo/teal sky; high contrast, modern UI feel.",
            highlight="#e8f0ff",
            light="#a8c0ee",
            mid="#5d7bc7",
            base="#2c3a6b",
            shadow="#161d3a",
            accent_a="#f5a623",
            accent_b="#22d3ee",
            background="#0e1117",
            ink="#0b0f1a",
        ),
        Palette(
            id="forest",
            name="Forest",
            description="Sage / pine layered greens for nature & sustainability viz.",
            highlight="#ecfccb",
            light="#a3e635",
            mid="#4d7c0f",
            base="#1f3a1f",
            shadow="#0c1f0c",
            accent_a="#fbbf24",
            accent_b="#22d3ee",
            background="#f6faf2",
            ink="#0a1408",
        ),
        Palette(
            id="terracotta",
            name="Terracotta",
            description="Warm earth-tone clay & terracotta for friendly clip art.",
            highlight="#fff1e6",
            light="#fbb88a",
            mid="#d97757",
            base="#7c3a1f",
            shadow="#3a1b0c",
            accent_a="#0ea5e9",
            accent_b="#facc15",
            background="#fdf6ef",
            ink="#2a1409",
        ),
        Palette(
            id="cobalt",
            name="Cobalt",
            description="Electric blue/violet with neon accents — tech & AI diagrams.",
            highlight="#dbeafe",
            light="#60a5fa",
            mid="#2563eb",
            base="#1e1b4b",
            shadow="#0b0a24",
            accent_a="#f472b6",
            accent_b="#34d399",
            background="#0a0e1f",
            ink="#04060d",
        ),
        Palette(
            id="mono",
            name="Monochrome",
            description="Neutral grayscale layers — works on any background.",
            highlight="#ffffff",
            light="#d4d4d8",
            mid="#71717a",
            base="#27272a",
            shadow="#0a0a0a",
            accent_a="#ef4444",
            accent_b="#22d3ee",
            background="#fafafa",
            ink="#000000",
        ),
        Palette(
            id="candy",
            name="Candy",
            description="Pastel pinks & mints for friendly, playful illustration.",
            highlight="#fff0f6",
            light="#fbcfe8",
            mid="#ec4899",
            base="#831843",
            shadow="#3f0a23",
            accent_a="#a7f3d0",
            accent_b="#fde68a",
            background="#fff7fb",
            ink="#1a0a13",
        ),
        Palette(
            id="slate",
            name="Slate",
            description="Cool blue-gray architectural palette for diagrams.",
            highlight="#f1f5f9",
            light="#cbd5e1",
            mid="#64748b",
            base="#1e293b",
            shadow="#0b1220",
            accent_a="#f59e0b",
            accent_b="#10b981",
            background="#f8fafc",
            ink="#020617",
        ),
    ]
}


def list_palettes() -> list[Palette]:
    return list(PALETTES.values())


def get_palette(name: str) -> Palette:
    if name not in PALETTES:
        raise KeyError(
            f"Unknown palette {name!r}. Available: {', '.join(sorted(PALETTES))}"
        )
    return PALETTES[name]


# ---------- color math: nearest palette swatch in OKLab (ΔE) ----------


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Not a #RRGGBB color: {h!r}")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def nearest_palette_color(target: str, candidates: list[str]) -> str:
    """Return the candidate hex color nearest `target` in OKLab ΔE."""
    if not candidates:
        raise ValueError("candidates is empty")
    t = _rgb_to_oklab(_hex_to_rgb(target))
    best, best_d = candidates[0], float("inf")
    for c in candidates:
        co = _rgb_to_oklab(_hex_to_rgb(c))
        d = (t[0] - co[0]) ** 2 + (t[1] - co[1]) ** 2 + (t[2] - co[2]) ** 2
        if d < best_d:
            best, best_d = c, d
    return best
