"""Generator base class — prompt + LLM call + sanitize + validate + retry.

Generation is driven by two inputs:
  1. A free-form `user_prompt` (what to draw).
  2. A structured `GenerationOptions` (how to draw: size, aspect, depth, components,
     shapes, combinations, grouping, color overrides).

The Generator merges (2) into the system prompt as machine-style constraints,
calls the LLM, sanitizes (no gradients ever), validates, and retries once on
failure feeding the errors back to the model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from studio.core.llm import LLMClient, LLMError, LLMMessage
from studio.generators.options import GenerationOptions
from studio.style.palettes import Palette
from studio.style.sanitizer import SanitizeReport, sanitize_svg
from studio.style.validator import validate_svg


class GeneratorError(RuntimeError):
    """Raised when generation can't produce a valid SVG even after retry."""


@dataclass
class GenerationResult:
    svg: str
    raw_model_output: str
    sanitize_report: SanitizeReport
    palette_id: str
    generator: str
    prompt: str
    model: str
    seed: int | None
    attempts: int
    options: dict | None = None


def _load_prompt(name: str) -> str:
    """Read a packaged prompt file (e.g. 'icon.md')."""
    pkg = "studio.core.prompts"
    try:
        return resources.files(pkg).joinpath(name).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise GeneratorError(f"Missing prompt template: {name}") from e


def _shared_prompt() -> str:
    return _load_prompt("_shared.md")


class Generator:
    """Single-type SVG generator. Subclasses set `type_name` and `prompt_file`."""

    type_name: str = "base"
    prompt_file: str = ""
    min_layers: int = 3
    require_role: bool = True
    max_attempts: int = 2
    default_viewbox: tuple[int, int] = (512, 512)

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def _system_prompt(self, palette: Palette, opts: GenerationOptions) -> str:
        if not self.prompt_file:
            raise GeneratorError(f"{type(self).__name__} has no prompt_file set")
        body = _shared_prompt() + "\n\n" + _load_prompt(self.prompt_file)

        active_palette = opts.apply_color_overrides(
            {
                "highlight": palette.highlight,
                "light": palette.light,
                "mid": palette.mid,
                "base": palette.base,
                "shadow": palette.shadow,
                "accent_a": palette.accent_a,
                "accent_b": palette.accent_b,
                "background": palette.background,
                "ink": palette.ink,
            }
        )
        body += "\n\n## Active palette (use ONLY these hex codes)\n" + json.dumps(
            active_palette, indent=2
        )

        body += "\n\n" + opts.to_prompt_block()
        return body

    def generate(
        self,
        user_prompt: str,
        palette: Palette,
        options: GenerationOptions | None = None,
    ) -> GenerationResult:
        opts = options or GenerationOptions()
        system = self._system_prompt(palette, opts)
        min_layers = opts.min_layers(self.min_layers)
        last_errors: list[str] = []
        raw: str = ""
        attempt = 0
        for attempt in range(1, self.max_attempts + 1):
            user_msg = user_prompt
            if last_errors:
                user_msg = (
                    f"{user_prompt}\n\n"
                    "Your previous attempt failed validation. Fix these "
                    "issues and try again, returning only the corrected "
                    "<svg>...</svg>:\n- " + "\n- ".join(last_errors)
                )
            try:
                raw = self.llm.chat(
                    [LLMMessage("system", system), LLMMessage("user", user_msg)],
                    temperature=opts.temperature,
                    max_tokens=6000,
                    seed=opts.seed,
                )
            except LLMError as e:
                raise GeneratorError(f"LLM call failed: {e}") from e

            try:
                cleaned, report = sanitize_svg(raw, palette)
            except ValueError as e:
                last_errors = [f"Sanitizer rejected output: {e}"]
                continue

            errors = validate_svg(
                cleaned,
                min_layers=min_layers,
                require_role=self.require_role,
            )

            # Extra component check: every required component must appear as
            # a data-role somewhere (case-insensitive substring match).
            if not errors and opts.components:
                lower = cleaned.lower()
                missing = [
                    c for c in opts.components if 'data-role="' not in lower or c.lower() not in lower
                ]
                if missing:
                    errors = []
                    last_errors = [f"missing component data-role: {m}" for m in missing]
                    continue

            if not errors:
                return GenerationResult(
                    svg=cleaned,
                    raw_model_output=raw,
                    sanitize_report=report,
                    palette_id=palette.id,
                    generator=self.type_name,
                    prompt=user_prompt,
                    model=self.llm.model,
                    seed=opts.seed,
                    attempts=attempt,
                    options=_options_to_dict(opts),
                )
            last_errors = [str(e) for e in errors]

        raise GeneratorError(
            f"Generation failed after {attempt} attempts. Last errors:\n"
            + "\n".join(f"  - {e}" for e in last_errors)
        )


def _options_to_dict(opts: GenerationOptions) -> dict:
    return {
        "aspect_ratio": opts.aspect_ratio,
        "width": opts.width,
        "height": opts.height,
        "style_mode": opts.style_mode,
        "layering": opts.layering,
        "projection": opts.projection,
        "components": opts.components,
        "shapes": opts.shapes,
        "combinations": opts.combinations,
        "grouping": opts.grouping,
        "color_overrides": opts.color_overrides,
        "temperature": opts.temperature,
    }


def save_result(result: GenerationResult, out_path: Path) -> Path:
    """Convenience: write SVG to disk and return the path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.svg, encoding="utf-8")
    return out_path
