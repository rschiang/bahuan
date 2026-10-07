"""Android 7.1 waved flags, in vector form.

A port of waveflag.c (https://github.com/rschiang/waveflag). The C tool
texture-maps a flag through a cairo mesh patch whose corner colors encode
(u, v), clips it to a rounded wave outline, strokes a luminosity border and
adds a soft-light shade. Here the flag's own SVG paths are pushed through the
same Coons patch (segments are subdivided, mapped, and refit as cubics), so
the result stays vector.

Two outputs per flag:
  out/full/  blend modes as in the C code (luminosity, soft-light); used by
             the golden test and anywhere SVG blending is supported.
  out/svg/   picosvg-clean for nanoemoji: blends approximated with plain
             alpha, clips applied.
"""

import argparse
import io
import math
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from steamer.fetch import flag_key, tool  # noqa: E402

EXTRA = ROOT / "flags" / "extra"


def key_for(src) -> str:
    """Region-flags `US` → regional indicators; extras are named `emoji_u<key>`."""
    stem = Path(src).stem
    return stem[len("emoji_u"):] if stem.startswith("emoji_u") else flag_key(stem)


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

SIZE = 128
STD_ASPECT = 5 / 3
MESH = [(-1, 43), (30, -3), (77, 47), (104, 1), (130, 84), (100, 138), (45, 80), (7, 127)]

# The wave outline from waveflag.c, as (command, relative points…), starting
# with an absolute move and ending with an absolute curve.
WAVE = [
    ("M", (127.15, 81.52)),
    ("l", (-20.51, -66.94)),
    ("c", (-0.61, -2), (-2.22, -3.53), (-4.25, -4.03)),
    ("c", (-0.48, -0.12), (-0.96, -0.18), (-1.44, -0.18)),
    ("c", (-1.56, 0), (-3.07, 0.61), (-4.2, 1.74)),
    ("c", (-9.56, 9.56), (-17.94, 11.38), (-30.07, 11.38)),
    ("c", (-3.68, 0), (-7.72, -0.18), (-11.99, -0.38)),
    ("c", (-3.37, -0.15), (-6.85, -0.31), (-10.62, -0.4)),
    ("c", (-0.66, -0.02), (-1.31, -0.02), (-1.95, -0.02)),
    ("c", (-30.67, 0), (-40.49, 18.56), (-40.89, 19.35)),
    ("c", (-0.52, 1.01), (-0.73, 2.16), (-0.62, 3.29)),
    ("l", (6.72, 66.95)),
    ("c", (0.22, 2.22), (1.67, 4.13), (3.75, 4.95)),
    ("c", (0.7, 0.27), (1.43, 0.4), (2.16, 0.4)),
    ("c", (1.43, 0), (2.84, -0.52), (3.95, -1.5)),
    ("c", (0.1, -0.09), (12.42, -10.63), (32.13, -10.63)),
    ("c", (2.52, 0), (5.09, 0.17), (7.64, 0.51)),
    ("c", (9.27, 1.23), (16.03, 1.78), (21.95, 1.78)),
    ("c", (18.93, 0), (32.93, -6.1), (46.82, -20.38)),
    ("C", (127.24, 85.85), (127.79, 83.59), (127.15, 81.52)),
]

# Shade bands across the patch, and the plain-alpha stand-in for soft-light.
BANDS = 32
SHADE_LIGHT, SHADE_DARK = 0.03, 0.06


PRECISION = 2


def f(x: float) -> str:
    return f"{x:.{PRECISION}f}".rstrip("0").rstrip(".")


# --- geometry -------------------------------------------------------------


def bez(p0, p1, p2, p3, t):
    s = 1 - t
    return (
        s**3 * p0[0] + 3 * s * s * t * p1[0] + 3 * s * t * t * p2[0] + t**3 * p3[0],
        s**3 * p0[1] + 3 * s * s * t * p1[1] + 3 * s * t * t * p2[1] + t**3 * p3[1],
    )


def bez_d(p0, p1, p2, p3, t):
    s = 1 - t
    return (
        3 * s * s * (p1[0] - p0[0]) + 6 * s * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0]),
        3 * s * s * (p1[1] - p0[1]) + 6 * s * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1]),
    )


