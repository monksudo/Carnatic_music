from studio.generators.base import Generator


class IconGenerator(Generator):
    type_name = "icon"
    prompt_file = "icon.md"
    min_layers = 3
