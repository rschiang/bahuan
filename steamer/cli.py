"""steamer command line."""

import argparse
import sys


def cmd_fetch(a):
    from .fetch import fetch

    fetch(a.eras or None, jobs=a.jobs)


def cmd_sheets(a):
    from .sheets import build, build_group, load_groups

    groups = load_groups()
    if unknown := [g for g in a.group if g not in groups]:
        sys.exit(f"unknown group {' '.join(unknown)}; known: {' '.join(groups)}")
    for g in a.group:
        build_group(g, groups[g]["keys"])
    if a.subgroups or not a.group:
        build(only=a.subgroups or None)


def _manifest():
    from .manifest import Manifest

    m = Manifest.load()
    if errs := m.lint():
        sys.exit("selection.toml:\n  " + "\n  ".join(errs))
    return m


def cmd_lint(a):
    from .redraw import lint

    _manifest()
    if errs := lint():
        sys.exit("recipes.toml:\n  " + "\n  ".join(errs))
    print("selection.toml, recipes.toml: ok")


def cmd_redraw(a):
    from .redraw import build

    build()


def cmd_resolve(a):
    from .resolve import RESOLVED, resolve, to_tsv

    text = to_tsv(resolve(_manifest()))
    if a.check:
        if not RESOLVED.exists() or RESOLVED.read_text(encoding="utf-8") != text:
            sys.exit("resolved.tsv is out of date; run `steamer resolve`")
        print("resolved.tsv: up to date")
        return
    RESOLVED.write_text(text, encoding="utf-8")
    print(f"wrote {RESOLVED.name}: {text.count(chr(10)) - 1} emoji")


def cmd_explain(a):
    from .emoji import by_key, key_from_text
    from .report import explain

    key = key_from_text(a.emoji)
    if key not in by_key():
        sys.exit(f"{a.emoji!r} is not a fully-qualified emoji")
    print(explain(key, _manifest()))


def cmd_set(a):
    from .manifest import set_entry

    try:
        where = set_entry(a.target, None if a.unset else a.era, a.message)
    except ValueError as e:
        sys.exit(str(e))
    print(f"{'removed' if a.unset else 'set'} {where}")


def cmd_report(a):
    from .report import report
    from .resolve import resolve

    m = _manifest()
    print(report(resolve(m), m), end="")


def cmd_materialize(a):
    from .materialize import materialize

    materialize()


def cmd_gallery(a):
    from .gallery import build

    build()


def cmd_import_gallery(a):
    from .gallery import import_choices

    for line in import_choices(a.choices):
        print(line)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="steamer", description="Pick Bahuan's emoji eras.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("fetch", help="check out and render each era from upstream")
    s.add_argument("eras", nargs="*", help="era IDs (default: all)")
    s.add_argument("-j", "--jobs", type=int, default=8)
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("sheets", help="contact sheets per subgroup, eras as columns")
    s.add_argument("subgroups", nargs="*")
    s.add_argument("--group", action="append", default=[], metavar="NAME", help="named key group from selection/groups.toml (repeatable)")
    s.set_defaults(func=cmd_sheets)

    s = sub.add_parser("lint", help="check selection.toml")
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser("resolve", help="write selection/resolved.tsv")
    s.add_argument("--check", action="store_true", help="fail if resolved.tsv is stale")
    s.set_defaults(func=cmd_resolve)

    s = sub.add_parser("explain", help="show the decision chain for one emoji")
    s.add_argument("emoji", help="emoji, key (1f34a) or U+1F34A")
    s.set_defaults(func=cmd_explain)

    s = sub.add_parser("set", help="set a subgroup or emoji era, keeping comments")
    s.add_argument("target", help="subgroup name, emoji or key")
    s.add_argument("era", nargs="?")
    s.add_argument("-m", "--message", help="inline comment")
    s.add_argument("--unset", action="store_true", help="remove the entry")
    s.set_defaults(func=cmd_set)

    s = sub.add_parser("report", help="coverage, fallbacks, avoided eras, backlog")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("materialize", help="copy resolved art into art/")
    s.set_defaults(func=cmd_materialize)

    s = sub.add_parser("gallery", help="build the static comparison gallery")
    s.set_defaults(func=cmd_gallery)

    s = sub.add_parser("redraw", help="derive art/derived/ from art/recipes.toml")
    s.set_defaults(func=cmd_redraw)

    s = sub.add_parser("import-gallery", help="apply choices exported from the gallery")
    s.add_argument("choices", help="choices JSON file")
    s.set_defaults(func=cmd_import_gallery)

    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.cmd == "set" and not a.unset and not a.era:
        sys.exit("steamer set: era required (or --unset)")
    return a.func(a) or 0


if __name__ == "__main__":
    sys.exit(main())