class Patch:
    """The cairo mesh patch: top/bottom cubic edges, straight left/right."""

    def __init__(self, aspect: float):
        def adj(p):
            x, y = p
            if aspect < 1:
                x = (x - 64) * aspect + 64
            if aspect > 1:
                y = (y - 64) / aspect + 64
            return (x, y)

        m = [adj(p) for p in MESH]
        self.top = (m[0], m[1], m[2], m[3])  # corner 0 → 1
        self.bot = (m[7], m[6], m[5], m[4])  # corner 3 → 2
        self.c00, self.c10, self.c11, self.c01 = m[0], m[3], m[4], m[7]

    def map(self, u: float, v: float) -> tuple[float, float]:
        t, b = bez(*self.top, u), bez(*self.bot, u)
        out = []
        for i in (0, 1):
            left = (1 - v) * self.c00[i] + v * self.c01[i]
            right = (1 - v) * self.c10[i] + v * self.c11[i]
            corner = (
                (1 - u) * (1 - v) * self.c00[i] + u * (1 - v) * self.c10[i]
                + (1 - u) * v * self.c01[i] + u * v * self.c11[i]
            )
            out.append((1 - v) * t[i] + v * b[i] + (1 - u) * left + u * right - corner)
        return out[0], out[1]

    def jacobian(self, u: float, v: float):
        """d(x,y)/du and d(x,y)/dv."""
        t, b = bez(*self.top, u), bez(*self.bot, u)
        dt, db = bez_d(*self.top, u), bez_d(*self.bot, u)
        du, dv = [], []
        for i in (0, 1):
            left = (1 - v) * self.c00[i] + v * self.c01[i]
            right = (1 - v) * self.c10[i] + v * self.c11[i]
            du.append(
                (1 - v) * dt[i] + v * db[i] - left + right
                - (-(1 - v) * self.c00[i] + (1 - v) * self.c10[i] - v * self.c01[i] + v * self.c11[i])
            )
            dv.append(
                -t[i] + b[i] + (1 - u) * (self.c01[i] - self.c00[i]) + u * (self.c11[i] - self.c10[i])
                - (-(1 - u) * self.c00[i] - u * self.c10[i] + (1 - u) * self.c01[i] + u * self.c11[i])
            )
        return du, dv

    def outline(self) -> str:
        """The patch boundary (where the flag texture lands)."""
        w = Warper(self, (0, 0, 1, 1))
        return w.path([("M", (0, 0)), ("L", (1, 0)), ("L", (1, 1)), ("L", (0, 1)), ("Z", ())])


