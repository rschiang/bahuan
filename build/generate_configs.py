# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generate nanoemoji config files for Bahuan, one per output format.
# Adapted from noto-emoji's colrv1_generate_configs.py: sources are the
# resolved masters in art/svg (flags included), not svg/ + waved-svg/.

from pathlib import Path

_FAMILY_NAME = "Bahuan"
_ROOT = Path(__file__).resolve().parent.parent
_ART_SVG_DIR = _ROOT / "art" / "svg"
_CONFIG_DIR = _ROOT / "build" / "config"

# config name → (output file, nanoemoji color_format, extra settings)
_OUTPUTS = {
    "colrv1": ("Bahuan-COLRv1.ttf", "glyf_colr_1", {"clipbox_quantization": 32}),
    "cbdt": ("Bahuan-CBDT.ttf", "cbdt", {"use_zopflipng": False}),
    "sbix": ("Bahuan-sbix.ttf", "sbix", {"use_zopflipng": False}),
    "svg": ("Bahuan-SVG.ttf", "picosvg", {"keep_glyph_names": True}),
}


def _toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return repr(v) if isinstance(v, int) else f'"{v}"'


def _write_config(config_name, output_file, color_format, extra, svg_files):
    svg_files = [Path("../../art/svg") / f.name for f in svg_files]
    svg_list = ",\n    ".join(f'"{f}"' for f in sorted(svg_files)).rstrip()
    extra_lines = "".join(f"{k} = {_toml_value(v)}\n" for k, v in extra.items())
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_DIR / f"{config_name}.toml", "w") as f:
        f.write(
            f"""
family = "{_FAMILY_NAME}"
output_file = "{output_file}"
color_format = "{color_format}"
{extra_lines}
[axis.wght]
name = "Weight"
default = 400

[master.regular]
style_name = "Regular"
srcs = [
    {svg_list},
]

[master.regular.position]
wght = 400
"""
        )


def main():
    svgs = tuple(_ART_SVG_DIR.glob("emoji_u*.svg"))
    if not svgs:
        raise SystemExit("art/svg is empty; run `steamer materialize` first")
    for name, (output, fmt, extra) in _OUTPUTS.items():
        _write_config(name, output, fmt, extra, svgs)
    print(f"wrote {len(_OUTPUTS)} configs for {len(svgs)} SVGs to {_CONFIG_DIR}")


if __name__ == "__main__":
    main()
