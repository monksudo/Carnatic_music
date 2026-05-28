"""Local dev server that mirrors the GitHub Pages layout.

Why: the Pages workflow assembles the site by copying:
    studio/studio/web/*      → _site/
    studio/studio/library/*  → _site/library/
So `library/index.json` ends up a sibling of `verify.html`. The same trick is
needed locally — otherwise fetch("library/index.json") from verify.html 404s.

Run:
    python -m studio.web.dev_serve          # binds 127.0.0.1:8000
    python -m studio.web.dev_serve --port 9000
Open:
    http://127.0.0.1:8000/                  (gallery)
    http://127.0.0.1:8000/verify.html
    http://127.0.0.1:8000/generator.html
"""

from __future__ import annotations

import argparse
import http.server
import shutil
import socketserver
import sys
import tempfile
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent
LIB_DIR = WEB_DIR.parent / "library"


def build_site(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    # Copy every web asset (HTML, CSS, JS modules).
    for item in WEB_DIR.iterdir():
        if item.name == "dev_serve.py":
            continue
        dest = out / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
    # Copy the library so library/index.json + library/svg/*.svg sit next to the HTMLs.
    if LIB_DIR.exists():
        dest_lib = out / "library"
        dest_lib.mkdir(exist_ok=True)
        if (LIB_DIR / "index.json").exists():
            shutil.copy2(LIB_DIR / "index.json", dest_lib / "index.json")
        svg_src = LIB_DIR / "svg"
        if svg_src.exists():
            shutil.copytree(svg_src, dest_lib / "svg", dirs_exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="studio-site-") as tmp:
        site = Path(tmp)
        build_site(site)
        print(f"built site at {site}")
        if args.build_only:
            return 0

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(site), **kw)

            def log_message(self, fmt, *a):  # quieter logs
                sys.stderr.write(f"  {self.address_string()} {fmt % a}\n")

        with socketserver.TCPServer((args.host, args.port), Handler) as httpd:
            httpd.allow_reuse_address = True
            url = f"http://{args.host}:{args.port}/"
            print(f"serving on {url}")
            print(f"  → gallery:   {url}")
            print(f"  → verify:    {url}verify.html")
            print(f"  → generator: {url}generator.html")
            print("Ctrl-C to stop.")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nbye")
    return 0


if __name__ == "__main__":
    sys.exit(main())
