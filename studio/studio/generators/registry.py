"""Generator registry — keep new types here as v1 lands them."""

from __future__ import annotations

from studio.generators.arch_diagram import ArchDiagramGenerator
from studio.generators.base import Generator
from studio.generators.clipart_3d_layered import Clipart3DLayeredGenerator
from studio.generators.icon import IconGenerator

REGISTRY: dict[str, type[Generator]] = {
    "icon": IconGenerator,
    "clipart_3d_layered": Clipart3DLayeredGenerator,
    "arch_diagram": ArchDiagramGenerator,
}


def list_types() -> list[str]:
    return sorted(REGISTRY)


def get_generator(type_name: str) -> type[Generator]:
    if type_name not in REGISTRY:
        raise KeyError(
            f"Unknown generator {type_name!r}. Available: {', '.join(list_types())}"
        )
    return REGISTRY[type_name]
