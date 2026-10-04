"""The selection manifest, selection/selection.toml.

    [defaults]  fallback = [...], avoid = [...]
    [subgroup]  subgroup = "era"  (or a list, tried in order before the fallback)
    [override]  key = "era"
    [redraw]    key = "why no era is acceptable"

Reasons live in inline comments, so edits go through tomlkit to keep them.
"""

from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

from .emoji import ROOT, by_key, key_from_text, subgroups
from .eras import catalog

MANIFEST = ROOT / "selection" / "selection.toml"


@dataclass
class Manifest:
    fallback: list[str]
    avoid: list[str]
    subgroup: dict[str, str | list[str]] = field(default_factory=dict)
    override: dict[str, str | list[str]] = field(default_factory=dict)
    redraw: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = MANIFEST) -> "Manifest":
        return cls.parse(path.read_text(encoding="utf-8"))

    @classmethod
    def parse(cls, text: str) -> "Manifest":
        doc = tomlkit.parse(text).unwrap()
        d = doc.get("defaults", {})
        return cls(
            fallback=list(d.get("fallback", ["android-12", "latest"])),
            avoid=list(d.get("avoid", [])),
            subgroup=dict(doc.get("subgroup", {})),
            override=dict(doc.get("override", {})),
            redraw=dict(doc.get("redraw", {})),
        )

    def lint(self) -> list[str]:
        """Problems that would make resolution meaningless."""
        eras, sgs, keys = catalog(), subgroups(), by_key()
        errs = []
        for e in [*self.fallback, *self.avoid]:
            if e not in eras:
                errs.append(f"defaults: unknown era {e!r}")
        for sg, e in self.subgroup.items():
            if sg not in sgs:
                errs.append(f"subgroup: unknown subgroup {sg!r}")
            for x in [e] if isinstance(e, str) else e:
                if x not in eras:
                    errs.append(f"subgroup.{sg}: unknown era {x!r}")
        for k, e in self.override.items():
            if k not in keys:
                errs.append(f"override: {k!r} is not a fully-qualified emoji key")
            for x in [e] if isinstance(e, str) else e:
                if x not in eras:
                    errs.append(f"override.{k}: unknown era {x!r}")
        for k in self.redraw:
            if k not in keys:
                errs.append(f"redraw: {k!r} is not a fully-qualified emoji key")
        return errs


def target_table(target: str) -> tuple[str, str]:
    """`steamer set` target → (table, key). Subgroup names win over emoji keys."""
    if target in subgroups():
        return "subgroup", target
    key = key_from_text(target)
    if key not in by_key():
        raise ValueError(f"{target!r} is neither a subgroup nor a fully-qualified emoji")
    return "override", key


def set_entry(target: str, era: str | None, comment: str | None = None, path: Path = MANIFEST) -> str:
    """Set (or with era=None, remove) one entry, keeping the file's comments."""
    if era is not None and era not in catalog():
        raise ValueError(f"unknown era {era!r}")
    table_name, key = target_table(target)
    doc = tomlkit.parse(path.read_text(encoding="utf-8"))
    if table_name not in doc:
        doc.add(table_name, tomlkit.table())
    table = doc[table_name]
    if era is None:
        table.pop(key, None)
    else:
        old = table.get(key)
        item = tomlkit.string(era)
        if comment:
            item.comment(comment)
        elif old is not None and old.trivia.comment:
            item.trivia.comment = old.trivia.comment
            item.trivia.comment_ws = old.trivia.comment_ws
        table[key] = item
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return f"{table_name}.{key}"
