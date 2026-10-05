"""
Post-nanoemoji processing of the Bahuan fonts.

Adapted from noto-emoji's colrv1_postproc.py. Upstream copies names and
vertical metrics from its CBDT build; Bahuan builds every format with
nanoemoji, so each font gets the same treatment directly: names, the emoji
variation-selector cmap, blank tag glyphs for subdivision flags, vertical
metrics, no embedding restrictions and a consistent version.
"""

import argparse
import datetime
import functools
import re
import subprocess
import sys
from pathlib import Path

from fontTools import ttLib
from fontTools.ttLib.tables import _g_l_y_f as glyf
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from steamer.emoji import entries  # noqa: E402

_FAMILY = "Bahuan"
_URL = "https://github.com/rschiang/bahuan"
_COPYRIGHT = "Copyright 2013-2026 Google LLC. Selection copyright 2026 the Bahuan authors."
_DESIGNER = "Google Noto Emoji designers (art); Bahuan authors (selection)"
_LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)
_FORMATS = {
    "COLRv1": "Color emoji font using COLRv1.",
    "CBDT": "Color emoji font using CBDT bitmaps.",
    "sbix": "Color emoji font using sbix bitmaps, for macOS and iOS.",
    "SVG": "Color emoji font using OpenType-SVG.",
}


def _set_name(name_table, nameID, value):
    name_table.setName(value, nameID, 3, 1, 0x409)


def _set_names(font, fmt, version, stamp):
    name_table = font["name"]
    name_table.names = [n for n in name_table.names if n.nameID > 255]
    ps = f"{_FAMILY}-{fmt}"
    for nameID, value in {
        0: _COPYRIGHT,
        1: _FAMILY,
        2: "Regular",
        3: f"{version:.3f};BAHN;{ps}",
        4: _FAMILY,
        5: f"Version {version:.3f};bahuan:{stamp}",
        6: ps,
        9: _DESIGNER,
        10: _FORMATS[fmt],
        11: _URL,
        12: "https://github.com/googlefonts/noto-emoji",
        13: _LICENSE,
        14: "https://openfontlicense.org",
    }.items():
        _set_name(name_table, nameID, value)


def _Cmap(ttfont):
    def _Reducer(acc, u):
        acc.update(u)
        return acc

    unicode_cmaps = (t.cmap for t in ttfont["cmap"].tables if t.isUnicode())
    return functools.reduce(_Reducer, unicode_cmaps, {})


# Upstream: add_vs_cmap from nototools. Here the emoji-presentation pairs come
# straight from the pinned emoji-test.txt.
def _add_vs_cmap(font):
    cmap = _Cmap(font)
    pairs = sorted(
        {e.cps[0] for e in entries() if len(e.cps) >= 2 and e.cps[1] == 0xFE0F and e.cps[0] in cmap}
    )
    font["cmap"].tables = [t for t in font["cmap"].tables if t.format != 14]
    vs = CmapSubtable.newSubtable(14)
    vs.platformID, vs.platEncID, vs.language = 0, 5, 0xFF
    vs.cmap = {}
    vs.uvsDict = {0xFE0F: [(cp, None) for cp in pairs]}
    font["cmap"].tables.append(vs)


FLAG_TAGS = set(range(0xE0030, 0xE0039 + 1)) | set(range(0xE0061, 0xE007A + 1))
CANCEL_TAG = 0xE007F


def _add_cmap_entries(font, codepoint, glyph_name):
    for table in font["cmap"].tables:
        if table.format == 14:
            continue
        if codepoint > 0xFFFF and table.format == 4:
            continue
        table.cmap[codepoint] = glyph_name


def _map_missing_flag_tag_chars_to_empty_glyphs(font):
    # Add all tag characters used in flags + cancel tag
    tag_cps = (FLAG_TAGS | {CANCEL_TAG}) - set(_Cmap(font).keys())
    glyph_order = font.getGlyphOrder()
    for cp in sorted(tag_cps):
        glyph_name = f"u{cp:04X}"
        assert glyph_name not in glyph_order, f"{glyph_name} already in font"
        glyph_order.append(glyph_name)
        if "glyf" in font:
            font["glyf"][glyph_name] = glyf.Glyph()
        font["hmtx"][glyph_name] = (0, 0)
        _add_cmap_entries(font, cp, glyph_name)
    font.setGlyphOrder(glyph_order)


def _add_vertical_layout_tables(font):
    # Upstream scales these from the CBDT font; here each font is monospaced
    # on its own, so the vertical advance is its line height.
    hhea = font["hhea"]
    height = hhea.ascent - hhea.descent
    vhea = font["vhea"] = ttLib.newTable("vhea")
    vhea.tableVersion = 0x00010000
    vhea.ascent = height // 2
    vhea.descent = -(height - height // 2)
    vhea.lineGap = 0
    for attr in (
        "advanceHeightMax", "minTopSideBearing", "minBottomSideBearing", "yMaxExtent",
        "caretSlopeRise", "caretSlopeRun", "caretOffset", "reserved0", "reserved1",
        "reserved2", "reserved3", "reserved4", "metricDataFormat", "numberOfVMetrics",
    ):
        setattr(vhea, attr, 0)
    vmtx = font["vmtx"] = ttLib.newTable("vmtx")
    vmtx.metrics = {gn: (height, 0) for gn in font.getGlyphOrder()}


def _set_no_font_embedding_restrictions(font):
    font["OS/2"].fsType = 0


def stamp() -> str:
    date = datetime.date.today().strftime("%Y%m%d")
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, check=True, cwd=ROOT
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    return f"{date}:{sha}"


def process(path: Path, out: Path, version: float, stamp_: str):
    fmt = path.stem.split("-", 1)[1]
    font = ttLib.TTFont(path)
    _set_names(font, fmt, version, stamp_)
    _add_vs_cmap(font)
    _map_missing_flag_tag_chars_to_empty_glyphs(font)
    _add_vertical_layout_tables(font)
    _set_no_font_embedding_restrictions(font)
    font["head"].fontRevision = version
    out.parent.mkdir(parents=True, exist_ok=True)
    font.save(out)
    print(f"wrote {out}")


def font_version(s: str) -> float:
    """`v1.2`, `1.2` → 1.2. Tags carry the font revision, so `major.minor` only."""
    text = s[1:] if s[:1] in "vV" else s
    if not re.fullmatch(r"\d+\.\d+", text):
        raise argparse.ArgumentTypeError(f"{s!r}: want a major.minor version, e.g. v1.2")
    return float(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n")[0])
    ap.add_argument("fonts", nargs="+", type=Path, help="nanoemoji outputs")
    ap.add_argument("-o", "--out-dir", type=Path, default=ROOT / "build" / "out")
    ap.add_argument("--version", type=font_version, default=0.1)
    a = ap.parse_args(argv)
    s = stamp()
    for f in a.fonts:
        process(f, a.out_dir / f.name, a.version, s)


if __name__ == "__main__":
    main()