class Warper:
    """Maps flag-space path commands into the 128-unit wave."""

    def __init__(self, patch: Patch, rect: tuple[float, float, float, float]):
        self.p = patch
        self.x0, self.y0, self.w, self.h = rect

    def uv(self, pt):
        return (pt[0] - self.x0) / self.w, (pt[1] - self.y0) / self.h

    def point(self, pt):
        return self.p.map(*self.uv(pt))

    def _deriv(self, pt, d):
        """Chain rule: flag-space tangent d at pt → output tangent."""
        du, dv = self.p.jacobian(*self.uv(pt))
        a, b = d[0] / self.w, d[1] / self.h
        return du[0] * a + dv[0] * b, du[1] * a + dv[1] * b

    def cubic(self, p0, p1, p2, p3) -> list[str]:
        """One flag-space cubic → output cubics (Hermite refit per piece)."""
        u0, v0 = self.uv(p0)
        u3, v3 = self.uv(p3)
        span = abs(u3 - u0) + abs(v3 - v0)
        for q in (p1, p2):
            uq, vq = self.uv(q)
            span = max(span, abs(uq - u0) + abs(vq - v0) + abs(uq - u3) + abs(vq - v3))
        n = max(1, math.ceil(span * 12))
        out = []
        for i in range(n):
            ta, tb = i / n, (i + 1) / n
            a, b = bez(p0, p1, p2, p3, ta), bez(p0, p1, p2, p3, tb)
            da, db = bez_d(p0, p1, p2, p3, ta), bez_d(p0, p1, p2, p3, tb)
            A, B = self.point(a), self.point(b)
            dA, dB = self._deriv(a, da), self._deriv(b, db)
            k = (tb - ta) / 3
            out.append(
                f"C{f(A[0] + dA[0] * k)},{f(A[1] + dA[1] * k)} "
                f"{f(B[0] - dB[0] * k)},{f(B[1] - dB[1] * k)} {f(B[0])},{f(B[1])}"
            )
        return out

    def path(self, cmds) -> str:
        out, cur, start = [], (0.0, 0.0), (0.0, 0.0)
        open_ = False

        def close():
            # Fills close open subpaths with a straight line in flag space,
            # which must be warped too.
            if open_ and cur != start:
                out.extend(self.cubic(cur, _lerp(cur, start, 1 / 3), _lerp(cur, start, 2 / 3), start))

        for cmd, args in cmds:
            if cmd != "M":
                open_ = cmd != "Z"
            if cmd == "M":
                close()
                open_ = False
                cur = start = (args[0], args[1])
                x, y = self.point(cur)
                out.append(f"M{f(x)},{f(y)}")
            elif cmd == "L":
                nxt = (args[0], args[1])
                out += self.cubic(cur, _lerp(cur, nxt, 1 / 3), _lerp(cur, nxt, 2 / 3), nxt)
                cur = nxt
            elif cmd == "Q":
                c, nxt = (args[0], args[1]), (args[2], args[3])
                out += self.cubic(cur, _lerp(cur, c, 2 / 3), _lerp(nxt, c, 2 / 3), nxt)
                cur = nxt
            elif cmd == "C":
                p1, p2, nxt = (args[0], args[1]), (args[2], args[3]), (args[4], args[5])
                out += self.cubic(cur, p1, p2, nxt)
                cur = nxt
            elif cmd == "Z":
                if cur != start:
                    out += self.cubic(cur, _lerp(cur, start, 1 / 3), _lerp(cur, start, 2 / 3), start)
                out.append("Z")
                cur = start
            else:
                raise ValueError(f"unexpected path command {cmd}")
        close()
        return " ".join(out)

    def affine(self) -> tuple[float, ...]:
        """Least-squares affine fit of the warp, for gradients."""
        pts = [(i / 4, j / 4) for i in range(5) for j in range(5)]
        src = [(self.x0 + u * self.w, self.y0 + v * self.h) for u, v in pts]
        dst = [self.p.map(u, v) for u, v in pts]
        return _fit_affine(src, dst)


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _fit_affine(src, dst):
    """Least squares for [x y 1]·M = [X Y], via the 3x3 normal equations."""
    rows = [(x, y, 1.0) for x, y in src]
    ata = [[sum(r[i] * r[j] for r in rows) for j in range(3)] for i in range(3)]
    cols = []
    for k in (0, 1):
        atb = [sum(r[i] * d[k] for r, d in zip(rows, dst)) for i in range(3)]
        cols.append(_solve3(ata, atb))
    (a, c, e), (b, d, f_) = cols
    return a, b, c, d, e, f_


def _solve3(m, v):
    """Cramer's rule."""
    def det(a):
        return (
            a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
        )

    d = det(m)
    out = []
    for i in range(3):
        mi = [row[:] for row in m]
        for r in range(3):
            mi[r][i] = v[r]
        out.append(det(mi) / d)
    return out


def wave_path(aspect: float) -> str:
    """The rounded wave outline, aspect-adjusted like waveflag.c's matrix."""
    sx = aspect if aspect < 1 else 1
    sy = 1 / aspect if aspect > 1 else 1
    tx = 64 * (1 - aspect) if aspect < 1 else 0
    ty = 64 * (1 - 1 / aspect) if aspect > 1 else 0

    def t(p):
        return f(p[0] * sx + tx) + "," + f(p[1] * sy + ty)

    out, cur = [], (0.0, 0.0)
    for cmd, *pts in WAVE:
        if cmd.islower():
            pts = [(cur[0] + x, cur[1] + y) for x, y in pts]
        cur = pts[-1]
        out.append(cmd.upper() + " ".join(t(p) for p in pts))
    return " ".join(out) + " Z"


