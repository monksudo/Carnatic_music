"""End-to-end pipeline test with a fake LLM.

We mock the LLM client to return a known SVG so we exercise the full path:
  Generator.generate → sanitize → validate → GenerationResult,
plus the GenerationOptions injection into the system prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

from studio.core.llm import LLMMessage
from studio.generators import GenerationOptions, get_generator
from studio.style.palettes import get_palette

GOOD_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <ellipse cx="32" cy="56" rx="22" ry="4" fill="#161d3a" data-layer="0" data-role="shadow"/>
  <rect x="14" y="14" width="36" height="36" fill="#2c3a6b" data-layer="1" data-role="body-base"/>
  <rect x="16" y="16" width="32" height="32" fill="#5d7bc7" data-layer="2" data-role="body-front"/>
  <rect x="20" y="20" width="24" height="6" fill="#a8c0ee" data-layer="3" data-role="body-light"/>
  <circle cx="44" cy="23" r="1.5" fill="#22d3ee" data-layer="4" data-role="led"/>
</svg>"""


SVG_WITH_GRADIENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs><linearGradient id="g"><stop offset="0" stop-color="#102040"/><stop offset="1" stop-color="#a0c0ff"/></linearGradient></defs>
  <ellipse cx="32" cy="56" rx="22" ry="4" fill="#161d3a" data-layer="0" data-role="shadow"/>
  <rect x="14" y="14" width="36" height="36" fill="url(#g)" data-layer="1" data-role="body-base"/>
  <rect x="16" y="16" width="32" height="32" fill="#5d7bc7" data-layer="2" data-role="body-front"/>
  <rect x="20" y="20" width="24" height="6" fill="#a8c0ee" data-layer="3" data-role="body-light"/>
</svg>"""


@dataclass
class FakeLLM:
    name: str = "fake"
    model: str = "fake-model"
    response: str = GOOD_ICON
    last_messages: list[LLMMessage] | None = None

    def chat(self, messages, **kwargs):
        self.last_messages = messages
        return self.response

    def health(self) -> bool:
        return True


def test_generator_returns_clean_result():
    llm = FakeLLM()
    gen = get_generator("icon")(llm)
    res = gen.generate("aws lambda", get_palette("dusk"))
    assert res.generator == "icon"
    assert "<svg" in res.svg
    assert "linearGradient" not in res.svg
    assert res.attempts == 1
    assert res.sanitize_report.gradients_removed == 0


def test_generator_sanitizes_gradients_from_model_output():
    llm = FakeLLM(response=SVG_WITH_GRADIENT)
    gen = get_generator("icon")(llm)
    res = gen.generate("aws lambda", get_palette("dusk"))
    assert "linearGradient" not in res.svg
    assert "url(" not in res.svg
    assert res.sanitize_report.gradients_removed >= 1


def test_options_inject_components_into_prompt():
    llm = FakeLLM()
    gen = get_generator("arch_diagram")(llm)
    opts = GenerationOptions(
        aspect_ratio="16:9",
        layering=5,
        components=["user", "api-gateway", "database"],
        combinations="user on the left, db on the right",
        color_overrides={"accent_a": "#ff0066"},
    )
    # Fake response must contain those data-roles so validation passes.
    llm.response = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
      <rect width="960" height="540" fill="#0e1117" data-layer="0" data-role="background"/>
      <circle cx="100" cy="270" r="20" fill="#5d7bc7" data-layer="1" data-role="user"/>
      <rect x="400" y="240" width="160" height="60" fill="#5d7bc7" data-layer="2" data-role="api-gateway"/>
      <rect x="780" y="240" width="120" height="60" fill="#5d7bc7" data-layer="3" data-role="database"/>
      <line x1="120" y1="270" x2="400" y2="270" stroke="#a8c0ee" data-layer="4" data-role="conn-1"/>
    </svg>"""
    res = gen.generate("user, api, db", get_palette("dusk"), opts)
    system = llm.last_messages[0].content
    assert "viewBox: `0 0 960 540`" in system
    assert "layering: 5" in system
    assert "user" in system
    assert "api-gateway" in system
    assert "database" in system
    assert "user on the left" in system
    assert "accent_a=#ff0066" in system
    assert res.options["style_mode"] == "layered_3d"


def test_options_flat_style_relaxes_min_layers():
    llm = FakeLLM(
        response="""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
            <rect width="64" height="64" fill="#5d7bc7" data-layer="0" data-role="body"/>
        </svg>"""
    )
    gen = get_generator("icon")(llm)
    res = gen.generate("flat tile", get_palette("dusk"), GenerationOptions(style_mode="flat", layering=1))
    assert res.svg.count("data-layer") == 1


def test_aspect_ratio_parses_custom():
    opts = GenerationOptions(aspect_ratio="3:2")
    w, h = opts.viewbox()
    # 3:2 normalised so longer side is 512
    assert w == 512 and h == round(512 * 2 / 3)


def test_aspect_ratio_preset_square():
    assert GenerationOptions(aspect_ratio="1:1").viewbox() == (512, 512)
