"""`steamer fetch`: check out each era from upstream history and normalize it.

The upstream repo is several GB, so it is cloned blob-less and each era is a
sparse worktree holding only its png/, svg/ and flag folders.
"""

import hashlib
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

from .emoji import ROOT, key_from_filename, key_of
from .eras import CACHE, UPSTREAM, Era, catalog, upstream_url, write_index

SIZES = (72, 512)


def tool(name: str) -> str:
    """Prefer the binary installed next to this interpreter (e.g. resvg-cli)."""
    local = Path(sys.executable).parent / name
    return str(local) if local.exists() else shutil.which(name) or name


def git(*args, cwd=UPSTREAM, **kw) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, **kw
    ).stdout


def ensure_clone() -> None:
    if not UPSTREAM.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--filter=blob:none", "--no-checkout", upstream_url(), str(UPSTREAM)],
            check=True,
        )


def ensure_commit(commit: str) -> None:
    try:
        git("cat-file", "-e", f"{commit}^{{commit}}")
    except subprocess.CalledProcessError:
        git("fetch", "--filter=blob:none", "origin")


def sparse_paths(era: Era) -> list[str]:
    paths = [p for p in (era.png, era.svg, era.waved_flags) if p]
    if era.aliases:
        paths.append(era.aliases)
    return paths


def checkout(era: Era) -> None:
    ensure_commit(era.commit)
    wt = era.worktree
    if not wt.exists():
        wt.parent.mkdir(parents=True, exist_ok=True)
        git("worktree", "add", "--no-checkout", "--detach", str(wt), era.commit)
    git("sparse-checkout", "set", "--no-cone", *(f"/{p}" for p in sparse_paths(era)), cwd=wt)
    git("checkout", "--detach", era.commit, cwd=wt)


def blob_shas(era: Era, folder: str) -> dict[str, str]:
    """filename → git blob sha, read from the tree without touching blobs."""
    out = {}
    for line in git("ls-tree", f"{era.commit}:{folder}").splitlines():
        meta, name = line.split("\t", 1)
        _, kind, sha = meta.split()
        if kind == "blob":
            out[name] = sha
    return out


def read_aliases(path: Path) -> dict[str, str]:
    """emoji_aliases.txt: `alias;target # comment`."""
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ";" not in line:
            continue
        a, t = (s.strip() for s in line.split(";", 1))
        try:
            out[key_of(int(p, 16) for p in a.split("_"))] = key_of(int(p, 16) for p in t.split("_"))
        except ValueError:
            pass  # e.g. `unknown_flag`
    return out


def flag_key(code: str) -> str:
    """Region-flags file stem → key: `TW` → regional indicators, `GB-ENG` → tag sequence."""
    if len(code) == 2:
        return key_of(0x1F1E6 + ord(c) - ord("A") for c in code)
    tags = [0xE0000 + ord(c) for c in code.replace("-", "").lower()]
    return key_of([0x1F3F4, *tags, 0xE007F])


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def build_index(era: Era) -> dict[str, dict]:
    """key → {format, path, sha[, png][, alias_of]}; paths are relative to the worktree."""
    found: dict[str, dict] = {}

    def add(folder: str, fmt: str, keyfn=key_from_filename):
        for name, sha in blob_shas(era, folder).items():
            if name.endswith(f".{fmt}") and (key := keyfn(name)) is not None:
                found.setdefault(key, {})[fmt] = (f"{folder}/{name}", sha)

    if era.generator == "flags":
        stem = lambda n: flag_key(n.rsplit(".", 1)[0])  # noqa: E731
        add(era.svg, "svg", stem)
        add(era.png, "png", stem)
        for p in sorted((ROOT / era.extra).glob("emoji_u*.svg")) if era.extra else []:
            data = p.read_bytes()
            sha = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()  # == git hash-object
            found.setdefault(p.stem[len("emoji_u"):], {})["svg"] = (f"{era.extra}/{p.name}", sha)
    else:
        if era.png:
            add(era.png, "png")
        if era.svg and era.vector:
            add(era.svg, "svg")
        if era.waved_flags:
            add(era.waved_flags, "svg")

    index = {}
    for key, f in found.items():
        fmt = "svg" if "svg" in f else "png"
        index[key] = {"format": fmt, "path": f[fmt][0], "sha": f[fmt][1]}
        if fmt == "svg" and "png" in f:
            index[key]["png"] = f["png"][0]

    if era.aliases:
        for alias, target in read_aliases(era.worktree / era.aliases).items():
            if alias not in index and target in index:
                index[alias] = {**index[target], "alias_of": target}
    return index


def render_one(src: Path, fmt: str, out: Path, size: int) -> None:
    if out.exists():
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "svg":
        subprocess.run(
            [tool("resvg"), "-w", str(size), "-h", str(size), str(src), str(out)],
            check=True, capture_output=True,
        )
        return
    # Old PNGs are 136x128 or so; center them on a square before scaling.
    im = Image.open(src).convert("RGBA")
    side = max(im.size)
    sq = Image.new("RGBA", (side, side))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    sq.resize((size, size), Image.LANCZOS).save(out, optimize=True)


def render(era: Era, index: dict[str, dict], jobs: int = 8) -> list[str]:
    """Render every master to the gallery sizes. Returns keys that failed."""
    wt = era.worktree
    tasks = [
        (key, wt / e["path"], e["format"], era.render_path(key, size, e), size)
        for key, e in index.items()
        if "alias_of" not in e
        for size in SIZES
    ]

    failed = []

    def run(t):
        key, src, fmt, out, size = t
        try:
            render_one(src, fmt, out, size)
        except (subprocess.CalledProcessError, OSError):
            # Fall back to the PNG when resvg rejects an SVG.
            if fmt == "svg" and "png" in index[key]:
                render_one(wt / index[key]["png"], "png", out, size)
            failed.append(key)

    with ThreadPoolExecutor(jobs) as pool:
        list(pool.map(run, tasks))
    return sorted(set(failed))


def fetch(era_ids: list[str] | None = None, *, jobs: int = 8, log=print) -> None:
    ensure_clone()
    for era in catalog().values():
        if era_ids and era.id not in era_ids:
            continue
        log(f"{era.id}: checking out {era.commit}")
        checkout(era)
        index = build_index(era)
        meta = {"vector": era.vector, "count": len(index)}
        # Flag art is warped by flags/waveflag.py; its renders come from there.
        if not era.generator:
            log(f"{era.id}: rendering {len(index)} emoji")
            if failed := render(era, index, jobs):
                meta["svg_render_failed"] = failed
                log(f"{era.id}: resvg failed on {len(failed)} SVGs, used PNG instead")
        write_index(era, index, meta)
        log(f"{era.id}: {len(index)} keys → {rel(era.index_path)}")