# --- flag input -----------------------------------------------------------

_LEN_ATTRS_X = {"x", "width", "cx", "rx", "x1", "x2", "dx"}
_LEN_ATTRS_Y = {"y", "height", "cy", "ry", "y1", "y2", "dy"}
_LEN_ATTRS_D = {"r", "stroke-width", "stroke-dashoffset"}
_DROP = {f"{{{SVG_NS}}}{t}" for t in ("foreignObject", "text", "metadata", "title", "desc")}
_UNIT_RE = re.compile(r"^\s*(-?[\d.]+(?:e-?\d+)?)\s*(px|pt|%)\s*$")


def _len(value: str, attr: str, vb) -> str:
    m = _UNIT_RE.match(value)
    if not m:
        return value
    n, unit = float(m[1]), m[2]
    if unit == "px":
        return f(n) if abs(n) >= 0.01 else repr(n)
    if unit == "pt":
        return repr(n * 4 / 3)
    ref = vb[2] if attr in _LEN_ATTRS_X else vb[3] if attr in _LEN_ATTRS_Y else math.hypot(vb[2], vb[3]) / math.sqrt(2)
    return repr(n / 100 * ref)


def flag_aspect(text: str) -> float | None:
    """Width/height when the viewBox is stretched to it (preserveAspectRatio="none")."""
    root = ET.fromstring(text)
    if root.get("preserveAspectRatio", "").strip() != "none":
        return None
    try:
        w = float(_len(root.get("width", ""), "x", (0, 0, 1, 1)))
        h = float(_len(root.get("height", ""), "y", (0, 0, 1, 1)))
    except ValueError:
        return None
    return w / h if w > 0 and h > 0 else None


def normalize_flag(text: str) -> str:
    """Strip CSS units and <switch> so picosvg accepts Wikipedia-style SVGs."""
    root = ET.fromstring(text)
    vb = root.get("viewBox")
    if vb:
        vbox = [float(v) for v in re.split(r"[\s,]+", vb.strip())]
    else:
        w = float(_len(root.get("width", "100"), "x", (0, 0, 100, 100)))
        h = float(_len(root.get("height", "100"), "y", (0, 0, 100, 100)))
        vbox = [0, 0, w, h]
        root.set("viewBox", " ".join(f(v) for v in vbox))
    for a in ("width", "height"):
        root.attrib.pop(a, None)
    for el in root.iter():
        for a in list(el.attrib):
            if a in _LEN_ATTRS_X | _LEN_ATTRS_Y | _LEN_ATTRS_D:
                el.set(a, _len(el.get(a), a, vbox))
        if style := el.get("style"):
            el.set(
                "style",
                re.sub(
                    r"(stroke-width|font-size)\s*:\s*([^;]+)",
                    lambda m: f"{m[1]}:{_len(m[2], 'stroke-width', vbox)}",
                    style,
                ),
            )
    for parent in root.iter():
        for child in list(parent):
            if child.tag in _DROP:
                parent.remove(child)
    for parent in root.iter():
        for i, child in enumerate(list(parent)):
            if child.tag == f"{{{SVG_NS}}}switch":
                parent.remove(child)
                kids = [k for k in child if isinstance(k.tag, str)]
                if kids:
                    parent.insert(i, kids[0])
    return ET.tostring(root, encoding="unicode")


def border_info(svg_text: str) -> tuple[float, bool]:
    """(luminosity, transparent) of the flag's edge, as waveflag.c measures it."""
    png = render(svg_text, 512)
    im = Image.open(io.BytesIO(png)).convert("RGBA").resize((256, 256), Image.BICUBIC)
    px = im.load()
    skip, n, luma = 5, 0, 0.0
    edge = [(x, skip) for x in range(skip, 256 - skip)] + [(x, 255 - skip) for x in range(skip, 256 - skip)]
    edge += [(skip, y) for y in range(skip + 1, 255 - skip)] + [(255 - skip, y) for y in range(skip + 1, 255 - skip)]
    for x, y in edge:
        r, g, b, a = px[x, y]
        if a < 255:
            return 0.0, True
        luma += (0.2126 * r * r + 0.7152 * g * g + 0.0722 * b * b) / (255 * 255)
        n += 1
    return luma / n, False


