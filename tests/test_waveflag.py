"""Golden test: flags/waveflag.py against the C waveflag it ports.

Needs the C build (`make flags/waveflag`) and the fetched region-flags art
(`steamer fetch waveflag`); skipped otherwise. Uses flags/out/ when `make
flags` has filled it, else waves the flag on the spot.
"""

import io
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from flags import waveflag as wf
from steamer.emoji import ROOT, entries
from steamer.fetch import flag_key

C_BIN = ROOT / "flags" / "waveflag"
SRC = ROOT / "sources" / "cache" / "worktrees" / "waveflag" / "third_party" / "region-flags"
OUT = ROOT / "flags" / "out"

# Mean absolute RGB difference over white, 0–1. The full variant reproduces
# the C blend modes; the font variant swaps soft-light for plain alpha.
FULL_LIMIT = 0.025
FONT_LIMIT = 0.035

pytestmark = pytest.mark.skipif(
    not (C_BIN.exists() and SRC.exists()), reason="needs flags/waveflag and fetched region-flags"
)


def emoji_flag_codes() -> list[str]:
    keys = {e.key for e in entries() if e.subgroup in ("country-flag", "subdivision-flag")}
    codes = [p.stem for p in sorted((SRC / "svg").glob("*.svg"))] if SRC.exists() else []
    return [c for c in codes if flag_key(c) in keys]


def diff(a: Image.Image, b: Image.Image) -> float:
    bg = Image.new("RGBA", a.size, "white")
    a = Image.alpha_composite(bg, a.convert("RGBA")).convert("RGB")
    b = Image.alpha_composite(bg, b.convert("RGBA")).convert("RGB")
    hist = ImageChops.difference(a, b).histogram()
    total = sum(i * n for band in range(3) for i, n in enumerate(hist[band * 256 : (band + 1) * 256]))
    return total / (a.width * a.height * 3 * 255)


def c_render(code: str, tmp: Path) -> Image.Image:
    src = tmp / f"{code}.png"
    src.write_bytes((SRC / "png" / f"{code}.png").read_bytes())
    subprocess.run([str(C_BIN), "ref_", src.name], cwd=tmp, check=True)
    return Image.open(tmp / f"ref_{code}.png")


def py_render(code: str) -> tuple[Image.Image, Image.Image]:
    key = flag_key(code)
    full_p, font_p = OUT / "full" / f"emoji_u{key}.svg", OUT / "svg" / f"emoji_u{key}.svg"
    if full_p.exists() and font_p.exists():
        full, font = full_p.read_text(), font_p.read_text()
    else:
        full, font = wf.wave_flag((SRC / "svg" / f"{code}.svg").read_text())
    return tuple(Image.open(io.BytesIO(wf.render(s, 128))) for s in (full, font))


@pytest.mark.parametrize("code", emoji_flag_codes())
def test_matches_c_waveflag(code, tmp_path):
    ref = c_render(code, tmp_path)
    full, font = py_render(code)
    assert ref.size == full.size == (128, 128)
    d_full, d_font = diff(ref, full), diff(ref, font)
    assert d_full < FULL_LIMIT, f"{code}: full variant differs by {d_full:.4f}"
    assert d_font < FONT_LIMIT, f"{code}: font variant differs by {d_font:.4f}"
