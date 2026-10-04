# Bahuan

Bahuan is a color emoji font that brings back Google's **blob** emoji. It picks,
emoji by emoji, from the published eras of [Noto Emoji][noto] art: blob faces
from Android 6–7.1, flat objects from Android 7.x and the Android 12 refresh,
and the waved Android 7.1 flags.

## Build

```sh
uv sync
make
```

Fonts land in `build/out/`. See [DECISIONS.md](DECISIONS.md) for the plan and
the reasoning behind each choice.

## License

Code and art: [Apache-2.0](LICENSE). Fonts: [OFL-1.1](OFL.txt).
The art is Google's; see [AUTHORS](AUTHORS).

[noto]: https://github.com/googlefonts/noto-emoji