def render(svg_text: str, width: int) -> bytes:
    return subprocess.run(
        [tool("resvg"), "-w", str(width), "-", "-c"],
        input=svg_text.encode(), check=True, capture_output=True,
    ).stdout


# --- assembly -------------------------------------------------------------


def wave_flag(svg_text: str) -> tuple[str, str]:
    """Flag SVG → (full SVG, font SVG), both on a 128-unit canvas."""
    from picosvg.svg import SVG
    from picosvg.svg_types import SVGPath

    flat = normalize_flag(svg_text)
    pico = SVG.fromstring(flat).topicosvg()
    vb = pico.view_box()
    aspect = math.sqrt((flag_aspect(svg_text) or vb.w / vb.h) / STD_ASPECT)
    if 0.9 <= aspect <= 1.1:
        aspect = 1.0
    patch = Patch(aspect)
    warp = Warper(patch, (vb.x, vb.y, vb.w, vb.h))
    lum, transparent = border_info(flat)

    root = ET.fromstring(pico.tostring())
    q = lambda t: f"{{{SVG_NS}}}{t}"  # noqa: E731
    flag_paths = []
    for el in root.iter(q("path")):
        p = SVGPath(d=el.get("d", ""))
        p = p.absolute(inplace=True).explicit_lines(inplace=True)
        p = p.expand_shorthand(inplace=True).arcs_to_cubics(inplace=True)
        el.set("d", warp.path(list(p)))
        flag_paths.append(el.get("d"))
    a = warp.affine()
    for tag in ("linearGradient", "radialGradient"):
        for g in root.iter(q(tag)):
            old = g.get("gradientTransform")
            m = "matrix(" + " ".join(repr(v) for v in a) + ")"
            g.set("gradientTransform", f"{m} {old}" if old else m)
    defs = root.find(q("defs"))
    body = [c for c in root if c.tag != q("defs")]
    defs_xml = "".join(ET.tostring(c, encoding="unicode") for c in (defs if defs is not None else []))
    flag_xml = "".join(ET.tostring(c, encoding="unicode") for c in body)
    flag_xml = re.sub(r' xmlns(:\w+)?="[^"]+"', "", flag_xml)
    defs_xml = re.sub(r' xmlns(:\w+)?="[^"]+"', "", defs_xml)

    wave = wave_path(aspect)
    shade_clip = patch.outline() if not transparent else " ".join(flag_paths)
    bands_full, bands_font = shade_bands(patch)

    border_full = border_font = ""
    if not transparent:
        alpha = 0.2 * (1 + lum)
        gray = round(0x42 * lum)
        color = f"#{gray:02x}{gray:02x}{gray:02x}"
        border = f'<path d="{wave}" fill="none" stroke="{color}" stroke-opacity="{f(alpha)}" stroke-width="3"'
        border_full = border + ' style="mix-blend-mode:luminosity"/>'
        border_font = border + "/>"

    def doc(border, shade):
        return (
            f'<svg xmlns="{SVG_NS}" viewBox="0 0 {SIZE} {SIZE}">'
            f'<defs>{defs_xml}<clipPath id="bahuan-wave"><path d="{wave}"/></clipPath>'
            f'<clipPath id="bahuan-flagshape"><path d="{shade_clip}"/></clipPath></defs>'
            f'<g clip-path="url(#bahuan-wave)">{flag_xml}{border}{shade}</g></svg>'
        )

    # The blend must sit directly on the clipped element: a clip-path group
    # in between would isolate it from the flag beneath.
    full = doc(
        border_full,
        f'<g clip-path="url(#bahuan-flagshape)" opacity="0.5" style="mix-blend-mode:soft-light">{bands_full}</g>',
    )
    font = SVG.fromstring(doc(border_font, f'<g clip-path="url(#bahuan-flagshape)">{bands_font}</g>')).topicosvg().tostring()
    return full, font


