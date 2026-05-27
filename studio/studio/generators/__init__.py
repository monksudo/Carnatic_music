"""Per-type SVG generators.

MVP ships three:  icon, clipart_3d_layered, arch_diagram.
v1 will add: chart, graph, table, clipart_2d, cloud_diagram, custom_viz.
"""

from studio.generators.base import GenerationResult, Generator, GeneratorError
from studio.generators.options import GenerationOptions
from studio.generators.registry import REGISTRY, get_generator, list_types

__all__ = [
    "REGISTRY",
    "GenerationOptions",
    "GenerationResult",
    "Generator",
    "GeneratorError",
    "get_generator",
    "list_types",
]
