"""`steamer gallery` and `steamer import-gallery`.

The gallery is a static page (gallery/index.html) with one sprite sheet per
subgroup. Choices made in it come back as JSON:

    {"subgroup": {"food-fruit": "android-12"}, "override": {"1f34a": null}}

where null removes the entry. `import-gallery` applies that with `steamer set`.
"""

import json
import re
from pathlib import Path

from PIL import Image

from .emoji import ROOT, by_key, subgroups
from .eras import catalog
from .manifest import MANIFEST, Manifest, set_entry
from .resolve import Resolver
from .sheets import sheet_entries, sheet_eras

GALLERY = ROOT / "gallery"
TEMPLATE = Path(__file__).with_name("gallery.html")
TILE = 72
CHUNK = 200  # rows per sprite; WebP tops out at 16383px

SKELETON = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    "</head><body>{}</body></html>\n"
)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", "and")).strip("-")


def build(out: Path = GALLERY, log=print) -> Path:
    m = Manifest.load()
    r = Resolver(m)
    picks = r.resolve_all()
    cat = catalog()
    (out / "sprites").mkdir(parents=True, exist_ok=True)

    data = {
        "eras": {
            e.id: {"title": e.title, "vector": e.vector, "avoid": e.avoid, "note": e.note}
            for e in cat.values()
        },
        "fallback": m.fallback,
        "subgroups": [],
    }
    a11 = cat["android-11"].index()
    for sg, entries in subgroups().items():
        rows, eras = sheet_entries(entries), sheet_eras(sg)
        sheets = [
            Image.new("RGBA", (TILE * len(eras), TILE * min(CHUNK, len(rows) - i)))
            for i in range(0, len(rows), CHUNK)
        ]
        out_rows = []
        for y, e in enumerate(rows):
            have, bordered = [], []
            for x, era in enumerate(eras):
                idx = cat[era].index()
                p = cat[era].render_path(e.key, TILE)
                ok = e.key in idx and p.exists()
                have.append(1 if ok else 0)
                same = ok and era not in m.avoid and a11.get(e.key, {}).get("sha") == idx[e.key]["sha"]
                bordered.append(1 if same else 0)
                if ok:
                    tile = Image.open(p).convert("RGBA")
                    sheets[y // CHUNK].alpha_composite(tile, (x * TILE, (y % CHUNK) * TILE))
            pk = picks[e.key]
            out_rows.append({
                "k": e.key, "t": e.text, "n": e.name, "v": e.version,
                "have": have, "b": bordered, "pick": pk.era, "why": pk.why,
                **({"ov": m.override[e.key]} if e.key in m.override else {}),
                **({"redraw": m.redraw[e.key]} if e.key in m.redraw else {}),
            })
        sprites = []
        for i, sheet in enumerate(sheets):
            sprites.append(f"sprites/{slug(sg)}{f'-{i + 1}' if len(sheets) > 1 else ''}.webp")
            sheet.save(out / sprites[-1], "WEBP", quality=82, method=4)
        data["subgroups"].append({
            "name": sg, "group": entries[0].group, "eras": eras, "sprites": sprites, "chunk": CHUNK,
            "manifest": m.subgroup.get(sg), "rows": out_rows, "total": len(entries),
        })

    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    page = TEMPLATE.read_text(encoding="utf-8")
    (out / "page.html").write_text(page, encoding="utf-8")  # body only, for an Artifact
    (out / "index.html").write_text(SKELETON.format(page), encoding="utf-8")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    log(f"gallery: {len(data['subgroups'])} subgroups, {size / 1e6:.1f} MB in {out.relative_to(ROOT)}/")
    return out


def import_choices(path: str | Path, manifest: Path = MANIFEST) -> list[str]:
    """Apply gallery choices to the manifest with comment-preserving edits."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    keys, sgs = by_key(), subgroups()
    done = []
    for sg, era in data.get("subgroup", {}).items():
        if sg not in sgs:
            raise ValueError(f"unknown subgroup {sg!r}")
        done.append(("unset " if era is None else "set ") + set_entry(sg, era, path=manifest) + (f" = {era}" if era else ""))
    for key, era in data.get("override", {}).items():
        if key not in keys:
            raise ValueError(f"unknown emoji key {key!r}")
        note = f"{keys[key].text} from the gallery" if era else None
        done.append(("unset " if era is None else "set ") + set_entry(key, era, note, path=manifest) + (f" = {era}" if era else ""))
    return done
