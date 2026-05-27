from __future__ import annotations

import re

from studio.style.palettes import get_palette
from studio.style.recolor import list_roles, recolor

DUSK = get_palette("dusk")
FOREST = get_palette("forest")

SAMPLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <ellipse cx="50" cy="90" rx="30" ry="4" fill="#161d3a" data-layer="0" data-role="shadow"/>
  <rect x="10" y="40" width="80" height="40" fill="#2c3a6b" data-layer="1" data-role="box-base"/>
  <rect x="10" y="40" width="80" height="40" fill="#5d7bc7" data-layer="2" data-role="box-mid"/>
  <rect x="20" y="50" width="60" height="20" fill="#a8c0ee" data-layer="3" data-role="box-light"/>
  <circle cx="50" cy="60" r="5" fill="#e8f0ff" data-layer="4" data-role="dot"/>
</svg>"""


def test_recolor_maps_layers_to_new_palette():
    out, report = recolor(SAMPLE, DUSK, FOREST)
    fills = re.findall(r'fill="([^"]+)"', out)
    forest_colors = {c.lower() for c in FOREST.all_colors()}
    for fill in fills:
        assert fill.lower() in forest_colors, f"non-forest color {fill} after recolor"
    assert report.fills_changed >= 4


def test_list_roles_returns_every_distinct_role():
    roles = list_roles(SAMPLE)
    assert "shadow" in roles
    assert "box-base" in roles
    assert "dot" in roles
    assert len(roles) == 5
