"""steamer command line."""

import argparse
import sys


def cmd_fetch(a):
    from .fetch import fetch

    fetch(a.eras or None, jobs=a.jobs)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="steamer", description="Pick Bahuan's emoji eras.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("fetch", help="check out and render each era from upstream")
    s.add_argument("eras", nargs="*", help="era IDs (default: all)")
    s.add_argument("-j", "--jobs", type=int, default=8)
    s.set_defaults(func=cmd_fetch)

    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    return a.func(a) or 0


if __name__ == "__main__":
    sys.exit(main())
