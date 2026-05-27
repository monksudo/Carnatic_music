from studio.generators.base import Generator


class ArchDiagramGenerator(Generator):
    type_name = "arch_diagram"
    prompt_file = "arch_diagram.md"
    min_layers = 4
