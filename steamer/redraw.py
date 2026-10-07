"""`steamer redraw`: derive art from an upstream master by recolouring it.

art/derived/emoji_u<key>.svg is generated (git-ignored) from art/recipes.toml.
Hand-authored art still goes in art/fixes/ and wins over a recipe.
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .emoji import ROOT, by_key
from .eras import catalog
from .fixups import SVG_NS, apply, picosvg_ok

RECIPES = ROOT / "art" / "recipes.toml"
DERIVED = ROOT / "art" / "derived"
DERIVED_PNG = DERIVED / "png"

HEX = re.compile(r"#[0-9A-Fa-f]{6}")
PAINT = ("fill", "stroke", "stop-color")
SHAPES = {f"{{{SVG_NS}}}{t}" for t in ("path", "circle", "ellipse", "polygon", "polyline", "rect", "line")}
CANVAS = 128


@dataclass(frozen=True)
class Layer:
    """A second master drawn on top of the donor, scaled about the canvas centre."""

    era: str
    src: str
    recolor: dict[str, str] = field(default_factory=dict)
    drop: tuple[str, ...] = ()
    fill: str = ""
    subpath: int | None = None  # keep only this subpath of each <path>
    scale: float = 1.0


@dataclass(frozen=True)
class Recipe:
    key: str
    era: str  # donor era id, from "era:key"
    src: str  # donor key
    why: str
    recolor: dict[str, str] = field(default_factory=dict)  # "#rrggbb" → "#rrggbb"
    drop: tuple[str, ...] = ()  # delete elements with this fill
    fill: str = ""  # fill for elements with none
    subpath: int | None = None  # keep only this subpath of each <path>
    add: tuple[Layer, ...] = ()  # masters drawn on top, in order


def _layer(t: dict) -> Layer:
    era, _, src = t.get("from", "").partition(":")
    return Layer(
        era=era,
        src=src,
        recolor=dict(t.get("recolor", {})),
        drop=tuple(t.get("drop", ())),
        fill=t.get("fill", ""),
        subpath=t.get("subpath"),
        scale=float(t.get("scale", 1.0)),
    )


def load(path: Path = RECIPES) -> dict[str, Recipe]:
    if not path.exists():
        return {}
    out = {}
    for key, t in tomllib.loads(path.read_text(encoding="utf-8")).items():
        era, _, src = t.get("from", "").partition(":")
        out[key] = Recipe(
            key=key,
            era=era,
            src=src,
            why=t.get("why", ""),
            recolor=dict(t.get("recolor", {})),
            drop=tuple(t.get("drop", ())),
            fill=t.get("fill", ""),
            subpath=t.get("subpath"),
            add=tuple(_layer(x) for x in t.get("add", ())),
        )
    return out


def _style(el) -> dict[str, str]:
    return {
        k.strip(): v.strip()
        for k, v in (d.split(":", 1) for d in el.get("style", "").split(";") if ":" in d)
    }


def _set_style(el, decls: dict[str, str]) -> None:
    el.set("style", ";".join(f"{k}:{v}" for k, v in decls.items()))


def _own_fill(el) -> str | None:
    return _style(el).get("fill", el.get("fill"))


def _lower(colours) -> set[str]:
    return {c.lower() for c in colours}


def render(r: Recipe) -> str:
    """Donor text → derived SVG text."""
    return transform(catalog()[r.era].master(r.src).read_text(encoding="utf-8"), r)


def transform(text: str, r: Recipe) -> str:
    text, _ = apply(text)
    root = ET.fromstring(text)
    _paint(root, r)
    for layer in r.add:
        _compose(root, layer)
    out = ET.tostring(root, encoding="unicode")
    if err := picosvg_ok(out):
        raise ValueError(f"{r.key}: {err}")
    return out


def _compose(root, layer: "Layer") -> None:
    """Append another master's drawing on top, scaled about the canvas centre."""
    text, _ = apply(catalog()[layer.era].master(layer.src).read_text(encoding="utf-8"))
    donor = ET.fromstring(text)
    _paint(donor, layer)
    g = ET.SubElement(root, f"{{{SVG_NS}}}g")
    if layer.scale != 1:
        shift = CANVAS / 2 * (1 - layer.scale)
        g.set("transform", f"translate({shift:g},{shift:g}) scale({layer.scale:g})")
    g.extend(list(donor))


