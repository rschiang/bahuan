"""`steamer sheets`: one PNG contact sheet per subgroup, eras as columns."""

import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .emoji import ROOT, SKIN_TONES, Entry, by_key, subgroups
from .eras import catalog

CELL = 72
PAD = 12
LABEL_W = 240
HEAD_H = 40
ROWS_PER_PAGE = 40
FLAG_SUBGROUPS = {"country-flag", "subdivision-flag"}


def has_tone(e: Entry) -> bool:
    return any(cp in SKIN_TONES for cp in e.cps)


def sheet_entries(entries: list[Entry]) -> list[Entry]:
    """Skin-tone variants follow their base (family rule), so sheets skip them."""
    return [e for e in entries if not has_tone(e)]


def sheet_eras(subgroup: str) -> list[str]:
    eras = [e.id for e in catalog().values() if not e.generator]
    if subgroup in FLAG_SUBGROUPS:
        eras.append("waveflag")
    return eras


def same_as_bordered(key: str, era: str) -> bool:
    """True when the art is byte-identical to the bordered android-11 file."""
    a, b = catalog()["android-11"].index().get(key), catalog()[era].index().get(key)
    return bool(a and b and a["sha"] == b["sha"])


def _font(size: int):
    return ImageFont.load_default(size)


def draw_sheet(subgroup: str, rows: list[Entry], eras: list[str], page: str = "") -> Image.Image:
    cat = catalog()
    w = LABEL_W + len(eras) * (CELL + PAD) + PAD
    h = HEAD_H + len(rows) * (CELL + PAD) + PAD
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    small, tiny = _font(13), _font(11)
    d.text((PAD, 6), f"{subgroup}{page}", fill="black", font=_font(15))
    d.text((PAD, 23), "=11: unchanged since android-11", fill="#a00", font=tiny)
    for c, era in enumerate(eras):
        x = LABEL_W + c * (CELL + PAD)
        d.text((x, 8), era, fill="black", font=small)
        if cat[era].avoid:
            d.text((x, 23), "(avoid)", fill="#a00", font=tiny)
        elif not cat[era].vector:
            d.text((x, 23), "(PNG only)", fill="#666", font=tiny)
    for r, e in enumerate(rows):
        y = HEAD_H + r * (CELL + PAD)
        if r % 2:
            d.rectangle((0, y - PAD // 2, w, y + CELL + PAD // 2), fill="#f3f3f3")
        d.text((PAD, y + 8), e.key, fill="black", font=small)
        d.text((PAD, y + 26), e.name[:34], fill="#333", font=tiny)
        d.text((PAD, y + 42), f"E{e.version}", fill="#888", font=tiny)
        for c, era in enumerate(eras):
            x = LABEL_W + c * (CELL + PAD)
            p = cat[era].render_path(e.key, CELL)
            if e.key in cat[era].index() and p.exists():
                tile = Image.open(p).convert("RGBA")
                im.paste(tile, (x, y), tile)
                if not cat[era].avoid and same_as_bordered(e.key, era):
                    d.text((x + CELL - 22, y + CELL - 10), "=11", fill="#a00", font=tiny)
            else:
                d.rectangle((x, y, x + CELL - 1, y + CELL - 1), outline="#ddd")
                d.line((x, y, x + CELL - 1, y + CELL - 1), fill="#eee")
    return im


def build(out_dir: Path = ROOT / "sheets", only: list[str] | None = None, log=print) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for sg, entries in subgroups().items():
        if only and sg not in only:
            continue
        rows, eras = sheet_entries(entries), sheet_eras(sg)
        pages = [rows[i : i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)]
        for n, chunk in enumerate(pages, 1):
            suffix = f"-{n}" if len(pages) > 1 else ""
            label = f" (page {n}/{len(pages)})" if len(pages) > 1 else ""
            path = out_dir / f"{sg}{suffix}.png"
            draw_sheet(sg, chunk, eras, label).save(path, optimize=True)
            written.append(path)
    log(f"wrote {len(written)} sheets to {out_dir.relative_to(ROOT)}/")
    return written


GROUPS = ROOT / "selection" / "groups.toml"


def load_groups(path: Path = GROUPS) -> dict[str, dict]:
    return tomllib.loads(path.read_text(encoding="utf-8")).get("group", {})


def build_group(name: str, keys: list[str], out_dir: Path = ROOT / "sheets", log=print) -> list[Path]:
    """One sheet for a hand-picked key list (any subgroups), in the given order."""
    lookup = by_key()
    rows = [lookup[k] for k in keys]
    eras = [e.id for e in catalog().values() if not e.generator]
    if any(e.subgroup in FLAG_SUBGROUPS for e in rows):
        eras.append("waveflag")
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = [rows[i : i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)]
    written = []
    for n, chunk in enumerate(pages, 1):
        suffix = f"-{n}" if len(pages) > 1 else ""
        label = f" (page {n}/{len(pages)})" if len(pages) > 1 else ""
        path = out_dir / f"group-{name}{suffix}.png"
        draw_sheet(name, chunk, eras, label).save(path, optimize=True)
        written.append(path)
    log(f"wrote {len(written)} sheets for group {name} to {out_dir.relative_to(ROOT)}/")
    return written
