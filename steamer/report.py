"""`steamer explain` and `steamer report`."""

from collections import Counter, defaultdict

from .emoji import by_key, cps_of, key_of
from .eras import catalog
from .manifest import Manifest
from .resolve import Pick, Resolver

PEOPLE = {0x1F468, 0x1F469}  # man, woman → person, to group professions
PERSON = 0x1F9D1


def explain(key: str, manifest: Manifest | None = None) -> str:
    m = manifest or Manifest.load()
    r = Resolver(m)
    e = r.keys[key]
    pick = r.resolve_all()[key]
    lines = [
        f"{e.text}  {key}  {e.name}  (E{e.version}, {e.group} / {e.subgroup})",
        f"→ {pick.era or 'none'} ({pick.why})",
    ]
    if key in m.override:
        lines.append(f"  override: {m.override[key]}")
    if e.subgroup in m.subgroup:
        lines.append(f"  subgroup {e.subgroup}: {m.subgroup[e.subgroup]}")
    root = r.root_of(key)
    if root != key:
        lines.append(f"  family of {root} ({r.keys[root].name}); follows its era")
    lines += [f"  {s}" for s in pick.trail]
    if pick.vector:
        lines.append(f"  raster-only pick; vector formats use {pick.vector}")
    if pick.source:
        lines.append(f"  source: {pick.source}")
    if key in m.redraw:
        lines.append(f"  redraw backlog: {m.redraw[key]}")
    return "\n".join(lines)


def kin(key: str) -> str:
    """Group key for style checks: drop tones, fold man/woman into person."""
    cps = [cp for cp in cps_of(key) if not 0x1F3FB <= cp <= 0x1F3FF]
    cps = [PERSON if cp in PEOPLE and len(cps) > 1 else cp for cp in cps]
    if len(cps) == 3 and cps[1] == 0x200D and cps[2] in (0x2640, 0x2642):
        cps = cps[:1]
    return key_of(cps)


def bordered(pick: Pick) -> bool:
    """Picked art identical to the bordered android-11 file."""
    if not pick.era or pick.era == "android-11":
        return pick.era == "android-11"
    a = catalog()["android-11"].index().get(pick.key)
    b = catalog()[pick.era].index().get(pick.key)
    return bool(a and b and a["sha"] == b["sha"])


def report(picks: dict[str, Pick], manifest: Manifest | None = None) -> str:
    m = manifest or Manifest.load()
    keys = by_key()
    out = []

    def section(title):
        out.extend(["", f"## {title}"])

    eras = [e for e in catalog() if any(p.era == e for p in picks.values())]
    out.append(f"# Bahuan selection report — {len(picks)} emoji")

    section("Coverage by Emoji version")
    out.append("| version | total | " + " | ".join(eras) + " | none |")
    out.append("|---" * (len(eras) + 3) + "|")
    byver = defaultdict(Counter)
    for p in picks.values():
        byver[keys[p.key].version][p.era or "none"] += 1
    for v in sorted(byver, key=lambda s: tuple(map(int, s.split(".")))):
        c = byver[v]
        out.append(f"| {v} | {sum(c.values())} | " + " | ".join(str(c[e] or "") for e in eras) + f" | {c['none'] or ''} |")

    section("Why")
    why = Counter(p.why for p in picks.values())
    out.append(", ".join(f"{w}: {n}" for w, n in why.most_common()))

    section("Fallbacks by subgroup")
    fb = defaultdict(Counter)
    for p in picks.values():
        if p.why == "fallback":
            fb[keys[p.key].subgroup][p.era] += 1
    for sg, c in fb.items():
        out.append(f"- {sg}: " + ", ".join(f"{e} ×{n}" for e, n in c.most_common()))

    section("Avoided eras used")
    av = [p for p in picks.values() if p.why == "avoid"]
    out += [f"- {keys[p.key].text} {p.key} {keys[p.key].name}: {p.era}" for p in av] or ["none"]

    section("Mixed styles inside a family")
    groups = defaultdict(set)
    for p in picks.values():
        groups[kin(p.key)].add(p.era)
    mixed = {k: v for k, v in groups.items() if len(v) > 1}
    for k, v in mixed.items():
        label = keys[k].name if k in keys else k
        out.append(f"- {k} ({label}): {', '.join(sorted(e or 'none' for e in v))}")
    if not mixed:
        out.append("none")

    section("Raster-only picks")
    ro = [p for p in picks.values() if p.era and not catalog()[p.era].vector]
    no_vec = [p for p in ro if not p.vector]
    out.append(f"{len(ro)} picks from PNG-only eras; vector formats use the era shown.")
    c = Counter((p.era, p.vector or "NONE") for p in ro)
    out += [f"- {a} → {b}: {n}" for (a, b), n in c.most_common()]
    if no_vec:
        out.append(f"No vector master at all: {' '.join(p.key for p in no_vec)}")

    section("Redraw backlog")
    out.append("Listed in the manifest:")
    out += [f"- {keys[k].text} {k} {keys[k].name}: {why}" for k, why in m.redraw.items()] or ["  none"]
    bd = [p for p in picks.values() if bordered(p) and p.key not in m.redraw]
    by_sg = defaultdict(list)
    for p in bd:
        by_sg[keys[p.key].subgroup].append(p.key)
    out.append(f"Still in the bordered style (art unchanged since android-11): {len(bd)}")
    out += [f"- {sg}: {len(ks)}" for sg, ks in sorted(by_sg.items(), key=lambda kv: -len(kv[1]))]
    return "\n".join(out) + "\n"