def _subpath(root, n: int) -> None:
    """Keep only subpath n of every `<path>`; Illustrator frames carry their cut-out as one."""
    for el in root.iter(f"{{{SVG_NS}}}path"):
        parts = [p for p in el.get("d", "").split("M") if p.strip()]
        if n >= len(parts):
            raise ValueError(f"subpath {n}: path has only {len(parts)}")
        el.set("d", "M" + parts[n].strip())


def _paint(root, part) -> None:
    if part.subpath is not None:
        _subpath(root, part.subpath)
    recolor, drop, fill = part.recolor, part.drop, part.fill
    dropped = _lower(drop)
    if dropped:
        for parent in root.iter():
            for child in list(parent):
                f = _own_fill(child)
                if f and f.lower() in dropped:
                    parent.remove(child)

    if recolor:
        mapping = {k.lower(): v for k, v in recolor.items()}
        for el in root.iter():
            for attr in PAINT:
                if (v := el.get(attr)) and v.lower() in mapping:
                    el.set(attr, mapping[v.lower()])
            decls = _style(el)
            hit = False
            for attr in PAINT:
                if (v := decls.get(attr)) and v.lower() in mapping:
                    decls[attr] = mapping[v.lower()]
                    hit = True
            if hit:
                _set_style(el, decls)

    if fill:

        def walk(el, inherited: bool) -> None:
            has = inherited or _own_fill(el) is not None
            if el.tag in SHAPES and not has:
                el.set("fill", fill)
            for c in el:
                walk(c, has)

        walk(root, False)


def _write(path: Path, data: bytes) -> bool:
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def render_path(key: str, size: int = 72) -> Path:
    return DERIVED_PNG / str(size) / f"{key}.png"


def build(log=print) -> list[str]:
    from .fetch import render_one

    recipes = load()
    DERIVED.mkdir(parents=True, exist_ok=True)
    for key, r in recipes.items():
        svg = DERIVED / f"emoji_u{key}.svg"
        if _write(svg, render(r).encode("utf-8")):
            render_path(key).unlink(missing_ok=True)
        render_one(svg, "svg", render_path(key), 72)
    keep = {f"emoji_u{k}.svg" for k in recipes}
    for f in DERIVED.glob("emoji_u*.svg"):
        if f.name not in keep:
            f.unlink()
    for f in DERIVED_PNG.glob("*/*.png"):
        if f.stem not in recipes:
            f.unlink()
    log(f"art/derived: {len(recipes)} SVGs")
    return list(recipes)


def lint(recipes: dict[str, Recipe] | None = None) -> list[str]:
    errs = []
    keys = by_key()
    eras = catalog()
    fixes = ROOT / "art" / "fixes"
    for key, r in (load() if recipes is None else recipes).items():
        if key not in keys:
            errs.append(f"recipes.toml [{key}]: unknown emoji key")
        for part in (r, *r.add):
            if part.era not in eras:
                errs.append(f"recipes.toml [{key}]: unknown donor era {part.era!r}")
            elif part.src not in eras[part.era].index():
                errs.append(f"recipes.toml [{key}]: donor {part.era}:{part.src} not in the era index")
            colours = [
                *part.recolor,
                *part.recolor.values(),
                *part.drop,
                *([part.fill] if part.fill else []),
            ]
            errs += [
                f"recipes.toml [{key}]: bad colour {c!r} (want #rrggbb)"
                for c in colours
                if not HEX.fullmatch(c)
            ]
        if not r.why:
            errs.append(f"recipes.toml [{key}]: missing why")
        if (fixes / f"emoji_u{key}.svg").exists():
            errs.append(f"recipes.toml [{key}]: also in art/fixes/ (ambiguous owner)")
    return errs
