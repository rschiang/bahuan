"""Make old upstream SVGs acceptable to picosvg/nanoemoji.

Each fixup returns the new text, or None when it doesn't apply; the names of
the ones that ran go into art/PROVENANCE.tsv.
"""

import re
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

_RULE_RE = re.compile(r"([^{}]+)\{([^}]*)\}")


def _q(tag: str) -> str:
    return f"{{{SVG_NS}}}{tag}"


def inline_css(text: str) -> str | None:
    """Illustrator exports put fills in `<style>.st0{fill:#FCC21B}`; inline them."""
    if "<style" not in text:
        return None
    root = ET.fromstring(text)
    rules: dict[str, dict[str, str]] = {}
    for style in root.iter(_q("style")):
        for sel, body in _RULE_RE.findall(style.text or ""):
            decls = dict(
                (p.strip(), v.strip())
                for p, v in (d.split(":", 1) for d in body.split(";") if ":" in d)
            )
            for s in sel.split(","):
                s = s.strip()
                if s.startswith("."):
                    rules.setdefault(s[1:], {}).update(decls)
    for el in root.iter():
        classes = el.attrib.pop("class", "").split()
        for c in classes:
            for prop, val in rules.get(c, {}).items():
                el.attrib.setdefault(prop, val)  # attributes on the element win
    for parent in root.iter():
        for child in list(parent):
            if child.tag == _q("style"):
                parent.remove(child)
    return ET.tostring(root, encoding="unicode")


def drop_unsupported(text: str) -> str | None:
    """Remove `<image>`, `<font>` and `<text>`; nanoemoji can't use them."""
    root = ET.fromstring(text)
    dropped = False
    for parent in root.iter():
        for child in list(parent):
            if child.tag in (_q("image"), _q("font"), _q("text")):
                parent.remove(child)
                dropped = True
    return ET.tostring(root, encoding="unicode") if dropped else None


FIXUPS = [inline_css, drop_unsupported]


def apply(text: str) -> tuple[str, list[str]]:
    applied = []
    for fix in FIXUPS:
        if (new := fix(text)) is not None:
            text, applied = new, applied + [fix.__name__]
    return text, applied


def picosvg_ok(text: str) -> str | None:
    """None if picosvg accepts the SVG, else the error."""
    from picosvg.svg import SVG

    try:
        SVG.fromstring(text).topicosvg()
        return None
    except Exception as e:  # picosvg raises plain ValueErrors
        return f"{type(e).__name__}: {e}"[:300]