def shade_bands(patch: Patch) -> tuple[str, str]:
    """Bands of constant u+v: the soft-light mesh (white → black) in pieces."""
    full, font = [], []
    w = Warper(patch, (0, 0, 1, 1))
    eps = 0.004
    for k in range(BANDS):
        s0, s1 = 2 * k / BANDS, 2 * (k + 1) / BANDS
        poly = _band(max(0, s0 - eps), min(2, s1 + eps))
        if len(poly) < 3:
            continue
        cmds = [("M", poly[0])] + [("L", p) for p in poly[1:]] + [("Z", ())]
        d = w.path(cmds)
        lum = 1 - (s0 + s1) / 4
        g = round(lum * 255)
        full.append(f'<path d="{d}" fill="#{g:02x}{g:02x}{g:02x}"/>')
        if lum >= 0.5:
            alpha, color = (lum - 0.5) * 2 * SHADE_LIGHT, "#ffffff"
        else:
            alpha, color = (0.5 - lum) * 2 * SHADE_DARK, "#000000"
        if alpha > 0.004:
            font.append(f'<path d="{d}" fill="{color}" fill-opacity="{alpha:.3f}"/>')
    return "".join(full), "".join(font)


def _band(s0: float, s1: float) -> list[tuple[float, float]]:
    """Polygon of the unit square where s0 <= u+v <= s1."""
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]

    def clip(poly, keep, edge):
        out = []
        for i, p in enumerate(poly):
            q = poly[(i + 1) % len(poly)]
            ip, iq = keep(p), keep(q)
            if ip:
                out.append(p)
            if ip != iq:
                out.append(edge(p, q))
        return out

    def cut(s):
        def edge(p, q):
            sp, sq_ = p[0] + p[1], q[0] + q[1]
            t = (s - sp) / (sq_ - sp)
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

        return edge

    poly = clip(sq, lambda p: p[0] + p[1] >= s0, cut(s0))
    poly = clip(poly, lambda p: p[0] + p[1] <= s1, cut(s1)) if poly else []
    return poly


# --- CLI ------------------------------------------------------------------


def _one(job):
    src, out = job
    code = Path(src).stem
    key = key_for(code)
    global PRECISION
    text = Path(src).read_text(encoding="utf-8")
    err = None
    # skia-pathops occasionally chokes on near-degenerate warped curves; a
    # different rounding usually gets it through.
    for PRECISION in (2, 3, 1):
        try:
            full, font = wave_flag(text)
            break
        except Exception as e:
            err = f"{type(e).__name__}: {e}"[:200]
    else:
        return code, err
    PRECISION = 2
    (out / "full" / f"emoji_u{key}.svg").write_text(full, encoding="utf-8")
    (out / "svg" / f"emoji_u{key}.svg").write_text(font, encoding="utf-8")
    for size in (72, 512):
        png = render(font, size)
        dst = ROOT / "sources" / "waveflag" / "png" / str(size) / f"{key}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(png)
    return code, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("flags", nargs="*", help="region-flags SVGs (default: all)")
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "flags" / "out")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    src_dir = ROOT / "sources" / "cache" / "worktrees" / "waveflag" / "third_party" / "region-flags" / "svg"
    files = a.flags or [
        *sorted(str(p) for p in src_dir.glob("*.svg")),
        *sorted(str(p) for p in EXTRA.glob("emoji_u*.svg")),
    ]
    for sub in ("full", "svg"):
        (a.out / sub).mkdir(parents=True, exist_ok=True)
    from steamer.emoji import by_key

    failed, needed = [], []
    with ProcessPoolExecutor(a.jobs) as pool:
        for code, err in pool.map(_one, [(s, a.out) for s in files]):
            if err:
                failed.append(code)
                if key_for(code) in by_key():
                    needed.append(code)
                print(f"{code}: {err}", file=sys.stderr)
    print(f"waved {len(files) - len(failed)} flags into {a.out}")
    if needed:
        print(f"failed flags that are emoji: {' '.join(needed)}", file=sys.stderr)
    return 1 if needed else 0


if __name__ == "__main__":
    sys.exit(main())
