"""The era catalog (sources/eras.toml) and each era's fetched index."""

import json
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from .emoji import ROOT

SOURCES = ROOT / "sources"
CACHE = SOURCES / "cache"
UPSTREAM = CACHE / "noto-emoji"


@dataclass(frozen=True)
class Era:
    id: str
    title: str
    commit: str
    vector: bool
    emoji: str = ""
    tag: str = ""
    png: str = ""
    svg: str = ""
    aliases: str = ""
    waved_flags: str = ""
    generator: str = ""
    avoid: bool = False
    note: str = ""

    @property
    def dir(self) -> Path:
        return SOURCES / self.id

    @property
    def worktree(self) -> Path:
        return CACHE / "worktrees" / self.id

    @property
    def index_path(self) -> Path:
        return self.dir / "index.json"

    def index(self) -> dict[str, dict]:
        return load_index(self.id)

    def master(self, key: str) -> Path | None:
        """The upstream file (SVG if any, else PNG) for a key."""
        e = self.index().get(key)
        return self.worktree / e["path"] if e else None

    def render_path(self, key: str, size: int, entry: dict | None = None) -> Path:
        e = entry if entry is not None else self.index().get(key, {})
        return self.dir / "png" / str(size) / f"{e.get('alias_of', key)}.png"


@cache
def catalog(path: Path = SOURCES / "eras.toml") -> dict[str, Era]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {k: Era(id=k, **v) for k, v in data["era"].items()}


def upstream_url() -> str:
    return tomllib.loads((SOURCES / "eras.toml").read_text())["upstream"]


@cache
def load_index(era_id: str) -> dict[str, dict]:
    p = catalog()[era_id].index_path
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))["emoji"]


def write_index(era: Era, emoji: dict[str, dict], meta: dict | None = None) -> None:
    era.dir.mkdir(parents=True, exist_ok=True)
    # One entry per line keeps diffs readable.
    lines = [f"  {json.dumps(k)}: {json.dumps(v, sort_keys=True)}" for k, v in sorted(emoji.items())]
    head = json.dumps({"era": era.id, "commit": era.commit, **(meta or {})}, sort_keys=True)[1:-1]
    era.index_path.write_text(
        "{" + head + ', "emoji": {\n' + ",\n".join(lines) + "\n}}\n", encoding="utf-8"
    )
    load_index.cache_clear()
