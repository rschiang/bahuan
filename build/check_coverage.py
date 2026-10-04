"""Check that each font renders every fully-qualified emoji-test sequence as a
single glyph, shaping with HarfBuzz the way browsers do."""

import sys
from pathlib import Path

import uharfbuzz as hb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from steamer.emoji import entries  # noqa: E402


def check(path: Path) -> list[str]:
    blob = hb.Blob.from_file_path(str(path))
    font = hb.Font(hb.Face(blob))
    bad = []
    for e in entries():
        buf = hb.Buffer()
        buf.add_str(e.text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        glyphs = [(i.codepoint, p.x_advance) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]
        visible = [g for g, adv in glyphs if adv > 0]
        if any(g == 0 for g, _ in glyphs) or len(visible) != 1:
            bad.append(f"{e.key} {e.name}: {len(visible)} visible glyphs {glyphs}")
    return bad


def main(paths):
    failed = False
    for p in map(Path, paths):
        bad = check(p)
        print(f"{p.name}: {len(entries()) - len(bad)}/{len(entries())} sequences shape to one glyph")
        for line in bad[:20]:
            print("  " + line)
        failed |= bool(bad)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
