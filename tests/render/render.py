"""Render sample text in each Bahuan build with real browsers and screenshot it.

    python tests/render/render.py build/out build/out/render [--browsers chromium firefox]
    python tests/render/render.py build/out docs --preview   # README image

Chromium covers COLRv1, CBDT and sbix; Firefox adds OpenType-SVG. Screenshots
are for eyes (CI uploads them); it fails if the font doesn't load.
"""

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

SAMPLES = [
    ("blob", "😀 😂 🥰 🤔 😴"),
    ("flat", "🍊 🍎 🥑 ☕ 🍣"),
    ("waved", "🇹🇼 🇯🇵 🇺🇸 🇳🇵 🏴󠁧󠁢󠁷󠁬󠁳󠁿"),
    ("redraw", "❤️ 🧡 🩷 🖤 🟠 ⚫ ⬛ ◾ ✅ ❎ ❓ ‼️ ⁉️ 🟰 🫟 🏴‍☠️ 🏳️‍⚧️ 🧑‍🧒"),
    ("people", "👍🏽 🧑🏿‍🚀 👩‍👩‍👧 🙋‍♂️"),
    ("text", "Dinner tonight? 🍜 Sounds good 👌 see you 🚲💨"),
]

PAGE = """<!doctype html><meta charset="utf-8">
<style>
@font-face {{ font-family: "Bahuan"; src: url("{font}"); }}
body {{ margin: 16px; font: 20px/1.4 sans-serif; background: #fff; color: #222; }}
h1 {{ font: 600 14px sans-serif; margin: 0 0 8px; }}
.row {{ display: flex; gap: 16px; align-items: baseline; }}
.row b {{ width: 70px; font: 12px monospace; color: #666; }}
.e {{ font-family: "Bahuan"; }}
.big {{ font-size: 64px; line-height: 1.1; }}
</style>
<h1>{name} · {browser}</h1>
<div class="big e">😀🍊🇹🇼</div>
{rows}
"""


PREVIEW = """<!doctype html><meta charset="utf-8">
<style>
@font-face {{ font-family: "Bahuan"; src: url("{font}"); }}
body {{ margin: 0; padding: 24px 28px; background: #fbfaf7; font: 44px/1.3 "Bahuan"; letter-spacing: 4px; }}
p {{ margin: 0; }}
</style>
<p>😀😂🥰😴🤔🙃😎😭</p>
<p>👍🏽🙋‍♀️🧑‍🍳🐱🐶🦊🌻🍊</p>
<p>🍜☕🚲🌈⛅🎉💡🇹🇼🇯🇵🇳🇵</p>
"""


def page_for(font: Path, browser: str) -> str:
    rows = "".join(f'<div class="row"><b>{k}</b><span class="e">{v}</span></div>' for k, v in SAMPLES)
    return PAGE.format(font=font.name, name=font.name, browser=browser, rows=rows)


def launch(p, name: str):
    kind = getattr(p, name)
    try:
        return kind.launch()
    except Error:
        # Sandboxed environments ship a fixed Chromium build.
        exe = os.environ.get("CHROMIUM_PATH")
        if name == "chromium" and exe and Path(exe).exists():
            return kind.launch(executable_path=exe)
        raise


def font_loaded(page) -> bool:
    """True when the page really shapes with Bahuan; a broken font rejects."""
    try:
        return page.evaluate(
            "async () => { await document.fonts.load('20px Bahuan'); "
            "return document.fonts.check('20px Bahuan'); }"
        )
    except Error:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("fonts_dir", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--browsers", nargs="+", default=["chromium", "firefox"])
    ap.add_argument("--preview", action="store_true", help="write preview.png from the COLRv1 build")
    a = ap.parse_args(argv)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    if a.preview:
        font = a.fonts_dir / "Bahuan-COLRv1.ttf"
        html = a.fonts_dir / ".preview.html"
        html.write_text(PREVIEW.format(font=font.name), encoding="utf-8")
        with sync_playwright() as p:
            browser = launch(p, "chromium")
            page = browser.new_page(viewport={"width": 640, "height": 220}, device_scale_factor=2)
            page.goto(html.resolve().as_uri())
            if not font_loaded(page):
                sys.exit(f"{font.name}: Bahuan did not load in chromium")
            page.wait_for_timeout(300)
            page.screenshot(path=str(a.out_dir / "preview.png"), full_page=True)
            browser.close()
        html.unlink()
        print(f"wrote {a.out_dir / 'preview.png'}")
        return
    fonts = sorted(p for p in a.fonts_dir.iterdir() if p.suffix in (".ttf", ".otf"))
    if not fonts:
        sys.exit(f"no fonts in {a.fonts_dir}")
    shots = 0
    with sync_playwright() as p:
        for name in a.browsers:
            try:
                browser = launch(p, name)
            except Error as e:
                print(f"skipping {name}: {str(e).splitlines()[0]}")
                continue
            for font in fonts:
                html = a.fonts_dir / f".render-{font.stem}-{name}.html"
                html.write_text(page_for(font, name), encoding="utf-8")
                page = browser.new_page(viewport={"width": 640, "height": 400})
                page.goto(html.resolve().as_uri())
                if not font_loaded(page):
                    sys.exit(f"{font.name}: Bahuan did not load in {name}")
                page.wait_for_timeout(300)
                shot = a.out_dir / f"{font.stem}-{name}.png"
                page.screenshot(path=str(shot), full_page=True)
                page.close()
                html.unlink()
                shots += 1
                print(f"wrote {shot}")
            browser.close()
    if not shots:
        sys.exit(f"no browser could be launched from {a.browsers}")


if __name__ == "__main__":
    main()
