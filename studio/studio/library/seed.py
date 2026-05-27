"""Seed the library with hand-authored exemplar SVGs.

Idempotent: running it again won't duplicate entries that already exist by slug.
Run with:  python -m studio.library.seed
"""

from __future__ import annotations

from dataclasses import dataclass

from studio.library.store import Library
from studio.style.palettes import get_palette
from studio.style.sanitizer import sanitize_svg
from studio.style.validator import validate_svg


@dataclass
class Seed:
    slug: str
    type: str
    title: str
    description: str
    palette: str
    tags: list[str]
    svg: str


SEEDS: list[Seed] = [
    Seed(
        slug="papercraft-cloud",
        type="icon",
        title="Papercraft cloud",
        description="A friendly cloud icon using stacked palette layers for depth.",
        palette="dusk",
        tags=["type:icon", "palette:dusk", "domain:cloud", "style:papercraft"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <path d="M14 44 Q14 30 26 30 Q28 22 38 22 Q50 22 50 32 Q58 32 58 42 Q58 50 50 50 L20 50 Q14 50 14 44 Z" fill="#161d3a" data-layer="0" data-role="cloud-shadow"/>
  <path d="M14 42 Q14 28 26 28 Q28 20 38 20 Q50 20 50 30 Q58 30 58 40 Q58 48 50 48 L20 48 Q14 48 14 42 Z" fill="#2c3a6b" data-layer="1" data-role="cloud-base"/>
  <path d="M16 40 Q16 28 26 28 Q28 21 37 21 Q48 21 48 30 Q55 30 55 38 Q55 45 48 45 L22 45 Q16 45 16 40 Z" fill="#5d7bc7" data-layer="2" data-role="cloud-mid"/>
  <path d="M20 36 Q20 28 27 28 Q29 23 36 23 Q44 23 44 30 Q49 30 49 35 Q49 39 44 39 L26 39 Q20 39 20 36 Z" fill="#a8c0ee" data-layer="3" data-role="cloud-light"/>
  <ellipse cx="32" cy="31" rx="6" ry="2" fill="#e8f0ff" data-layer="4" data-role="cloud-highlight"/>
</svg>""",
    ),
    Seed(
        slug="papercraft-server-rack",
        type="icon",
        title="Server rack",
        description="Vertical server rack with status LEDs, layered papercraft style.",
        palette="dusk",
        tags=["type:icon", "palette:dusk", "domain:infra", "style:papercraft"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="14" y="50" width="36" height="6" fill="#161d3a" data-layer="0" data-role="rack-shadow"/>
  <rect x="14" y="10" width="36" height="42" fill="#2c3a6b" data-layer="1" data-role="rack-body"/>
  <rect x="16" y="12" width="32" height="38" fill="#5d7bc7" data-layer="2" data-role="rack-front"/>
  <rect x="18" y="14" width="28" height="6" fill="#a8c0ee" data-layer="3" data-role="rack-slot-1"/>
  <rect x="18" y="22" width="28" height="6" fill="#a8c0ee" data-layer="3" data-role="rack-slot-2"/>
  <rect x="18" y="30" width="28" height="6" fill="#a8c0ee" data-layer="3" data-role="rack-slot-3"/>
  <rect x="18" y="38" width="28" height="6" fill="#a8c0ee" data-layer="3" data-role="rack-slot-4"/>
  <circle cx="44" cy="17" r="1.5" fill="#22d3ee" data-layer="4" data-role="led-1"/>
  <circle cx="44" cy="25" r="1.5" fill="#22d3ee" data-layer="4" data-role="led-2"/>
  <circle cx="44" cy="33" r="1.5" fill="#f5a623" data-layer="4" data-role="led-3"/>
  <circle cx="44" cy="41" r="1.5" fill="#22d3ee" data-layer="4" data-role="led-4"/>
</svg>""",
    ),
    Seed(
        slug="papercraft-lock",
        type="icon",
        title="Padlock",
        description="Locked padlock — papercraft style, suitable for security UI.",
        palette="dusk",
        tags=["type:icon", "palette:dusk", "domain:security", "style:papercraft"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="16" y="50" width="32" height="4" fill="#161d3a" data-layer="0" data-role="lock-shadow"/>
  <path d="M22 22 Q22 12 32 12 Q42 12 42 22 L42 30 L38 30 L38 22 Q38 16 32 16 Q26 16 26 22 L26 30 L22 30 Z" fill="#2c3a6b" data-layer="1" data-role="shackle-base"/>
  <path d="M24 22 Q24 14 32 14 Q40 14 40 22 L40 28 L36 28 L36 22 Q36 18 32 18 Q28 18 28 22 L28 28 L24 28 Z" fill="#5d7bc7" data-layer="2" data-role="shackle-front"/>
  <rect x="14" y="30" width="36" height="22" rx="2" fill="#2c3a6b" data-layer="1" data-role="body-base"/>
  <rect x="16" y="32" width="32" height="18" rx="1.5" fill="#5d7bc7" data-layer="2" data-role="body-front"/>
  <rect x="18" y="34" width="28" height="3" fill="#a8c0ee" data-layer="3" data-role="body-light"/>
  <circle cx="32" cy="40" r="3" fill="#161d3a" data-layer="3" data-role="keyhole"/>
  <rect x="31" y="40" width="2" height="6" fill="#161d3a" data-layer="3" data-role="keyhole-stem"/>
</svg>""",
    ),
    Seed(
        slug="isometric-storage-cube",
        type="clipart_3d_layered",
        title="Isometric storage cube",
        description="A chunky isometric cube with three visible faces and ground shadow.",
        palette="dusk",
        tags=["type:clipart_3d_layered", "palette:dusk", "style:isometric", "style:papercraft"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <ellipse cx="100" cy="170" rx="60" ry="10" fill="#161d3a" data-layer="0" data-role="ground-shadow"/>
  <polygon points="100,60 160,90 160,150 100,180 40,150 40,90" fill="#161d3a" data-layer="1" data-role="cube-shadow-edge"/>
  <polygon points="100,60 160,90 100,120 40,90" fill="#a8c0ee" data-layer="4" data-role="cube-top"/>
  <polygon points="100,120 160,90 160,150 100,180" fill="#2c3a6b" data-layer="2" data-role="cube-right"/>
  <polygon points="100,120 40,90 40,150 100,180" fill="#5d7bc7" data-layer="3" data-role="cube-front"/>
  <polygon points="100,60 130,75 100,90 70,75" fill="#e8f0ff" data-layer="5" data-role="cube-highlight"/>
  <rect x="60" y="135" width="80" height="6" fill="#2c3a6b" data-layer="3" data-role="cube-band"/>
  <circle cx="130" cy="138" r="2" fill="#22d3ee" data-layer="5" data-role="status-led"/>
</svg>""",
    ),
    Seed(
        slug="isometric-folder",
        type="clipart_3d_layered",
        title="Isometric folder",
        description="A friendly isometric folder with a tab and paper edges peeking out.",
        palette="dusk",
        tags=["type:clipart_3d_layered", "palette:dusk", "style:isometric", "domain:files"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <ellipse cx="100" cy="170" rx="65" ry="10" fill="#161d3a" data-layer="0" data-role="ground-shadow"/>
  <polygon points="40,90 80,70 130,70 140,80 160,80 160,160 40,160" fill="#2c3a6b" data-layer="1" data-role="folder-back"/>
  <polygon points="40,100 160,100 160,170 40,170" fill="#5d7bc7" data-layer="2" data-role="folder-body"/>
  <polygon points="40,100 60,90 180,90 160,100" fill="#a8c0ee" data-layer="3" data-role="folder-top"/>
  <rect x="60" y="115" width="80" height="3" fill="#e8f0ff" data-layer="4" data-role="folder-paper-edge"/>
  <rect x="60" y="123" width="80" height="3" fill="#e8f0ff" data-layer="4" data-role="folder-paper-edge-2"/>
  <polygon points="80,70 130,70 130,80 80,80" fill="#161d3a" data-layer="1" data-role="folder-tab-shadow"/>
  <circle cx="148" cy="145" r="4" fill="#f5a623" data-layer="5" data-role="folder-badge"/>
</svg>""",
    ),
    Seed(
        slug="isometric-database",
        type="clipart_3d_layered",
        title="Isometric database",
        description="Classic cylinder database with stacked rings.",
        palette="dusk",
        tags=["type:clipart_3d_layered", "palette:dusk", "style:isometric", "domain:database"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
  <ellipse cx="100" cy="178" rx="60" ry="8" fill="#161d3a" data-layer="0" data-role="ground-shadow"/>
  <ellipse cx="100" cy="160" rx="50" ry="14" fill="#161d3a" data-layer="1" data-role="db-bottom-shadow"/>
  <rect x="50" y="80" width="100" height="80" fill="#5d7bc7" data-layer="3" data-role="db-side-front"/>
  <ellipse cx="100" cy="160" rx="50" ry="14" fill="#2c3a6b" data-layer="3" data-role="db-bottom"/>
  <ellipse cx="100" cy="80" rx="50" ry="14" fill="#a8c0ee" data-layer="4" data-role="db-top"/>
  <ellipse cx="100" cy="80" rx="35" ry="9" fill="#e8f0ff" data-layer="5" data-role="db-top-highlight"/>
  <rect x="50" y="105" width="100" height="2" fill="#2c3a6b" data-layer="3" data-role="db-ring-1"/>
  <rect x="50" y="130" width="100" height="2" fill="#2c3a6b" data-layer="3" data-role="db-ring-2"/>
</svg>""",
    ),
    Seed(
        slug="arch-user-api-db",
        type="arch_diagram",
        title="User → API → Database",
        description="A canonical three-component architecture diagram, slide-ready.",
        palette="dusk",
        tags=["type:arch_diagram", "palette:dusk", "domain:architecture", "style:papercraft"],
        svg="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
  <rect x="0" y="0" width="960" height="540" fill="#0e1117" data-layer="0" data-role="background"/>
  <ellipse cx="160" cy="270" rx="42" ry="8" fill="#161d3a" data-layer="0" data-role="user-shadow"/>
  <circle cx="160" cy="240" r="22" fill="#2c3a6b" data-layer="1" data-role="user-base"/>
  <circle cx="160" cy="240" r="20" fill="#5d7bc7" data-layer="2" data-role="user-front"/>
  <circle cx="156" cy="236" r="6" fill="#a8c0ee" data-layer="3" data-role="user-highlight"/>
  <text x="160" y="290" text-anchor="middle" fill="#e8f0ff" font-size="14" data-layer="4" data-role="user-label">User</text>
  <ellipse cx="480" cy="290" rx="80" ry="10" fill="#161d3a" data-layer="0" data-role="api-shadow"/>
  <rect x="400" y="210" width="160" height="80" fill="#2c3a6b" data-layer="1" data-role="api-base"/>
  <rect x="405" y="215" width="150" height="70" fill="#5d7bc7" data-layer="2" data-role="api-front"/>
  <rect x="410" y="220" width="140" height="14" fill="#a8c0ee" data-layer="3" data-role="api-top"/>
  <circle cx="540" cy="227" r="3" fill="#22d3ee" data-layer="4" data-role="api-led"/>
  <text x="480" y="310" text-anchor="middle" fill="#e8f0ff" font-size="14" data-layer="4" data-role="api-label">API Gateway</text>
  <ellipse cx="820" cy="290" rx="60" ry="8" fill="#161d3a" data-layer="0" data-role="db-shadow"/>
  <rect x="770" y="210" width="100" height="80" fill="#2c3a6b" data-layer="1" data-role="db-side"/>
  <ellipse cx="820" cy="210" rx="50" ry="12" fill="#a8c0ee" data-layer="3" data-role="db-top"/>
  <ellipse cx="820" cy="290" rx="50" ry="12" fill="#2c3a6b" data-layer="2" data-role="db-bottom"/>
  <rect x="770" y="230" width="100" height="2" fill="#2c3a6b" data-layer="3" data-role="db-ring-1"/>
  <rect x="770" y="255" width="100" height="2" fill="#2c3a6b" data-layer="3" data-role="db-ring-2"/>
  <text x="820" y="320" text-anchor="middle" fill="#e8f0ff" font-size="14" data-layer="4" data-role="db-label">Database</text>
  <line x1="190" y1="240" x2="400" y2="240" stroke="#a8c0ee" stroke-width="2" data-layer="4" data-role="conn-user-api"/>
  <polygon points="400,240 392,236 392,244" fill="#a8c0ee" data-layer="4" data-role="arrow-user-api"/>
  <line x1="560" y1="240" x2="770" y2="240" stroke="#a8c0ee" stroke-width="2" data-layer="4" data-role="conn-api-db"/>
  <polygon points="770,240 762,236 762,244" fill="#a8c0ee" data-layer="4" data-role="arrow-api-db"/>
</svg>""",
    ),
]


def seed_library(force: bool = False) -> int:
    lib = Library()
    added = 0
    for s in SEEDS:
        if lib.exists(s.slug) and not force:
            continue
        # Sanitize each seed through the same pipeline as a real generation,
        # so the on-disk library is guaranteed gradient-free.
        pal = get_palette(s.palette)
        cleaned, _ = sanitize_svg(s.svg, pal)
        errors = validate_svg(cleaned, min_layers=3)
        if errors:
            raise RuntimeError(f"seed {s.slug} fails validation: {errors}")
        if lib.exists(s.slug):
            lib.delete(s.slug)
        lib.add_raw(
            cleaned,
            type_name=s.type,
            title=s.title,
            description=s.description,
            palette=s.palette,
            model="seed",
            prompt="seed/exemplar",
            tags=s.tags,
            slug_hint=s.slug,
        )
        added += 1
    return added


if __name__ == "__main__":  # pragma: no cover
    n = seed_library()
    print(f"Seeded {n} assets.")
