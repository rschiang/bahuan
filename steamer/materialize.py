"""`steamer materialize`: copy resolved art into art/ and record provenance.

art/svg/ and art/png/ are generated (git-ignored). Hand-fixed SVGs live in
art/fixes/emoji_u<key>.svg and win over the upstream file. Old SVGs that
picosvg rejects get the automatic fixups in fixups.py; if that's not enough,
the next vector era in the chain is used and the provenance says so.
"""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .emoji import ROOT
from .eras import catalog
from .fixups import apply, picosvg_ok
from .manifest import Manifest
from .resolve import Pick, Resolver

ART = ROOT / "art"
FIXES = ART / "fixes"
FLAGS_OUT = ROOT / "flags" / "out" / "svg"
PROVENANCE = ART / "PROVENANCE.tsv"
COLUMNS = ["key", "era", "commit", "path", "sha", "fixups"]


def _prepare(job: tuple[str, str, str]) -> tuple[str, str, list[str], str | None]:
    """(key, era, src) → (key, era, fixups, error); runs in a worker."""
    key, era, src = job
    text, fixes = apply(Path(src).read_text(encoding="utf-8"))
    return key, era, fixes, picosvg_ok(text)


def _write(path: Path, data: bytes) -> None:
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def svg_source(key: str, era: str) -> Path:
    if catalog()[era].generator == "flags":
        return FLAGS_OUT / f"emoji_u{key}.svg"
    return catalog()[era].master(key)


def vector_candidates(r: Resolver, pick: Pick) -> list[str]:
    """Vector eras to try for a pick, best first."""
    first = pick.vector or pick.era
    rest = [e for e, _ in r.chain(r.keys[pick.key]) if e != first]
    return [e for e in [first, *rest] if e and has_svg(e, pick.key)]


def has_svg(era: str, key: str) -> bool:
    e = catalog()[era].index().get(key)
    return bool(e) and catalog()[era].vector and e["format"] == "svg"


def materialize(manifest: Manifest | None = None, jobs: int = 4, log=print) -> dict[str, list[str]]:
    r = Resolver(manifest or Manifest.load())
    picks = r.resolve_all()
    for sub in ("svg", "png"):
        (ART / sub).mkdir(parents=True, exist_ok=True)

    # First pass: try each pick's preferred vector era.
    todo = {k: vector_candidates(r, p) for k, p in picks.items()}
    chosen: dict[str, tuple[str, list[str]]] = {}
    notes: dict[str, list[str]] = {}
    while todo:
        jobs_ = []
        for key, cands in list(todo.items()):
            if (FIXES / f"emoji_u{key}.svg").exists():
                chosen[key] = ("fixes", ["hand-fixed"])
                del todo[key]
            elif not cands:
                notes.setdefault("no_vector", []).append(key)
                del todo[key]
            elif catalog()[cands[0]].generator:
                chosen[key] = (cands[0], ["waveflag"])
                del todo[key]
            else:
                jobs_.append((key, cands[0], str(svg_source(key, cands[0]))))
        if not jobs_:
            break
        with ProcessPoolExecutor(jobs) as pool:
            for key, era, fixes, err in pool.map(_prepare, jobs_, chunksize=16):
                if err is None:
                    chosen[key] = (era, fixes)
                    del todo[key]
                else:
                    notes.setdefault("picosvg_rejected", []).append(f"{key}@{era}")
                    todo[key] = todo[key][1:]

    rows = []
    for key, pick in picks.items():
        dst = ART / "svg" / f"emoji_u{key}.svg"
        if key in chosen:
            era, fixes = chosen[key]
            if era == "fixes":
                _write(dst, (FIXES / dst.name).read_bytes())
                rows.append([key, pick.era or "", "", f"art/fixes/{dst.name}", "", "hand-fixed"])
            else:
                src = svg_source(key, era)
                text = src.read_text(encoding="utf-8")
                if fixes and fixes != ["waveflag"]:
                    text, _ = apply(text)
                _write(dst, text.encode("utf-8"))
                e = catalog()[era].index()[key]
                if era != pick.era:
                    fixes = [*fixes, f"vector-from:{era}"]
                rows.append([key, pick.era or "", catalog()[era].commit, e["path"], e["sha"], ",".join(fixes)])
        if pick.era and not catalog()[pick.era].vector:
            # Raster-only pick: keep the upstream PNG for the bitmap builds.
            _write(ART / "png" / f"emoji_u{key}.png", catalog()[pick.era].master(key).read_bytes())
            e = catalog()[pick.era].index()[key]
            rows.append([key, pick.era, catalog()[pick.era].commit, e["path"], e["sha"], "png"])

    # Drop art no longer picked; unchanged files keep their mtime for ninja.
    keep = {f"emoji_u{k}.svg" for k in chosen} | {
        f"emoji_u{k}.png" for k, p in picks.items() if p.era and not catalog()[p.era].vector
    }
    for sub in ("svg", "png"):
        for f in (ART / sub).iterdir():
            if f.name not in keep:
                f.unlink()
    PROVENANCE.write_text(
        "\t".join(COLUMNS) + "\n" + "".join("\t".join(r) + "\n" for r in rows), encoding="utf-8"
    )
    log(f"art/svg: {len(chosen)} SVGs; art/png: {sum(1 for r in rows if r[-1] == 'png')} PNGs")
    for k, v in notes.items():
        log(f"{k}: {len(v)}: {' '.join(v[:20])}{' …' if len(v) > 20 else ''}")
    return notes
