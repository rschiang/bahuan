import pytest

from steamer.manifest import Manifest, set_entry
from steamer.report import explain, report
from steamer.resolve import resolve

BASE = """
[defaults]
fallback = ["android-12", "latest"]   # post-blob emoji: newest flat Google design
avoid = ["android-8.0", "android-11"]  # only if nothing else exists; reported

[subgroup]
food-fruit = "android-7.1"      # blob-era fruit
hand-fingers-closed = "android-7.1"
face-smiling = "android-7.1"    # classic blob

[override]
1f34a = "android-12"    # 🍊
"""


def picks(text=BASE):
    return resolve(Manifest.parse(text))


def test_override_beats_subgroup():
    p = picks()
    assert (p["1f34a"].era, p["1f34a"].why) == ("android-12", "override")
    assert (p["1f34b"].era, p["1f34b"].why) == ("android-7.1", "subgroup")


def test_subgroup_beats_fallback():
    p = picks()
    assert p["1f600"].why == "subgroup"
    # Melting face (E14) is not in 7.1: falls back.
    assert (p["1fae0"].era, p["1fae0"].why) == ("latest", "fallback")
    # No subgroup entry at all: straight to the fallback chain.
    assert p["1f431"].why == "fallback"


def test_family_follows_base():
    p = picks()
    assert p["1f44d"].era == "android-7.1"
    assert p["1f44d_1f3fd"].era == "android-7.1"
    assert p["1f44d_1f3fd"].family == "1f44d"


def test_override_on_base_covers_variants():
    p = picks(BASE + '1f44d = "latest"\n')
    assert {p[k].era for k in ("1f44d", "1f44d_1f3fb", "1f44d_1f3ff")} == {"latest"}
    assert p["1f44d_1f3fb"].why == "override"


def test_family_moves_together():
    # 6.0.1 has 👍 but no skin tones, so the whole family moves on.
    p = picks(BASE.replace('hand-fingers-closed = "android-7.1"', 'hand-fingers-closed = "android-6.0.1"'))
    assert p["1f44d"].era == p["1f44d_1f3fd"].era
    assert p["1f44d"].era in ("android-12", "latest")


def test_avoid_eras_are_last_and_reported():
    m = Manifest.parse(BASE.replace('fallback = ["android-12", "latest"]', 'fallback = ["android-7.1"]'))
    p = resolve(m)
    # Zany face (E5.0) exists in neither 7.1 nor the subgroup era.
    assert (p["1f92a"].era, p["1f92a"].why) == ("android-8.0", "avoid")
    assert "1f92a" in report(p, m).split("## Avoided eras used")[1]


def test_raster_only_pick_has_vector_era():
    p = picks(BASE.replace('face-smiling = "android-7.1"', 'face-smiling = "android-6.0.1"'))
    assert p["1f600"].era == "android-6.0.1"
    assert p["1f600"].vector == "android-12"


def test_explain_orange():
    out = explain("1f34a", Manifest.parse(BASE))
    assert "→ android-12 (override)" in out


def test_set_keeps_comments(tmp_path):
    f = tmp_path / "selection.toml"
    f.write_text(BASE)
    set_entry("food-fruit", "android-12", path=f)
    set_entry("🍋", "latest", "lemon reads better", path=f)
    text = f.read_text()
    assert 'food-fruit = "android-12"      # blob-era fruit' in text
    assert '1f34b = "latest" # lemon reads better' in text
    assert "# post-blob emoji: newest flat Google design" in text
    set_entry("1f34a", None, path=f)
    assert "1f34a" not in f.read_text()


def test_set_rejects_unknown():
    with pytest.raises(ValueError):
        set_entry("not-a-subgroup", "latest")


def test_fallback_skips_bordered_art():
    p = picks()
    # Pleading face: android-12's file is the android-11 one; latest redrew it.
    assert p["1f97a"].era == "latest"
    assert "unchanged from an avoided era" in " ".join(p["1f97a"].trail)


def test_subgroup_list_pins_the_chain():
    p = picks(BASE.replace("[subgroup]\n", '[subgroup]\nfamily = ["android-7.1", "android-12"]\n'))
    # Not in 7.1, so android-12 (listed) wins over latest even though unchanged since 11.
    fam = "1f468_200d_1f469_200d_1f467_200d_1f466"
    assert p[fam].why == "subgroup"
    assert p[fam].era in ("android-7.1", "android-12")


def test_import_gallery(tmp_path):
    import json

    from steamer.gallery import import_choices

    f = tmp_path / "selection.toml"
    f.write_text(BASE)
    choices = tmp_path / "choices.json"
    choices.write_text(json.dumps({"subgroup": {"food-fruit": "android-12"}, "override": {"1f34a": None, "1f600": "latest"}}))
    import_choices(choices, manifest=f)
    m = Manifest.load(f)
    assert m.subgroup["food-fruit"] == "android-12"
    assert "1f34a" not in m.override
    assert m.override["1f600"] == "latest"
    assert "# blob-era fruit" in f.read_text()
