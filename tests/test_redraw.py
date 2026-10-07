import re

from steamer.fixups import picosvg_ok
from steamer.redraw import Layer, Recipe, lint, render, transform

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
<path id="a" d="M0,0h10v10z" style="fill:#AAAAAA"/>
<path id="b" d="M20,0h10v10z" fill="#aaaaaa"/>
<path id="c" d="M40,0h10v10z" style="fill:#123456"/>
<path id="d" d="M60,0h10v10z"/>
<g fill="#00FF00"><path id="e" d="M80,0h10v10z"/></g>
<path id="f" d="M100,0h10v10z" fill="#FFFFFF"/>
</svg>"""


def test_recolor_style_and_attribute_case_insensitive():
    out = transform(SVG, Recipe("x", "e", "s", "w", recolor={"#aaaaaa": "#FF0000"}))
    assert out.count("#FF0000") == 2
    assert "#AAAAAA" not in out.upper().replace("#FF0000", "")  # nothing left to map
    assert "#123456" in out  # colour absent from the map is untouched


def test_drop_removes_matching_elements():
    out = transform(SVG, Recipe("x", "e", "s", "w", drop=("#ffffff",)))
    assert 'id="f"' not in out and 'id="a"' in out


def test_fill_only_paints_unfilled_shapes():
    out = transform(SVG, Recipe("x", "e", "s", "w", fill="#1976D2"))
    d = re.search(r'<path[^>]*id="d"[^>]*>', out).group(0)
    e = re.search(r'<path[^>]*id="e"[^>]*>', out).group(0)
    f = re.search(r'<path[^>]*id="f"[^>]*>', out).group(0)
    assert "#1976D2" in d
    assert "#1976D2" not in e  # inherits the group's fill
    assert "#1976D2" not in f and "#FFFFFF" in f


def test_real_donor_recipe_is_valid():
    out = render(Recipe("2764", "android-7.1", "1f49b", "w", recolor={"#FBB817": "#F44336"}))
    assert set(re.findall(r"#[0-9A-Fa-f]{6}", out)) == {"#F44336"}
    assert picosvg_ok(out) is None


def test_lint_reports_unknown_donor_and_bad_colour():
    errs = lint(
        {
            "2764": Recipe("2764", "android-7.1", "ffffff", "w"),
            "1f7e0": Recipe("1f7e0", "android-7.1", "1f534", "w", recolor={"#DB4437": "orange"}),
        }
    )
    assert any("donor android-7.1:ffffff" in e for e in errs)
    assert any("bad colour 'orange'" in e for e in errs)


def test_subpath_keeps_only_the_named_subpath():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0,0h10v10z M20,0h10v10z"/></svg>'
    out = transform(svg, Recipe("x", "e", "s", "w", subpath=0, fill="#000000"))
    assert 'd="M0,0h10v10z"' in out


def test_add_layer_draws_a_second_master_on_top_scaled():
    base = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128" fill="#7CB342"/></svg>'
    r = Recipe(
        "2705",
        "android-7.1",
        "274e",
        "w",
        add=(Layer("android-7.1", "2705", recolor={"#E0E0E0": "#FFFFFF"}, drop=("#757F3F",), scale=0.5),),
    )
    out = transform(base, r)
    assert 'transform="translate(32,32) scale(0.5)"' in out
    assert "#FFFFFF" in out and "#757F3F" not in out  # layer painted, its stray path gone
