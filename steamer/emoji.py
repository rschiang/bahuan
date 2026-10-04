"""Emoji keys and the pinned emoji-test.txt."""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMOJI_TEST = ROOT / "sources" / "emoji-test.txt"

FE0F = 0xFE0F
SKIN_TONES = range(0x1F3FB, 0x1F3FF + 1)
ZWJ = 0x200D
GENDER_SIGNS = {0x2640, 0x2642}


def key_of(cps) -> str:
    """Codepoints → key: lowercase hex joined by `_`, FE0F removed."""
    return "_".join(f"{cp:04x}" for cp in cps if cp != FE0F)


def cps_of(key: str) -> tuple[int, ...]:
    return tuple(int(p, 16) for p in key.split("_"))


def key_from_text(text: str) -> str:
    """Accept a key, `U+1F34A`-style codepoints or the emoji itself."""
    t = text.strip()
    if re.fullmatch(r"[0-9a-fA-F]{4,6}([_ ][0-9a-fA-F]{4,6})*", t):
        return key_of(int(p, 16) for p in re.split(r"[_ ]", t))
    if re.fullmatch(r"(U\+[0-9a-fA-F]{4,6}\s*)+", t, re.I):
        return key_of(int(p[2:], 16) for p in t.split())
    return key_of(ord(c) for c in t)


_FILE_RE = re.compile(r"emoji_u([0-9a-f_]+)\.(png|svg)$", re.I)


def key_from_filename(name: str) -> str | None:
    m = _FILE_RE.search(name)
    if not m:
        return None
    return key_of(int(p, 16) for p in m.group(1).lower().split("_"))


@dataclass(frozen=True)
class Entry:
    key: str
    cps: tuple[int, ...]  # as written in emoji-test, FE0F included
    group: str
    subgroup: str
    version: str  # Emoji version, e.g. "5.0"
    name: str
    order: int

    @property
    def text(self) -> str:
        return "".join(map(chr, self.cps))


_LINE_RE = re.compile(
    r"^(?P<cps>[0-9A-F ]+?)\s*;\s*fully-qualified\s*#\s*\S+\s+E(?P<ver>[\d.]+)\s+(?P<name>.+)$"
)


@cache
def entries(path: Path = EMOJI_TEST) -> tuple[Entry, ...]:
    """Fully-qualified entries in file order."""
    out, group, subgroup = [], "", ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
        elif line.startswith("# subgroup:"):
            subgroup = line.split(":", 1)[1].strip()
        elif m := _LINE_RE.match(line):
            cps = tuple(int(p, 16) for p in m["cps"].split())
            out.append(Entry(key_of(cps), cps, group, subgroup, m["ver"], m["name"], len(out)))
    return tuple(out)


@cache
def by_key() -> dict[str, Entry]:
    return {e.key: e for e in entries()}


def subgroups() -> dict[str, list[Entry]]:
    out: dict[str, list[Entry]] = {}
    for e in entries():
        out.setdefault(e.subgroup, []).append(e)
    return out


def base_key(key: str) -> str:
    """The family root: drop skin tones, gender signs and ZWJ-joined parts.

    `1f469_1f3fd_200d_1f52c` (woman scientist, medium) → `1f469_200d_1f52c`
    falls back to its tone-less form; the tone-less form's base is itself
    unless it is a gendered variant of a single emoji (`1f3c3_200d_2640` →
    `1f3c3`).
    """
    cps = [cp for cp in cps_of(key) if cp not in SKIN_TONES]
    # Gendered variants of a single base: X ZWJ ♀/♂
    if len(cps) == 3 and cps[1] == ZWJ and cps[2] in GENDER_SIGNS:
        cps = cps[:1]
    return key_of(cps)
