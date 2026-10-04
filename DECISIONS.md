# Decisions

Plans, rationale and choices for Bahuan. The README stays short; this file
holds the reasons.

## Goals

- Bring back the blobs, mixing Android 6 and 7.x.
- Prefer flat designs: the Android 7.x objects and the Android 12 refresh.
- Never use the bordered Android 8–11 style or Noto 3D, unless nothing else
  exists for an emoji.
- Keep the Android 7.1 waved flags, using the `waveflag` mesh warp.
- Use a current toolchain: COLRv1, CBDT, sbix and OpenType-SVG, built and
  released by CI.

## Settled

| Topic | Decision |
|---|---|
| Name | The font is **Bahuan**. The selection tool is **`steamer`**. |
| Starting point | A brand-new, empty repo. Copy upstream's **current** build tooling; don't re-port legacy scripts. |
| Era labels | Android versions only name an era. We **don't** check them against the fonts Android actually shipped. |
| Emoji newer than the blobs (Emoji 5.0+) | Fall back to Google's own newer designs, preferring the newest flat (Android 12+) version. Anything still bordered goes to a redraw backlog. |
| How styles are chosen | Per Unicode **subgroup** (about 100 of them, from `emoji-test.txt`), with overrides for single emoji. No default style is fixed in advance; pick whatever is most harmonious. |
| Manifest format | Compact `subgroup = era` and `key = era` tables. Reasons go in inline comments. |
| Docs | `README.md` stays short. Plans, rationale and choices go in `DECISIONS.md`. |
| Licenses | Code and art under Apache-2.0, fonts under OFL-1.1. Keep Google's attribution. Don't use "Noto" in the name (it's Google's trademark). |

## Upstream

Build tooling in `build/` is adapted from
[googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) at
`e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e` (main, 2026-09-24, Unicode 18.0).
`sources/emoji-test.txt` is pinned to Emoji 18.0.
