"""woff2 builds of Bahuan-COLRv1 for the web: the full font plus a flags /
no-flags split, and a stylesheet that loads them by unicode-range."""

import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parent / "out"
FLAG_RANGES = [(0x1F1E6, 0x1F1FF), (0xE0020, 0xE007F)]


def _ranges(cps):
    cps, out = sorted(cps), []
    for cp in cps:
        if out and cp == out[-1][1] + 1:
            out[-1][1] = cp
        else:
            out.append([cp, cp])
    return out


def _css_range(cps) -> str:
    return ", ".join(f"U+{a:X}" if a == b else f"U+{a:X}-{b:X}" for a, b in _ranges(cps))


def _subset(src: Path, dst: Path, unicodes) -> None:
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    font = TTFont(src)
    s = subset.Subsetter(opts)
    s.populate(unicodes=unicodes)
    s.subset(font)
    font.flavor = "woff2"
    font.save(dst)


def main(src: Path = OUT / "Bahuan-COLRv1.ttf") -> None:
    cmap = TTFont(src).getBestCmap()
    is_flag = lambda cp: any(a <= cp <= b for a, b in FLAG_RANGES)  # noqa: E731
    # 1F3F4 must stay with the tag characters: GSUB can't ligate across files.
    flags = {cp for cp in cmap if is_flag(cp)} | {0x1F3F4}
    rest = {cp for cp in cmap if not is_flag(cp)} - {0x1F3F4}
    parts = {"": set(cmap), "-flags": flags, "-noflags": rest}
    for suffix, cps in parts.items():
        _subset(src, OUT / f"Bahuan-COLRv1{suffix}.woff2", cps)
    css = "".join(
        "@font-face {\n"
        '  font-family: "Bahuan";\n'
        f'  src: url("Bahuan-COLRv1{suffix}.woff2") format("woff2");\n'
        f"  unicode-range: {_css_range(cps)};\n"
        "  font-display: swap;\n"
        "}\n"
        for suffix, cps in parts.items()
        if suffix
    )
    (OUT / "bahuan.css").write_text(css, encoding="utf-8")
    print(f"wrote {len(parts)} woff2 files and bahuan.css to {OUT}")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:]))
