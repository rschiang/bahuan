"""Resolve every fully-qualified emoji to an era.

Order: override → subgroup → fallback chain → avoid eras (last resort).
Family rule: skin-tone and gender variants follow their base's era when that
era has the whole family; otherwise the family moves down the base's chain
together. Members with their own override are resolved on their own.

Fallback eras skip art that is byte-identical to an avoided era's (the 2021
refresh left many bordered files untouched) while a later fallback era has
something newer.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .emoji import ROOT, Entry, base_key, by_key, entries
from .eras import catalog
from .manifest import Manifest

RESOLVED = ROOT / "selection" / "resolved.tsv"
COLUMNS = ["key", "emoji", "era", "why", "source", "vector", "family"]


@dataclass
class Pick:
    key: str
    era: str | None
    why: str  # override | subgroup | fallback | avoid | missing
    family: str = ""  # base key, when this pick followed its family
    vector: str = ""  # vector era behind a raster-only pick
    trail: list[str] = field(default_factory=list)  # human-readable decision steps

    @property
    def source(self) -> str:
        if not self.era:
            return ""
        e = catalog()[self.era].index()[self.key]
        return f"{self.era}:{e['path']}"


def as_list(v: str | list[str]) -> list[str]:
    return [v] if isinstance(v, str) else list(v)


def has(era: str, key: str) -> bool:
    return key in catalog()[era].index()


def is_vector(era: str) -> bool:
    return catalog()[era].vector


class Resolver:
    def __init__(self, manifest: Manifest):
        self.m = manifest
        self.entries = entries()
        self.keys = by_key()
        self.families = self._families()

    def _families(self) -> dict[str, list[str]]:
        fam: dict[str, list[str]] = {}
        for e in self.entries:
            root = base_key(e.key)
            fam.setdefault(root if root in self.keys else e.key, []).append(e.key)
        return fam

    def root_of(self, key: str) -> str:
        root = base_key(key)
        return root if root in self.keys else key

    def chain(self, entry: Entry) -> list[tuple[str, str]]:
        """[(era, why)] in the order this emoji tries them."""
        out: list[tuple[str, str]] = []
        if entry.key in self.m.override:
            out += [(e, "override") for e in as_list(self.m.override[entry.key])]
        if entry.subgroup in self.m.subgroup:
            out += [(e, "subgroup") for e in as_list(self.m.subgroup[entry.subgroup])]
        out += [(e, "fallback") for e in self.m.fallback]
        out += [(e, "avoid") for e in self.m.avoid]
        seen, uniq = set(), []
        for era, why in out:
            if era not in seen:
                seen.add(era)
                uniq.append((era, "avoid" if era in self.m.avoid else why))
        return uniq

    def bordered(self, era: str, key: str) -> bool:
        """The era's art for key is the same file as an avoided era's."""
        sha = catalog()[era].index().get(key, {}).get("sha")
        return bool(sha) and era not in self.m.avoid and any(
            catalog()[a].index().get(key, {}).get("sha") == sha for a in self.m.avoid
        )

    def _choose(self, chain, keys: list[str], root: str) -> tuple[str | None, str, list[str]]:
        """First era in chain having all keys, skipping bordered fallbacks when possible."""
        trail, cands = [], []
        for era, why in chain:
            if why == "avoid" and cands:
                break  # bordered fallback art beats an avoided era
            missing = [k for k in keys if not has(era, k)]
            if missing:
                what = "missing" if len(keys) == 1 else f"missing {len(missing)} of {len(keys)} in family"
                trail.append(f"{era} ({why}): {what}")
                continue
            if why == "fallback" and self.bordered(era, root):
                trail.append(f"{era} ({why}): has it, but unchanged from an avoided era")
                cands.append((era, why))
                continue
            trail.append(f"{era} ({why}): has it" + (f" (whole family of {len(keys)})" if len(keys) > 1 else ""))
            return era, why, trail
        if cands:
            trail.append(f"only bordered art left; using {cands[0][0]}")
            return cands[0][0], cands[0][1], trail
        return None, "missing", trail

    def _single(self, entry: Entry) -> Pick:
        era, why, trail = self._choose(self.chain(entry), [entry.key], entry.key)
        return Pick(entry.key, era, why, trail=trail)

    def _vector_behind(self, entry: Entry, pick: Pick) -> str:
        if not pick.era or is_vector(pick.era):
            return ""
        for era, _ in self.chain(self.keys[pick.family or entry.key]):
            if is_vector(era) and has(era, entry.key):
                return era
        for era, _ in self.chain(entry):
            if is_vector(era) and has(era, entry.key):
                return era
        return ""

    def resolve_all(self) -> dict[str, Pick]:
        picks: dict[str, Pick] = {}
        for root, members in self.families.items():
            followers = [k for k in members if k == root or k not in self.m.override]
            chosen, why, trail = self._choose(self.chain(self.keys[root]), followers, root)
            for k in members:
                if k in self.m.override and k != root:
                    picks[k] = self._single(self.keys[k])
                elif chosen:
                    picks[k] = Pick(k, chosen, why, family=root if k != root else "", trail=list(trail))
                else:
                    # No era has the whole family: fall back one by one.
                    p = self._single(self.keys[k])
                    p.trail = trail + ["no era has the whole family; resolving alone"] + p.trail
                    p.family = root if k != root else ""
                    picks[k] = p
        for e in self.entries:
            picks[e.key].vector = self._vector_behind(e, picks[e.key])
        return {e.key: picks[e.key] for e in self.entries}


def resolve(manifest: Manifest | None = None) -> dict[str, Pick]:
    return Resolver(manifest or Manifest.load()).resolve_all()


def rows(picks: dict[str, Pick]) -> list[list[str]]:
    keys = by_key()
    return [
        [p.key, keys[p.key].text, p.era or "", p.why, p.source, p.vector, p.family]
        for p in picks.values()
    ]


def to_tsv(picks: dict[str, Pick]) -> str:
    lines = ["\t".join(COLUMNS)] + ["\t".join(r) for r in rows(picks)]
    return "\n".join(lines) + "\n"


def write(picks: dict[str, Pick], path: Path = RESOLVED) -> None:
    path.write_text(to_tsv(picks), encoding="utf-8")


def read(path: Path = RESOLVED) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
