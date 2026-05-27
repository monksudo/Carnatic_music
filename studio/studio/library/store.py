"""JSON-index + filesystem asset library.

MVP shape — committed under `studio/library/`:
    svg/<slug>.svg              raw cleaned SVG
    png/<slug>.png              optional render
    thumbs/<slug>.png           gallery thumbnail
    index.json                  array of asset metadata

A v1 successor will mirror this into SQLite + FTS5 without changing the on-disk
shape; the JSON file stays so GitHub Pages can read it client-side.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from studio.generators.base import GenerationResult


def default_library_dir() -> Path:
    env = os.environ.get("STUDIO_LIBRARY_DIR")
    if env:
        return Path(env).expanduser().resolve()
    # Walk up from CWD looking for a studio/ directory; fall back to a user-home location.
    here = Path.cwd()
    for parent in (here, *here.parents):
        candidate = parent / "studio" / "studio" / "library"
        if candidate.exists():
            return candidate
        candidate2 = parent / "studio" / "library"
        if candidate2.exists():
            return candidate2
    return Path.home() / ".studio" / "library"


def slugify(text: str, *, max_len: int = 48) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:max_len] or "asset"


@dataclass
class Asset:
    slug: str
    type: str
    title: str
    description: str
    palette: str
    model: str
    prompt: str
    tags: list[str] = field(default_factory=list)
    seed: int | None = None
    svg_path: str = ""
    png_path: str = ""
    parent_slug: str | None = None
    sha256: str = ""
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class Library:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_library_dir()).resolve()
        (self.root / "svg").mkdir(parents=True, exist_ok=True)
        (self.root / "png").mkdir(parents=True, exist_ok=True)
        (self.root / "thumbs").mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.json"
        if not self._index_path.exists():
            self._index_path.write_text("[]\n", encoding="utf-8")

    # ---------- index io ----------

    def _read(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self._index_path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            return []

    def _write(self, items: list[dict[str, Any]]) -> None:
        self._index_path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ---------- CRUD ----------

    def all(self) -> list[Asset]:
        return [Asset(**row) for row in self._read()]

    def get(self, slug: str) -> Asset | None:
        for row in self._read():
            if row["slug"] == slug:
                return Asset(**row)
        return None

    def exists(self, slug: str) -> bool:
        return self.get(slug) is not None

    def unique_slug(self, base: str) -> str:
        base = slugify(base) or "asset"
        if not self.exists(base):
            return base
        n = 2
        while self.exists(f"{base}-{n}"):
            n += 1
        return f"{base}-{n}"

    def add_from_result(
        self,
        result: GenerationResult,
        *,
        title: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
        parent_slug: str | None = None,
        slug_hint: str | None = None,
    ) -> Asset:
        title = title or result.prompt[:80]
        slug = self.unique_slug(slug_hint or title)
        sha = hashlib.sha256(result.svg.encode("utf-8")).hexdigest()
        svg_rel = f"svg/{slug}.svg"
        (self.root / svg_rel).write_text(result.svg, encoding="utf-8")

        # Always tag the asset by type & palette; user tags merge in.
        auto_tags = {f"type:{result.generator}", f"palette:{result.palette_id}"}
        all_tags = sorted(auto_tags.union(tags or []))

        asset = Asset(
            slug=slug,
            type=result.generator,
            title=title,
            description=description,
            palette=result.palette_id,
            model=result.model,
            prompt=result.prompt,
            tags=all_tags,
            seed=result.seed,
            svg_path=svg_rel,
            png_path="",
            parent_slug=parent_slug,
            sha256=sha,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        items = self._read()
        items.append(asset.as_dict())
        self._write(items)
        return asset

    def add_raw(
        self,
        svg: str,
        *,
        type_name: str,
        title: str,
        description: str = "",
        palette: str = "dusk",
        model: str = "n/a",
        prompt: str = "",
        tags: list[str] | None = None,
        parent_slug: str | None = None,
        seed: int | None = None,
        slug_hint: str | None = None,
    ) -> Asset:
        slug = self.unique_slug(slug_hint or title)
        sha = hashlib.sha256(svg.encode("utf-8")).hexdigest()
        svg_rel = f"svg/{slug}.svg"
        (self.root / svg_rel).write_text(svg, encoding="utf-8")
        auto_tags = {f"type:{type_name}", f"palette:{palette}"}
        all_tags = sorted(auto_tags.union(tags or []))
        asset = Asset(
            slug=slug,
            type=type_name,
            title=title,
            description=description,
            palette=palette,
            model=model,
            prompt=prompt,
            tags=all_tags,
            seed=seed,
            svg_path=svg_rel,
            png_path="",
            parent_slug=parent_slug,
            sha256=sha,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        items = self._read()
        items.append(asset.as_dict())
        self._write(items)
        return asset

    def read_svg(self, slug: str) -> str:
        a = self.get(slug)
        if not a:
            raise KeyError(slug)
        return (self.root / a.svg_path).read_text(encoding="utf-8")

    def write_png(self, slug: str, png_bytes: bytes) -> Asset:
        items = self._read()
        for row in items:
            if row["slug"] == slug:
                rel = f"png/{slug}.png"
                (self.root / rel).write_bytes(png_bytes)
                row["png_path"] = rel
                self._write(items)
                return Asset(**row)
        raise KeyError(slug)

    def update_tags(self, slug: str, add: list[str] | None = None, remove: list[str] | None = None) -> Asset:
        items = self._read()
        for row in items:
            if row["slug"] == slug:
                tags = set(row.get("tags") or [])
                tags.update(add or [])
                tags.difference_update(remove or [])
                row["tags"] = sorted(tags)
                self._write(items)
                return Asset(**row)
        raise KeyError(slug)

    def delete(self, slug: str) -> None:
        items = self._read()
        new_items = []
        removed = False
        for row in items:
            if row["slug"] == slug:
                for k in ("svg_path", "png_path"):
                    p = row.get(k)
                    if p:
                        try:
                            (self.root / p).unlink(missing_ok=True)
                        except OSError:
                            pass
                removed = True
                continue
            new_items.append(row)
        if not removed:
            raise KeyError(slug)
        self._write(new_items)

    # ---------- search ----------

    def search(
        self,
        query: str = "",
        *,
        type_name: str | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
    ) -> list[Asset]:
        q = query.lower().strip()
        wanted_tags = set(tags or [])
        results: list[Asset] = []
        for row in self._read():
            if type_name and row.get("type") != type_name:
                continue
            row_tags = set(row.get("tags") or [])
            if wanted_tags and not wanted_tags.issubset(row_tags):
                continue
            if q:
                blob = " ".join(
                    [
                        row.get("title") or "",
                        row.get("description") or "",
                        row.get("prompt") or "",
                        " ".join(row.get("tags") or []),
                        row.get("slug") or "",
                    ]
                ).lower()
                if q not in blob:
                    continue
            results.append(Asset(**row))
            if limit and len(results) >= limit:
                break
        return results
